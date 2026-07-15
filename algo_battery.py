"""
应急无人机调度系统 — 统一电量管理模块
文件：algo_battery.py

职责：
  所有算法共享的电量约束处理。
  当无人机剩余电量不足以完成下一段飞行时，自动在最近服务区插入换电站航点，
  并施加合理的换电时间惩罚。

数据约定（trajectory 字典中有以下字段会被处理）：
  traj["waypoints"]  — [{"pos":[x,y,z], "label":""}, ...]
  traj["total_time"] — 秒（飞行时间，不含换电）
  traj["total_distance"] — 米
  traj["drone_index"]或数组索引 — 用于查找 drone 参数
  result["trajectories"] — 按 drones 顺序排列

添加/修改字段：
  traj["swap_stations"] — [{"pos":[x,y,z], "name":"..."}]
  traj["swap_count"] — int
  traj["battery_remaining_pct"] — 飞到终点剩余电量百分比
  traj["power_low"] — bool，是否换电过
  result["total_swaps"] — int
  result["total_swap_time"] — 总换电时间（秒）

使用示例（在每个算法的 solve 末尾调用）：
    from algo_battery import BatteryManager
    return BatteryManager().apply(drones, service_areas, result)

无人机电量参数来源（优先使用 drone 对象的字段）：
  - battery (float): 当前电量百分比或最大容量（默认 100）
  - battery_capacity_kWh (float): 物理电池容量（kWh）
  - max_range (float): 满电最大航程（km）
  - max_speed (float): 最大速度（km/h）

物理参数推导优先级：
  1. 如果 drone["battery_capacity_kWh"] 存在 → capacity_kWh = 该值
     否则如果 drone["max_range"] 存在 → capacity_kWh = max_range * SPECIFIC_CONSUMPTION
     否则 → capacity_kWh = BATTERY_CAPACITY_KWH_DEFAULT (0.6 kWh for a typical 10kg drone)
  2. current_energy = capacity_kWh * (battery / 100)
     （battery 字段解释为百分比）
  3. E_CONSUME = capacity_kWh / (max_range * 1000)  (kWh per meter)
     如果 max_range 不存在 → E_CONSUME = DEFAULT_E_CONSUME_PER_M
  4. 换电时间：由 drone["model"] 查表，默认 8 分钟 (480 s)
     (不合理地短，反映"快充"而非"换电池"场景，如需真实换电池 ~2 分钟/块)
"""

import math
import numpy as np

# ── 默认物理参数 ──────────────────────────────────────────────
# 典型 10kg 行业无人机（DJI M30T 同级别）
CAPACITY_DEFAULT_KWH = 0.57   # kWh（M30T 电池标称 ~0.57 kWh）
SPECIFIC_CONSUMPTION = 38.0   # Wh/km 典型巡航水平（含抗风余量）
DEFAULT_MAX_RANGE_KM = 15.0    # 默认最大航程 km
DEFAULT_MAX_SPEED_KMH = 60.0   # 默认最大速度 km/h
DEFAULT_E_CONSUME_PER_M = CAPACITY_DEFAULT_KWH * 1000 / (DEFAULT_MAX_RANGE_KM * 1000)
# ≈ 0.038 Wh/m = 0.038 / 3600 Wh/s，但这里我们直接用比例
# 为简化，我们直接让 E_CONSUME = capacity_kWh / (max_range * 1000) * 100 (百分比/米)

# ── 模型→换电时间（秒）查表 ───────────────────────────────────
# 数据基于典型行业无人机热换电池操作（工作人员换电池），通常 1~3 分钟
SWAP_TIME_BY_MODEL = {
    "DIY-M30T": 120,           # DJI M30T 双电池热换 ~2 分钟
    "DJI-M350": 150,           # 更重，换电稍慢 ~2.5 分钟
    "DJI-M300": 150,
    "DJI-MINI": 60,            # 小型无人机电池轻，换电 ~1 分钟
    "DJI-AVATA": 60,
    "EVO-HP": 90,              # 应急专用机，快速卡扣 ~1.5 分钟
    "EVO-HEAVY": 300,          # 大型物流无人机换电 ~5 分钟
    "EVO-VTOL": 420,           # VTOL 大型换电 ~7 分钟
}
SWAP_TIME_DEFAULT = 120.0  # 默认 2 分钟

