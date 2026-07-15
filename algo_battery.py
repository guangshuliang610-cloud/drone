"""
应急无人机调度系统 — 统一电量管理模块
文件：algo_battery.py

职责：
  所有算法共享的电量约束处理。
  当无人机剩余电量不足以完成下一段飞行时，自动在最近服务区插入换电站航点，
  并施加合理的换电时间惩罚。

物理模型（基于重载救援无人机工程功耗公式）：
  悬停基准功率: P_h = m_total * g / eta_total
  爬升功率:     P_climb = K_climb * P_h   (K_climb = 1.25)
  巡航功率:     P_cruise = K_cruise * P_h  (K_cruise = 0.90)
  下降功率:     P_descent = K_descent * P_h (K_descent = 0.85)
  单段能耗:     E_seg = P_seg * t = P_seg * dist_3d / speed
  可用能量:     E_usable = U_bat * C_bat_Ah * DOD

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
  - m_body (float): 机身质量(kg)，默认 10.0
  - m_payload (float): 载荷质量(kg)，默认 0.0
  - U_bat (float): 电池标称电压(V)，默认 64.8 (18S)
  - C_bat_Ah (float): 电池容量(Ah)，默认 30.0
  - battery_capacity_kWh (float): 物理电池容量(kWh)，备选
  - max_range (float): 满电最大航程（km），备选
  - max_speed (float): 最大速度（km/h）
  - battery (float): 当前电量百分比，默认 100
"""

import math
import numpy as np

# ── 物理常数（重载救援无人机工程标准） ─────────────────────────
G = 9.81              # 重力加速度(m/s^2)
ETA_TOTAL = 0.65      # 整机动力总效率（电机+电调+桨）
K_CLIMB = 1.25        # 爬升功率系数（满载）
K_CRUISE = 0.90       # 巡航功率系数（满载）
K_DESCENT = 0.85      # 下降功率系数（满载）
DOD = 0.80            # 电池可用放电深度（安全预留20%）

# ── 默认无人机参数 ────────────────────────────────────────────
DEFAULT_M_BODY = 10.0         # 默认机身质量(kg)
DEFAULT_M_PAYLOAD = 0.0       # 默认载荷(kg)
DEFAULT_U_BAT = 64.8          # 默认电池电压(V)，18S
DEFAULT_C_BAT_AH = 30.0       # 默认电池容量(Ah)
DEFAULT_MAX_RANGE_KM = 15.0   # 默认最大航程(km)
DEFAULT_MAX_SPEED_KMH = 60.0  # 默认最大速度(km/h)

