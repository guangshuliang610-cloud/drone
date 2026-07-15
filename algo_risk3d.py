"""
应急响应无人机调度系统 — 3D 风险评估器
文件：algo_risk3d.py

对 RRT* 给出的路径计算风险评分，高风险时在风险场中微调。

三种风险：
  1. 静态建筑风险：路径点到最近建筑中心的距离 d -> risk = exp(-d/tau)，tau=30
  2. 动态碰撞风险：路径点到其他无人机航迹的最短距离 -> risk += exp(-d/tau2)，tau2=20
  3. 地形碰撞风险：路径点 z < terrain_height -> risk += 极大值（直接拒绝）
  total_risk = sum(risk_i) / len(path)

依赖：dispatch_page.BaseAlgorithm，内部调用 algo_rrt_star.Algorithm
"""

import math
import numpy as np
from algo_battery import BatteryManager
from dispatch_page import BaseAlgorithm


class Algorithm(BaseAlgorithm):
    name = "RRT*+Risk3D 风险评估算法"
    desc = "对RRT*路径计算三维风险评分，高风险路段沿风险梯度反方向微调"

    # ── 风险参数 ──
    TAU_BUILDING = 30.0       # 静态建筑风险衰减系数
    TAU_COLLISION = 20.0      # 动态碰撞风险衰减系数
    RISK_THRESHOLD = 0.4      # 风险阈值，超过则微调
    TERRAIN_PENALTY = 100.0   # 地形碰撞惩罚（极大值）
    ADJUST_STEPS = 15         # 微调迭代次数
    ADJUST_LR = 2.0           # 微调步长（沿梯度反方向）

    def solve(self, drones, materials, service_areas, rescue_points, map_obj):
        """
        先调用 RRT* 获取路径，再计算风险评分，若 avg_risk > threshold 则微调高风险路段。
        """

        from algo_battery import BatteryManager

        # ── 延迟导入 RRT* ──
        from algo_rrt_star import Algorithm as RRTStar

        # ── 获取场景数据（不硬编码位置）──
        obstacles = map_obj.get_obstacles() if map_obj else []
        bounds = map_obj.get_bounds() if map_obj else ((-500, 500), (-500, 500), (0, 200))

        # 检测地图是否支持地形高程（山区场景）
        has_terrain = hasattr(map_obj, "get_terrain_height") if map_obj else False

        # ── 调用 RRT* 获取初始路径 ──
        rrt = RRTStar()
        rrt_result = rrt.solve(drones, materials, service_areas, rescue_points, map_obj)

        rrt_trajectories = rrt_result.get("trajectories", [])
        if not rrt_trajectories:
            return rrt_result

        # ── 对每条轨迹计算风险并微调 ──
        adjusted_trajectories = []
        total_risk = 0.0

        for traj_idx, traj in enumerate(rrt_trajectories):
            wps = traj.get("waypoints", [])
            if len(wps) < 2:
                adjusted_trajectories.append(traj)
                continue

            # 提取其他无人机的航迹（用于动态碰撞风险）
            other_trajs = [
                rrt_trajectories[j].get("waypoints", [])
                for j in range(len(rrt_trajectories)) if j != traj_idx
            ]

            # 计算风险评分
            risk_score = self._compute_risk(wps, obstacles, has_terrain, map_obj, other_trajs)
            risk_level = self._risk_level_str(risk_score)

            # 若风险超过阈值，微调高风险路段
            if risk_score > self.RISK_THRESHOLD:
                wps = self._adjust_high_risk(
                    wps, obstacles, has_terrain, map_obj, other_trajs
                )
                # 重新计算微调后的风险
                risk_score = self._compute_risk(wps, obstacles, has_terrain, map_obj, other_trajs)
                risk_level = self._risk_level_str(risk_score)

            # 更新轨迹信息
            traj["waypoints"] = wps
            traj["risk_score"] = round(risk_score, 4)
            traj["risk_level"] = risk_level

            # 重新计算距离（微调后可能变化）
            dist = sum(
                math.sqrt(sum((wps[i]["pos"][k] - wps[i + 1]["pos"][k]) ** 2 for k in range(3)))
                for i in range(len(wps) - 1)
            )
            traj["total_distance"] = round(dist, 2)

            total_risk += risk_score
            adjusted_trajectories.append(traj)

        n = len(adjusted_trajectories)
        avg_risk = total_risk / n if n > 0 else 0.0

        result = {
            "trajectories": adjusted_trajectories,
            "total_time": rrt_result.get("total_time", 0),
            "total_distance": round(sum(t.get("total_distance", 0) for t in adjusted_trajectories), 2),
            "success_rate": rrt_result.get("success_rate", 1.0),
            "avg_risk": round(avg_risk, 4),
            "message": f"RRT*+Risk3D规划完成，{n}架无人机平均风险{avg_risk:.2f}",
        }
        return BatteryManager().apply(drones, service_areas, result)

    # ============================================================
    #  风险计算
    # ============================================================

    def _compute_risk(self, waypoints, obstacles, has_terrain, map_obj, other_trajs):
        """
        计算路径的平均风险评分。
        
        total_risk = sum(risk_i) / len(path)
        risk_i = building_risk + collision_risk + terrain_risk
        """
        if len(waypoints) < 2:
            return 0.0

        total = 0.0
        for wp in waypoints:
            pos = wp["pos"]
            x, y, z = pos[0], pos[1], pos[2]

            # 1. 静态建筑风险
            building_risk = self._static_building_risk(x, y, z, obstacles)

            # 2. 动态碰撞风险
            collision_risk = self._dynamic_collision_risk(x, y, z, other_trajs)

            # 3. 地形碰撞风险
            terrain_risk = self._terrain_collision_risk(x, y, z, has_terrain, map_obj)

            total += building_risk + collision_risk + terrain_risk

        return total / len(waypoints)

    def _static_building_risk(self, x, y, z, obstacles):
        """
        静态建筑风险：路径点到最近建筑中心的水平距离 d，risk = exp(-d/tau)
        同时考虑高度因素：若 z 低于建筑顶面，风险更高。
        返回所有建筑贡献中的最大值。
        """
        if not obstacles:
            return 0.0

        max_risk = 0.0
        for obs in obstacles:
            cx, cy, _ = obs["center"]
            w, h, oz = obs["size"]

            # 水平距离（到建筑中心）
            dx = x - cx
            dy = y - cy
            d_horizontal = math.sqrt(dx * dx + dy * dy)

            # 考虑建筑占据区域：若点在建筑投影内，风险急剧上升
            half_w = w / 2
            half_h = h / 2
            if abs(dx) < half_w and abs(dy) < half_h:
                d_horizontal = d_horizontal * 0.3

            # 高度因素：建筑顶面高度
            z_top = oz
            if z < z_top:
                height_factor = 1.0 + (z_top - z) / max(z_top, 1.0)
            else:
                height_factor = 0.5  # 高于建筑顶面，风险减半

            risk = math.exp(-d_horizontal / self.TAU_BUILDING) * height_factor
            if risk > max_risk:
                max_risk = risk

        return max_risk

    def _dynamic_collision_risk(self, x, y, z, other_trajs):
        """
        动态碰撞风险：路径点到其他无人机航迹的最短距离 d，risk = exp(-d/tau2)
        """
        if not other_trajs:
            return 0.0

        min_dist = float('inf')
        for traj_wps in other_trajs:
            if len(traj_wps) < 2:
                continue
            for wp in traj_wps:
                ox, oy, oz = wp["pos"]
                d = math.sqrt((x - ox) ** 2 + (y - oy) ** 2 + (z - oz) ** 2)
                if d < min_dist:
                    min_dist = d

        if min_dist == float('inf'):
            return 0.0
        return math.exp(-min_dist / self.TAU_COLLISION)

    def _terrain_collision_risk(self, x, y, z, has_terrain, map_obj):
        """
        地形碰撞风险：若 z < terrain_height，风险加极大值。
        """
        if not has_terrain:
            return 0.0
        try:
            terrain_z = float(map_obj.get_terrain_height(np.array([x]), np.array([y]))[0])
            if z < terrain_z:
                return self.TERRAIN_PENALTY
        except Exception:
            pass
        return 0.0

    # ============================================================
    #  风险等级判定
    # ============================================================

    def _risk_level_str(self, risk_score):
        """根据风险分数返回等级标签"""
        if risk_score >= 0.6:
            return "极高"
        elif risk_score >= 0.4:
            return "较高"
        elif risk_score >= 0.2:
            return "中等"
        elif risk_score >= 0.05:
            return "较低"
        else:
            return "低"

    # ============================================================
    #  高风险路段微调
    # ============================================================

    def _adjust_high_risk(self, waypoints, obstacles, has_terrain, map_obj, other_trajs):
        """
        将路径点沿风险梯度反方向偏移，迭代降低风险。
        起点和终点固定不动。
        """
        if len(waypoints) <= 2:
            return waypoints

        # 提取可移动的内部航点
        positions = [list(wp["pos"]) for wp in waypoints]
        labels = [wp.get("label", "") for wp in waypoints]

        for _ in range(self.ADJUST_STEPS):
            max_grad = 0
            max_idx = -1
            grads = []

            for i in range(1, len(positions) - 1):
                # 计算该点的风险梯度（数值微分）
                grad = self._risk_gradient(
                    positions[i], obstacles, has_terrain, map_obj, other_trajs
                )
                grads.append(grad)
                norm = math.sqrt(sum(g ** 2 for g in grad))
                if norm > max_grad:
                    max_grad = norm
                    max_idx = i

            if max_grad < 1e-6 or max_idx < 0:
                break

            # 对最大梯度点进行偏移
            grad = grads[max_idx - 1]
            norm = math.sqrt(sum(g ** 2 for g in grad))
            if norm < 1e-8:
                break

            # 沿梯度反方向偏移
            idx = max_idx
            for k in range(3):
                positions[idx][k] -= self.ADJUST_LR * grad[k] / norm

            # 确保 z > terrain_height
            if has_terrain:
                try:
                    tz = float(map_obj.get_terrain_height(
                        np.array([positions[idx][0]]), np.array([positions[idx][1]])
                    )[0])
                    if positions[idx][2] < tz + 5:
                        positions[idx][2] = tz + 5
                except Exception:
                    pass

        # 重建 waypoints
        adjusted = []
        for i, (pos, label) in enumerate(zip(positions, labels)):
            adjusted.append({"pos": pos, "label": label})
        return adjusted

    def _risk_gradient(self, pos, obstacles, has_terrain, map_obj, other_trajs, eps=1.0):
        """
        用数值微分计算风险梯度。
        grad_k = (risk(pos + eps*e_k) - risk(pos - eps*e_k)) / (2*eps)
        """
        x, y, z = pos
        grad = [0.0, 0.0, 0.0]
        for k, (dx, dy, dz) in enumerate([(eps, 0, 0), (0, eps, 0), (0, 0, eps)]):
            pos_plus = [x + dx, y + dy, z + dz]
            pos_minus = [x - dx, y - dy, z - dz]
            r_plus = self._point_risk(pos_plus, obstacles, has_terrain, map_obj, other_trajs)
            r_minus = self._point_risk(pos_minus, obstacles, has_terrain, map_obj, other_trajs)
            grad[k] = (r_plus - r_minus) / (2 * eps)
        return grad

    def _point_risk(self, pos, obstacles, has_terrain, map_obj, other_trajs):
        """单点风险 = 静态 + 动态 + 地形"""
        x, y, z = pos
        br = self._static_building_risk(x, y, z, obstacles)
        cr = self._dynamic_collision_risk(x, y, z, other_trajs)
        tr = self._terrain_collision_risk(x, y, z, has_terrain, map_obj)
        return br + cr + tr

    # ============================================================
    #  渲染（Matplotlib）
    # ============================================================

    def render_result(self, ax, result):
        """在 3D 画布上绘制轨迹和风险热力点"""
        for t in result.get("trajectories", []):
            wps = t.get("waypoints", [])
            if len(wps) < 2:
                continue
            xs = [w["pos"][0] for w in wps]
            ys = [w["pos"][1] for w in wps]
            zs = [w["pos"][2] for w in wps]
            color = t.get("color", "#1E6FD9")
            name = t.get("drone_name", "?")
            risk = t.get("risk_score", 0)
            risk_text = t.get("risk_level", "")

            # 轨迹线
            ax.plot(
                xs, ys, zs, color=color, linewidth=2.5, alpha=0.9,
                linestyle="-", label=f"{name} ({risk_text})",
            )
            # 起点
            ax.scatter(
                [xs[0]], [ys[0]], [zs[0]], color=color, s=70,
                marker="o", edgecolors="white", linewidths=1.2,
            )
            # 终点
            ax.scatter(
                [xs[-1]], [ys[-1]], [zs[-1]], color=color, s=130,
                marker="*", edgecolors="white", linewidths=1.5,
            )
            # 中间航点（按风险值着色）
            if len(xs) > 2:
                # 根据风险值选择大小
                sizes = [40 + int(risk * 60)] * (len(xs) - 2)
                ax.scatter(
                    xs[1:-1], ys[1:-1], zs[1:-1],
                    c=color, s=sizes, marker="^", alpha=0.7,
                    edgecolors="white", linewidths=0.5,
                )

            # ── 换电站标记 ──
            for swap in t.get("swap_stations", []):
                BatteryManager.render_swap_mPL(ax, [swap])

    # ============================================================
    #  渲染（Plotly）
    # ============================================================

    def render_plotly(self, result):
        """
        返回 Plotly Scatter3d 轨迹列表。
        包含路径 + 风险热力点（按风险等级着色）。
        """
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
            risk = t.get("risk_score", 0)
            risk_text = t.get("risk_level", "")

            # 轨迹线
            traces.append(go.Scatter3d(
                x=xs, y=ys, z=zs, mode="lines",
                line=dict(color=color, width=5),
                name=f"{name} [{risk_text} R={risk:.2f}]",
                showlegend=True,
            ))
            # 起点
            traces.append(go.Scatter3d(
                x=[xs[0]], y=[ys[0]], z=[zs[0]], mode="markers",
                marker=dict(
                    size=8, color=color, symbol="circle",
                    line=dict(color="white", width=1.2),
                ),
                name=f"{name} 起点", showlegend=False,
            ))
            # 终点（菱形）
            traces.append(go.Scatter3d(
                x=[xs[-1]], y=[ys[-1]], z=[zs[-1]], mode="markers",
                marker=dict(
                    size=13, color=color, symbol="diamond",
                    line=dict(color="white", width=1.5),
                ),
                name=f"{name} 投送点", showlegend=False,
            ))
            # 中间航点
            if len(xs) > 2:
                traces.append(go.Scatter3d(
                    x=xs[1:-1], y=ys[1:-1], z=zs[1:-1], mode="markers",
                    marker=dict(size=6, color=color, symbol="diamond", opacity=0.8),
                    showlegend=False,
                ))

            # ── 换电站标记 ──
            swap_stations = t.get("swap_stations", [])
            if swap_stations:
                traces.extend(BatteryManager.render_swap_plotly_swap_traces(swap_stations))

        # ── 风险热力点 ──
        risk_colors = {
            "极高": "#FF0000",
            "较高": "#FF6600",
            "中等": "#FFCC00",
            "较低": "#66CC66",
            "低": "#00CCFF",
        }
        heat_x, heat_y, heat_z, heat_size, heat_color = [], [], [], [], []
        for t in result.get("trajectories", []):
            wps = t.get("waypoints", [])
            risk = t.get("risk_score", 0)
            risk_text = t.get("risk_level", "")
            for wp in wps:
                x, y, z = wp["pos"]
                heat_x.append(x)
                heat_y.append(y)
                heat_z.append(z)
                heat_size.append(max(4, int(risk * 20)))
                heat_color.append(risk_colors.get(risk_text, "#FFCC00"))

        if heat_x:
            traces.append(go.Scatter3d(
                x=heat_x, y=heat_y, z=heat_z, mode="markers",
                marker=dict(
                    size=heat_size,
                    color=heat_color,
                    opacity=0.4,
                    symbol="circle",
                ),
                name="风险热力点",
                showlegend=True,
            ))

        return traces