# ── 安全电量阈值（剩余电量百分比过此值时强制充电） ───────────
# 即：如果飞到下一段后剩余电量 < FORCE_SWAP_BELOW_PCT，则在该段前换电
FORCE_SWAP_BELOW_PCT = 25.0
# 如果当前电量已经低于此阈值且不在服务区，也需要换电
CRITICAL_BATTERY_PCT = 12.0


class BatteryManager:
    """统一电量管理器，由所有算法的 solve() 末尾调用。"""

    def apply(self, drones, service_areas, result):
        """
        对 result 中的所有轨迹做电量约束处理。

        参数:
          drones: list[dict] — 无人机对象列表（与 trajectories 顺序对应）
          service_areas: list[dict] — 服务区列表 {"name","x","y","z",...}
          result: dict — 算法返回的 result，必须有 "trajectories"

        返回:
          原地修改后的 result
        """
        trajectories = result.get("trajectories", [])
        if not trajectories or not service_areas:
            result.setdefault("total_swaps", 0)
            result.setdefault("total_swap_time", 0.0)
            return result

        # 提取服务区坐标
        sa_coords = [(float(a["x"]), float(a["y"]), float(a["z"])) for a in service_areas]
        sa_names = [a.get("name", f"服务区{i+1}") for i, a in enumerate(service_areas)]

        total_swaps = 0
        total_swap_time = 0.0
        total_time_recomputed = 0.0

        for t_idx, traj in enumerate(trajectories):
            waypoints = traj.get("waypoints", [])
            if len(waypoints) < 2:
                traj.setdefault("swap_stations", [])
                traj.setdefault("swap_count", 0)
                traj.setdefault("power_low", False)
                traj.setdefault("battery_remaining_pct", 100.0)
                continue

            # 如果已经处理过换电（即调用该模块前已设置 swap_stations），跳过插入但累积统计
            existing_swaps = traj.get("swap_stations")
            if existing_swaps is not None and len(existing_swaps) > 0:
                drone = drones[t_idx] if t_idx < len(drones) else {}
                st = self._swap_time(drone)
                traj["swap_count"] = len(existing_swaps)
                traj["total_swap_time"] = round(len(existing_swaps) * st, 2)
                traj["power_low"] = len(existing_swaps) > 0
                total_swaps += len(existing_swaps)
                total_swap_time += len(existing_swaps) * st
                # 重新计算累计 total_time（飞行时间 + swap 时间）
                total_dist = 0.0
                for k in range(len(waypoints) - 1):
                    total_dist += math.sqrt(sum(
                        (waypoints[k]["pos"][j] - waypoints[k + 1]["pos"][j]) ** 2
                        for j in range(3)
                    ))
                speed_kmh = float(drone.get("max_speed", DEFAULT_MAX_SPEED_KMH))
                speed_ms = speed_kmh / 3.6
                if speed_ms <= 0:
                    speed_ms = 16.67
                traj["total_time"] = round(total_dist / speed_ms + traj["total_swap_time"], 2)
                traj["total_distance"] = round(total_dist, 2)
                total_time_recomputed = max(total_time_recomputed, traj["total_time"])
                continue

            # ── 计算电量参数 ──
            drone = drones[t_idx] if t_idx < len(drones) else {}
            capacity_kwh = self._battery_capacity_kwh(drone)
            max_range_km = float(drone.get("max_range", DEFAULT_MAX_RANGE_KM))
            battery_pct_start = float(drone.get("battery", 100.0))
            speed_kmh = float(drone.get("max_speed", DEFAULT_MAX_SPEED_KMH))

            # 初始可用电量（kWh）
            energy_remaining = capacity_kwh * (battery_pct_start / 100.0)

            # 每米消耗（kWh/m）
            max_range_m = max_range_km * 1000.0
            if max_range_m <= 0:
                e_consume_per_m = DEFAULT_E_CONSUME_PER_M
            else:
                e_consume_per_m = capacity_kwh / max_range_m

            # 换电时间（秒）
            swap_time = self._swap_time(drone)

            new_waypoints = [waypoints[0]]
            swap_stations = []
            swap_time_accum = 0.0

            for i in range(len(waypoints) - 1):
                p1 = new_waypoints[-1]["pos"]
                p2 = waypoints[i + 1]["pos"]
                seg_dist = math.sqrt(sum((p1[j] - p2[j]) ** 2 for j in range(3)))
                need = seg_dist * e_consume_per_m

                # 飞到后剩余
                remaining_after = energy_remaining - need
                remaining_pct_after = (remaining_after / capacity_kwh * 100.0) if capacity_kwh > 0 else 0.0

                if remaining_after < 0 or remaining_pct_after < FORCE_SWAP_BELOW_PCT:
                    # ── 电量不足，找最近服务区换电 ──
                    cur_pos = new_waypoints[-1]["pos"]
                    sa_idx = self._nearest_sa(cur_pos, sa_coords)

                    # 飞向服务区的消耗
                    sa_pos = sa_coords[sa_idx]
                    fly_to_sa_dist = math.sqrt(
                        sum((cur_pos[j] - sa_pos[j]) ** 2 for j in range(3))
                    )
                    fly_to_sa_energy = fly_to_sa_dist * e_consume_per_m

                    # 如果飞向服务区都不够（极端：当前已在低电量且服务区很远）
                    # 还是飞向服务区，视为服务区带有移动充电车兜底
                    if energy_remaining < fly_to_sa_energy:
                        fly_to_sa_energy = energy_remaining * 0.9

                    # 插入换电站航点
                    sa_pos_list = list(sa_pos)
                    sa_name = sa_names[sa_idx]
                    swap_wp = {
                        "pos": sa_pos_list,
                        "label": f"换电站-{sa_name}",
                    }
                    new_waypoints.append(swap_wp)
                    swap_stations.append({
                        "pos": sa_pos_list,
                        "name": sa_name,
                    })

                    # 扣减飞向服务区所耗，然后换电
                    energy_remaining -= fly_to_sa_energy
                    energy_remaining = capacity_kwh  # 满电

                    swap_time_accum += swap_time

                # 飞行到下一航点
                new_waypoints.append(waypoints[i + 1])
                energy_remaining -= need
                if energy_remaining < 0:
                    energy_remaining = 0.0

            # 更新轨迹字段
            traj["waypoints"] = new_waypoints
            traj["swap_stations"] = swap_stations
            traj["swap_count"] = len(swap_stations)
            traj["power_low"] = len(swap_stations) > 0

            # 重新计算总距离与飞行时间（包含换电站偏离）
            total_dist = 0.0
            for k in range(len(new_waypoints) - 1):
                total_dist += math.sqrt(sum(
                    (new_waypoints[k]["pos"][j] - new_waypoints[k + 1]["pos"][j]) ** 2
                    for j in range(3)
                ))
            speed_ms = speed_kmh / 3.6
            if speed_ms <= 0:
                speed_ms = 16.67
            flight_time = total_dist / speed_ms

            traj["total_distance"] = round(total_dist, 2)
            traj["total_time"] = round(flight_time + swap_time_accum, 2)
            traj["total_swap_time"] = round(swap_time_accum, 2)
            traj["battery_remaining_pct"] = round(
                (energy_remaining / capacity_kwh * 100.0) if capacity_kwh > 0 else 0.0, 1
            )

            total_swaps += len(swap_stations)
            total_swap_time += swap_time_accum
            total_time_recomputed = max(total_time_recomputed, traj["total_time"])

        # 更新 result 顶层统计
        result["total_swaps"] = total_swaps
        result["total_swap_time"] = round(total_swap_time, 2)
        result["total_time"] = round(total_time_recomputed, 2)
        result["total_distance"] = round(
            sum(t.get("total_distance", 0.0) for t in trajectories), 2
        )
        n_drones = len(trajectories)
        if total_swaps > 0:
            result["message"] = (
                f"电量管理已应用，{n_drones}架无人机，"
                f"共触发{total_swaps}次换电，"
                f"总换电时间{round(total_swap_time, 1)}秒"
            )
        else:
            result["message"] = (
                f"电量管理已应用，{n_drones}架无人机，"
                f"电量充足无需换电"
            )

        return result

    # ──────────────────────────────────────────────────────────
    #  内部工具
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _battery_capacity_kwh(drone):
        """推测电池容量（kWh）。优先使用显式字段。"""
        cap = drone.get("battery_capacity_kWh")
        if cap is not None:
            try:
                return float(cap)
            except (ValueError, TypeError):
                pass
        # 根据 max_range 和 SPECIFIC_CONSUMPTION 推算
        max_range_km = drone.get("max_range")
        if max_range_km is not None:
            try:
                return float(max_range_km) * SPECIFIC_CONSUMPTION / 1000.0
            except (ValueError, TypeError):
                pass
        return CAPACITY_DEFAULT_KWH

    @staticmethod
    def _swap_time(drone):
        """根据模型返回换电时间（秒）。模型名忽略大小写、空格、连字符差异。"""
        raw_model = str(drone.get("model", "")).strip()
        # 标准化：大写 + 移除空格/连字符/下划线
        norm = raw_model.upper().replace(" ", "").replace("-", "").replace("_", "")
        for key, val in SWAP_TIME_BY_MODEL.items():
            key_norm = key.upper().replace(" ", "").replace("-", "").replace("_", "")
            if key_norm == norm:
                return float(val)
        # 含 MINI 关键字 → 小型机（~60s）
        if "MINI" in norm:
            return 60.0
        # 含 HEAVY / VTOL → 大型机（~300s+）
        if "HEAVY" in norm or "VTOL" in norm:
            return 300.0
        # 根据电池容量大小推断
        cap = drone.get("battery_capacity_kWh")
        if cap is not None:
            try:
                cap_f = float(cap)
                if cap_f >= 1.5:
                    return 300.0
                elif cap_f >= 0.8:
                    return 180.0
                elif cap_f >= 0.3:
                    return 90.0
                else:
                    return 60.0
            except (ValueError, TypeError):
                pass
        return SWAP_TIME_DEFAULT

    @staticmethod
    def _nearest_sa(pos, sa_coords):
        """返回 service_area 索引，基于 3D 距离最近。"""
        min_dist = float("inf")
        best = 0
        for i, sa in enumerate(sa_coords):
            d = math.sqrt(sum((pos[j] - sa[j]) ** 2 for j in range(3)))
            if d < min_dist:
                min_dist = d
                best = i
        return best

    # ──────────────────────────────────────────────────────────
    #  渲染辅助（接口各算法在渲染时调用）
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def render_swap_mPL(ax, swap_stations, color="#00E676"):
        """在 matplotlib axes 上画换电站标记（∎ 绿方块）。"""
        for swap in swap_stations:
            sp = swap["pos"]
            ax.scatter(
                [sp[0]], [sp[1]], [sp[2]],
                color=color, s=130, marker="s",
                edgecolors="white", linewidths=1.6,
                zorder=6,
            )

    @staticmethod
    def render_swap_plotly_swap_traces(swap_stations):
        """返回 plotly go.Scatter3d 的换电站 trace 列表。"""
        import plotly.graph_objects as go
        traces = []
        for swap in swap_stations:
            sp = swap["pos"]
            traces.append(go.Scatter3d(
                x=[sp[0]], y=[sp[1]], z=[sp[2]],
                mode="markers+text",
                marker=dict(
                    size=12, color="#00E676", symbol="square",
                    line=dict(color="white", width=2),
                ),
                text=["\u26a1"],  # ⚡
                textposition="top center",
                textfont=dict(size=14, color="#00E676"),
                name=f"换电站-{swap.get('name', '')}",
                showlegend=True,
            ))
        return traces