# ── 兼容旧模型的参数（fallback用） ───────────────────────────
CAPACITY_DEFAULT_KWH = 0.57   # kWh（M30T 电池标称 ~0.57 kWh）
SPECIFIC_CONSUMPTION = 38.0   # Wh/km 典型巡航水平（含抗风余量）

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

    # ──────────────────────────────────────────────────────────
    #  Drone-task assignment by service area
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def build_delivery_tasks(materials, service_areas, rescue_points):
        """Build delivery tasks from materials."""
        sa_index = {a["name"]: i for i, a in enumerate(service_areas)}
        rp_index = {r["name"]: i for i, r in enumerate(rescue_points)}
        task_dict = {}
        for m in materials:
            sa_name = m.get("service_area", "")
            rp_name = m.get("rescue_point", "")
            sa_idx = sa_index.get(sa_name)
            rp_idx = rp_index.get(rp_name)
            if sa_idx is not None and rp_idx is not None:
                task_dict.setdefault((sa_idx, rp_idx), []).append(m["name"])
        return [(sa_idx, rp_idx, mats) for (sa_idx, rp_idx), mats in task_dict.items()]

    @staticmethod
    def assign_drones_to_tasks(drones, tasks, service_areas, rescue_points):
        """Assign drones to tasks: drone at SA X delivers materials at SA X."""
        sa_tasks = {}
        for sa_idx, rp_idx, mats in tasks:
            sa_tasks.setdefault(sa_idx, []).append((rp_idx, mats))
        n_rp = len(rescue_points)
        assignments = []
        for d_idx in range(len(drones)):
            sa_idx = d_idx % len(service_areas)
            if sa_idx in sa_tasks and sa_tasks[sa_idx]:
                rp_idx, mat_names = sa_tasks[sa_idx].pop(0)
                has_task = True
            else:
                rp_idx = d_idx % n_rp if n_rp > 0 else 0
                mat_names = []
                has_task = False
            assignments.append({
                "drone_idx": d_idx,
                "sa_idx": sa_idx,
                "rp_idx": rp_idx,
                "material_names": mat_names,
                "has_task": has_task,
            })
        return assignments

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

            # ── 计算机体物理参数 ──
            drone = drones[t_idx] if t_idx < len(drones) else {}

            # 可用电池能量(Wh)
            e_usable_wh = self._usable_energy_wh(drone)
            # 初始可用能量
            battery_pct_start = float(drone.get("battery", 100.0))
            energy_remaining_wh = e_usable_wh * (battery_pct_start / 100.0)
            # 悬停基准功率(W)
            p_hover = self._hover_power(drone)
            # 换电时间(秒)
            swap_time = self._swap_time(drone)
            # 飞行速度
            speed_kmh = float(drone.get("max_speed", DEFAULT_MAX_SPEED_KMH))
            speed_ms = speed_kmh / 3.6
            if speed_ms <= 0:
                speed_ms = 16.67

            new_waypoints = [waypoints[0]]
            swap_stations = []
            swap_time_accum = 0.0

            for i in range(len(waypoints) - 1):
                p1 = new_waypoints[-1]["pos"]
                p2 = waypoints[i + 1]["pos"]

                # 计算该段能耗（基于物理模型，区分爬升/巡航/下降）
                e_seg_wh = self._segment_energy_wh(p1, p2, p_hover, speed_ms)

                # 飞到后剩余
                remaining_after_wh = energy_remaining_wh - e_seg_wh
                remaining_pct_after = (remaining_after_wh / e_usable_wh * 100.0) if e_usable_wh > 0 else 0.0

                if remaining_after_wh < 0 or remaining_pct_after < FORCE_SWAP_BELOW_PCT:
                    # ── 电量不足，找最近服务区换电 ──
                    cur_pos = new_waypoints[-1]["pos"]
                    sa_idx = self._nearest_sa(cur_pos, sa_coords)

                    # 飞向服务区的能耗
                    sa_pos = sa_coords[sa_idx]
                    fly_to_sa_energy_wh = self._segment_energy_wh(cur_pos, sa_pos, p_hover, speed_ms)

                    # 如果飞向服务区都不够（极端：当前已在低电量且服务区很远）
                    # 还是飞向服务区，视为服务区带有移动充电车兜底
                    if energy_remaining_wh < fly_to_sa_energy_wh:
                        fly_to_sa_energy_wh = energy_remaining_wh * 0.9

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
                    energy_remaining_wh -= fly_to_sa_energy_wh
                    energy_remaining_wh = e_usable_wh  # 满电

                    swap_time_accum += swap_time

                # 飞行到下一航点
                new_waypoints.append(waypoints[i + 1])
                energy_remaining_wh -= e_seg_wh
                if energy_remaining_wh < 0:
                    energy_remaining_wh = 0.0

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
            flight_time = total_dist / speed_ms

            traj["total_distance"] = round(total_dist, 2)
            traj["total_time"] = round(flight_time + swap_time_accum, 2)
            traj["total_swap_time"] = round(swap_time_accum, 2)
            traj["battery_remaining_pct"] = round(
                (energy_remaining_wh / e_usable_wh * 100.0) if e_usable_wh > 0 else 0.0, 1
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
    #  物理模型核心方法
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _hover_power(drone):
        """
        计算悬停基准功率 P_h = m_total * g / eta_total
        单位：瓦特(W)
        """
        m_body = float(drone.get("m_body", DEFAULT_M_BODY))
        m_payload = float(drone.get("m_payload", DEFAULT_M_PAYLOAD))
        m_total = m_body + m_payload
        return m_total * G / ETA_TOTAL

    @staticmethod
    def _usable_energy_wh(drone):
        """
        计算电池可用能量 E_usable = U_bat * C_bat_Ah * DOD
        单位：瓦时(Wh)
        兼容旧字段 battery_capacity_kWh 和 max_range
        """
        # 优先使用 U_bat * C_bat_Ah
        u_bat = drone.get("U_bat")
        c_bat_ah = drone.get("C_bat_Ah")
        if u_bat is not None and c_bat_ah is not None:
            try:
                return float(u_bat) * float(c_bat_ah) * DOD
            except (ValueError, TypeError):
                pass
        # 备选：battery_capacity_kWh
        cap_kwh = drone.get("battery_capacity_kWh")
        if cap_kwh is not None:
            try:
                return float(cap_kwh) * 1000.0 * DOD  # kWh -> Wh
            except (ValueError, TypeError):
                pass
        # 最后备选：max_range * SPECIFIC_CONSUMPTION
        max_range_km = drone.get("max_range")
        if max_range_km is not None:
            try:
                return float(max_range_km) * SPECIFIC_CONSUMPTION * DOD
            except (ValueError, TypeError):
                pass
        # 默认
        return CAPACITY_DEFAULT_KWH * 1000.0 * DOD

    @staticmethod
    def _segment_energy_wh(p1, p2, p_hover, speed_ms):
        """
        计算单段能耗（物理模型，区分爬升/巡航/下降）
        E_seg = P_seg * t_seg = K * P_h * (dist_3d / speed)
        单位：瓦时(Wh)
        """
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        dz = p2[2] - p1[2]
        dist_3d = math.sqrt(dx * dx + dy * dy + dz * dz)

        if dist_3d < 1e-6 or speed_ms <= 0:
            return 0.0

        # 根据高度变化选择工况系数
        if dz > 0.1:
            K = K_CLIMB      # 爬升
        elif dz < -0.1:
            K = K_DESCENT    # 下降
        else:
            K = K_CRUISE     # 水平巡航

        p_seg = K * p_hover          # 该段功率(W)
        t_seg = dist_3d / speed_ms   # 该段时长(s)
        e_seg = p_seg * t_seg / 3600.0  # Wh = W * s / 3600

        return e_seg

    @staticmethod
    def _segment_time_s(p1, p2, speed_ms):
        """计算单段飞行时间(秒)"""
        dist_3d = math.sqrt(sum((p1[j] - p2[j]) ** 2 for j in range(3)))
        if speed_ms <= 0:
            return 0.0
        return dist_3d / speed_ms

    # ──────────────────────────────────────────────────────────
    #  内部工具
    # ──────────────────────────────────────────────────────────

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
        """在 matplotlib axes 上画换电站标记（绿方块）。"""
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
                text=["\u26a1"],
                textposition="top center",
                textfont=dict(size=14, color="#00E676"),
                name=f"换电站-{swap.get('name', '')}",
                showlegend=True,
            ))
        return traces
