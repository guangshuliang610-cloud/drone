"""
应急无人机调度系统 — 电量约束器
文件：algo_power.py

算法职责：
  在 RRT* 无碰路径基础上，逐段累计电量消耗。
  当剩余电量不足以飞行下一段时，在最近 service_area 插入换电站航点，
  并施加换电时间惩罚，然后重置电量继续。

参数：
  e_consume = 0.08  (每米电量消耗)
  max_e     = 100   (满电量)
  swap_time = 1.8   (换电时间惩罚，秒)

依赖：dispatch_page.BaseAlgorithm，内部延迟调用 algo_rrt_star.Algorithm
兼容：城市地震 / 山区避障 双场景
"""

import math
import numpy as np
from dispatch_page import BaseAlgorithm


class Algorithm(BaseAlgorithm):
    name = "电量约束算法"
    desc = "RRT*+电量约束，逐段累计功耗，超出航程时自动插入换电站"

    # ── 电量约束参数 ──
    E_CONSUME = 0.08   # 每米电量消耗 (电量单位/米)
    MAX_E = 100.0      # 满电量
    SWAP_TIME = 1.8    # 换电时间惩罚 (秒)

    # ── 颜色表（与 RRT* 一致）──
    COLORS = [
        "#FF3366", "#00E5FF", "#FFEA00", "#76FF03",
        "#FF6D00", "#E040FB", "#00FFC8", "#FF1744",
        "#7C4DFF", "#FFAB00",
    ]

    def solve(self, drones, materials, service_areas, rescue_points, map_obj):
        """
        1) 调用 RRT* 获取基础无碰路径
        2) 逐段电量累计，超出航程时插入换电站
        """
        # ── 延迟导入 RRT* ──
        from algo_rrt_star import Algorithm as RRTStar

        rrt = RRTStar()
        result = rrt.solve(drones, materials, service_areas, rescue_points, map_obj)

        if not result.get("trajectories"):
            result["total_swaps"] = 0
            result["message"] = "电量约束：无可用轨迹"
            return result

        # ── 提取服务区坐标（用于换电站选址）──
        sa_coords = [(a["x"], a["y"], a["z"]) for a in service_areas]
        sa_names = [a["name"] for a in service_areas]

        total_swaps = 0

        for t_idx, traj in enumerate(result["trajectories"]):
            waypoints = traj.get("waypoints", [])
            if len(waypoints) < 2:
                traj["swap_stations"] = []
                traj["swap_count"] = 0
                continue

            new_waypoints = [waypoints[0]]
            swap_stations = []
            current_energy = self.MAX_E
            extra_time = 0.0

            for i in range(len(waypoints) - 1):
                p1 = waypoints[i]["pos"]
                p2 = waypoints[i + 1]["pos"]
                seg_dist = math.sqrt(
                    sum((p1[j] - p2[j]) ** 2 for j in range(3))
                )
                need = seg_dist * self.E_CONSUME

                # ── 电量不足 → 插入换电站 ──
                if current_energy < need:
                    # 找最近服务区
                    cur_pos = new_waypoints[-1]["pos"]
                    sa_idx = self._nearest_sa(cur_pos, sa_coords)
                    sa_pos = list(sa_coords[sa_idx])
                    sa_name = sa_names[sa_idx]

                    # 插入换电站航点
                    swap_wp = {
                        "pos": sa_pos,
                        "label": f"换电站-{sa_name}",
                    }
                    new_waypoints.append(swap_wp)
                    swap_stations.append({
                        "pos": sa_pos,
                        "name": f"换电站-{sa_name}",
                    })

                    # 重置电量 + 时间惩罚
                    current_energy = self.MAX_E
                    extra_time += self.SWAP_TIME
                    total_swaps += 1

                # 飞行消耗
                new_waypoints.append(waypoints[i + 1])
                current_energy -= need

            traj["waypoints"] = new_waypoints
            traj["swap_stations"] = swap_stations
            traj["swap_count"] = len(swap_stations)
            traj["total_time"] = traj.get("total_time", 0.0) + extra_time

        # ── 更新汇总字段 ──
        result["total_swaps"] = total_swaps
        result["total_time"] = max(
            (t.get("total_time", 0.0) for t in result["trajectories"]),
            default=0.0,
        )

        n_drones = len(result["trajectories"])
        if total_swaps > 0:
            result["message"] = (
                f"RRT*+电量约束完成，{n_drones}架无人机，"
                f"共插入{total_swaps}个换电站"
            )
        else:
            result["message"] = (
                f"RRT*+电量约束完成，{n_drones}架无人机，"
                f"电量充足无需换电"
            )

        return result

    # ============================================================
    #  工具
    # ============================================================

    @staticmethod
    def _nearest_sa(pos, sa_coords):
        """返回距离 pos 最近的服务区索引"""
        min_dist = float("inf")
        best = 0
        for i, sa in enumerate(sa_coords):
            d = math.sqrt(sum((pos[j] - sa[j]) ** 2 for j in range(3)))
            if d < min_dist:
                min_dist = d
                best = i
        return best

    # ============================================================
    #  渲染（Matplotlib）
    # ============================================================

    def render_result(self, ax, result):
        """在 3D 画布上绘制轨迹与换电站"""
        for t in result.get("trajectories", []):
            wps = t.get("waypoints", [])
            if len(wps) < 2:
                continue
            xs = [w["pos"][0] for w in wps]
            ys = [w["pos"][1] for w in wps]
            zs = [w["pos"][2] for w in wps]
            color = t.get("color", "#1E6FD9")
            name = t.get("drone_name", "?")

            line_style = "--" if t.get("is_fallback", False) else "-"
            line_alpha = 0.6 if t.get("is_fallback", False) else 0.85

            # 轨迹线
            ax.plot(
                xs, ys, zs, color=color, linewidth=2.2, alpha=line_alpha,
                linestyle=line_style, label=name,
            )
            # 起点
            ax.scatter(
                [xs[0]], [ys[0]], [zs[0]], color=color, s=60,
                marker="o", edgecolors="white", linewidths=1,
            )
            # 终点（大星）
            ax.scatter(
                [xs[-1]], [ys[-1]], [zs[-1]], color=color, s=120,
                marker="*", edgecolors="white", linewidths=1.5,
            )
            # 换电站 — 绿色方块
            for swap in t.get("swap_stations", []):
                sp = swap["pos"]
                ax.scatter(
                    [sp[0]], [sp[1]], [sp[2]],
                    color="#00E676", s=120, marker="s",
                    edgecolors="white", linewidths=1.5,
                    label=f"换电站-{name}", zorder=5,
                )
            # 普通中间航点（排除换电站）
            swap_positions = {
                tuple(s["pos"]) for s in t.get("swap_stations", [])
            }
            mid_x, mid_y, mid_z = [], [], []
            for w in wps[1:-1]:
                if tuple(w["pos"]) not in swap_positions:
                    mid_x.append(w["pos"][0])
                    mid_y.append(w["pos"][1])
                    mid_z.append(w["pos"][2])
            if mid_x:
                ax.scatter(
                    mid_x, mid_y, mid_z, color=color, s=25,
                    marker="^", alpha=0.6,
                )

    # ============================================================
    #  渲染（Plotly）
    # ============================================================

    def render_plotly(self, result):
        """返回 Plotly Scatter3d 轨迹列表"""
        import plotly.graph_objects as go

        traces = []
        for t in result.get("trajectories", []):
            wps = t.get("waypoints", [])
            if len(wps) < 2:
                continue
            xs = [w["pos"][0] for w in wps]
            ys = [w["pos"][1] for w in wps]
            zs = [w["pos"][2] for w in wps]
            color = t.get("color", "#1E6FD9")
            name = t.get("drone_name", "?")

            line_dash = "dash" if t.get("is_fallback", False) else "solid"

            # 轨迹线
            traces.append(go.Scatter3d(
                x=xs, y=ys, z=zs, mode="lines",
                line=dict(color=color, width=5, dash=line_dash),
                name=name, showlegend=True,
            ))
            # 起点
            traces.append(go.Scatter3d(
                x=[xs[0]], y=[ys[0]], z=[zs[0]], mode="markers",
                marker=dict(
                    size=7, color=color, symbol="circle",
                    line=dict(color="white", width=1),
                ),
                name=f"{name} 起点", showlegend=False,
            ))
            # 终点（菱形）
            traces.append(go.Scatter3d(
                x=[xs[-1]], y=[ys[-1]], z=[zs[-1]], mode="markers",
                marker=dict(
                    size=12, color=color, symbol="diamond",
                    line=dict(color="white", width=1.5),
                ),
                name=f"{name} 投送点", showlegend=False,
            ))
            # 换电站 — 绿色方块 + 闪电符号
            for swap in t.get("swap_stations", []):
                sp = swap["pos"]
                traces.append(go.Scatter3d(
                    x=[sp[0]], y=[sp[1]], z=[sp[2]], mode="markers+text",
                    marker=dict(
                        size=12, color="#00E676", symbol="square",
                        line=dict(color="white", width=2),
                    ),
                    text=["⚡"],
                    textposition="top center",
                    textfont=dict(size=14, color="#00E676"),
                    name=f"换电站 {swap.get('name', '')}",
                    showlegend=True,
                ))
            # 普通中间航点（排除换电站）
            swap_positions = {
                tuple(s["pos"]) for s in t.get("swap_stations", [])
            }
            mid_x, mid_y, mid_z = [], [], []
            for w in wps[1:-1]:
                if tuple(w["pos"]) not in swap_positions:
                    mid_x.append(w["pos"][0])
                    mid_y.append(w["pos"][1])
                    mid_z.append(w["pos"][2])
            if mid_x:
                traces.append(go.Scatter3d(
                    x=mid_x, y=mid_y, z=mid_z, mode="markers",
                    marker=dict(
                        size=5, color=color, symbol="diamond", opacity=0.7
                    ),
                    showlegend=False,
                ))
        return traces
