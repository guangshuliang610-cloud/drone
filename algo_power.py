"""
应急无人机调度系统 — 电量约束器
文件：algo_power.py

算法职责：
  内部调用 RRT* 获取无碰路径，再统一委托给共享 BatteryManager 模块
  做电量累计、换电站插入与时间惩罚。
  BatteryManager 负责 per-drone 物理参数（电池容量、换电时间按模型查表、
  安全电量阈值等），本算法只保留渲染与调度接口。

参数：详见 algo_battery.py (BatteryManager)

依赖：dispatch_page.BaseAlgorithm，algo_rrt_star.Algorithm，algo_battery.BatteryManager
兼容：城市地震 / 山区避障 双场景
"""

from dispatch_page import BaseAlgorithm


class Algorithm(BaseAlgorithm):
    name = "电量约束算法"
    desc = "RRT*+电量约束，逐段累计功耗，超出航程时自动插入换电站"

    # ── 颜色表（与 RRT* 一致）──
    COLORS = [
        "#FF3366", "#00E5FF", "#FFEA00", "#76FF03",
        "#FF6D00", "#E040FB", "#00FFC8", "#FF1744",
        "#7C4DFF", "#FFAB00",
    ]

    def solve(self, drones, materials, service_areas, rescue_points, map_obj):
        """
        1) 调用 RRT* 获取基础无碰路径
        2) 委托 BatteryManager 执行电量累计 / 换电站插入
        """
        # ── 延迟导入 RRT* 与共享电量管理模块 ──
        from algo_battery import BatteryManager
        from algo_rrt_star import Algorithm as RRTStar

        rrt = RRTStar()
        result = rrt.solve(drones, materials, service_areas, rescue_points, map_obj)

        if not result.get("trajectories"):
            result["total_swaps"] = 0
            result["message"] = "电量约束：无可用轨迹"
            return result

        return BatteryManager().apply(drones, service_areas, result)

    # ============================================================
    #  渲染（matplotlib）
    # ============================================================

    def render_result(self, ax, result):
        """在 3D 画布上绘制轨迹（含换电站）"""
        for t in result.get("trajectories", []):
            wps = t.get("waypoints", [])
            if len(wps) < 2:
                continue
            xs = [w["pos"][0] for w in wps]
            ys = [w["pos"][1] for w in wps]
            zs = [w["pos"][2] for w in wps]
            color = t.get("color", "#1E6FD9")
            name = t.get("drone_name", "?")

            # Fallback 路径用虚线+红色区分
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
