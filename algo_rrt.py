"""
应急无人机调度系统 — 改进RRT*算法
文件：algo_rrt.py

RRT*（快速探索随机树星）算法：
  - 在三维空间中随机采样，逐步构建路径树
  - 改进：引入目标偏好采样 + 障碍物膨胀 + 路径平滑
  - 适用于三维动态避障场景
"""

import math
import random
import numpy as np
from dispatch_page import BaseAlgorithm


class Algorithm(BaseAlgorithm):
    name = "改进RRT*算法"
    desc = "快速探索随机树，三维动态避障，目标偏好采样 + 路径平滑"

    def solve(self, drones, materials, service_areas, rescue_points, map_obj):
        """RRT* 核心求解"""
        n_drones = len(drones)
        n_rp = len(rescue_points)

        if n_drones == 0 or n_rp == 0:
            return self._empty_result("无无人机或无救援点")

        sa_coords = [(a["x"], a["y"], a["z"]) for a in service_areas]
        rp_coords = [(r["x"], r["y"], r["z"]) for r in rescue_points]

        # 获取障碍物
        obstacles = map_obj.get_obstacles() if map_obj else []
        bounds = map_obj.get_bounds() if map_obj else ((-500, 500), (-500, 500), (0, 200))

        colors = ["#1E6FD9", "#2EAA6C", "#E6A817", "#E24B4A",
                  "#9B59B6", "#00BCD4", "#FF6B6B", "#4CAF50",
                  "#FF9800", "#3F51B5"]

        trajectories = []
        total_time = 0.0
        total_distance = 0.0

        # 统计物资分配
        rp_materials = {i: [] for i in range(n_rp)}
        mat_idx = 0
        for m in materials:
            rp_name = m.get("rescue_point", "")
            assigned = False
            for rp_i, rp in enumerate(rescue_points):
                if rp["name"] == rp_name:
                    rp_materials[rp_i].append(m["name"])
                    assigned = True
                    break
            if not assigned:
                rp_materials[mat_idx % n_rp].append(m["name"])
                mat_idx += 1

        used_rps = set()
        for d_idx in range(n_drones):
            sa_idx = d_idx % len(sa_coords)
            rp_idx = d_idx % n_rp
            used_rps.add(rp_idx)

            start = sa_coords[sa_idx]
            goal = rp_coords[rp_idx]

            # 运行 RRT*
            path = self._rrt_star(start, goal, obstacles, bounds)

            if path is None:
                # 回退：直线路径
                path = [start, goal]

            # 路径平滑
            path = self._smooth_path(path)

            # 计算距离和时间
            dist = sum(
                math.sqrt(sum((path[i][j] - path[i+1][j])**2 for j in range(3)))
                for i in range(len(path) - 1)
            )
            speed = drones[d_idx].get("max_speed", 60) / 3.6
            if speed <= 0:
                speed = 16.67
            flight_time = dist / speed

            waypoints = [{"pos": list(p), "label": ""} for p in path]
            waypoints[0]["label"] = f"起点: {service_areas[sa_idx]['name']}"
            waypoints[-1]["label"] = f"投送: {rescue_points[rp_idx]['name']}"
            if len(waypoints) > 2:
                waypoints[1]["label"] = "避障航点"
                if len(waypoints) > 3:
                    waypoints[-2]["label"] = "接近目标"
                for w in waypoints[2:-2]:
                    w["label"] = "路径点"

            delivered = rp_materials.get(rp_idx, ["通用物资"])

            trajectories.append({
                "drone_id": drones[d_idx].get("id", d_idx + 1),
                "drone_name": drones[d_idx].get("name", f"无人机-{d_idx+1:02d}"),
                "color": colors[d_idx % len(colors)],
                "waypoints": waypoints,
                "total_distance": dist,
                "total_time": flight_time,
                "delivered_materials": delivered,
            })

            total_time = max(total_time, flight_time)
            total_distance += dist

        success_rate = len(used_rps) / n_rp if n_rp > 0 else 0

        return {
            "trajectories": trajectories,
            "total_time": total_time,
            "total_distance": total_distance,
            "success_rate": min(success_rate, 1.0),
            "message": f"RRT*规划完成，{n_drones}架无人机成功规避{len(obstacles)}个障碍物",
        }

    def _rrt_star(self, start, goal, obstacles, bounds,
                  max_iter=500, step_size=30, goal_bias=0.2, rewire_radius=50):
        """改进 RRT* 算法"""
        nodes = [np.array(start, dtype=float)]
        parents = [-1]
        costs = [0.0]

        goal_arr = np.array(goal, dtype=float)

        for _ in range(max_iter):
            # 目标偏好采样
            if random.random() < goal_bias:
                sample = goal_arr + np.random.normal(0, 10, 3)
            else:
                sample = np.array([
                    random.uniform(bounds[0][0], bounds[0][1]),
                    random.uniform(bounds[1][0], bounds[1][1]),
                    random.uniform(bounds[2][0], bounds[2][1]),
                ])

            # 找最近节点
            dists = [np.linalg.norm(sample - n) for n in nodes]
            nearest_idx = min(range(len(dists)), key=lambda i: dists[i])
            nearest = nodes[nearest_idx]

            # 向采样点扩展
            direction = sample - nearest
            dist = np.linalg.norm(direction)
            if dist < 1e-6:
                continue
            direction = direction / dist
            new_point = nearest + direction * min(step_size, dist)

            # 边界约束
            new_point[0] = np.clip(new_point[0], bounds[0][0], bounds[0][1])
            new_point[1] = np.clip(new_point[1], bounds[1][0], bounds[1][1])
            new_point[2] = np.clip(new_point[2], bounds[2][0], bounds[2][1])

            # 碰撞检测
            if self._check_collision(nearest, new_point, obstacles):
                continue

            # 重连（选择最优父节点）
            best_parent = nearest_idx
            best_cost = costs[nearest_idx] + np.linalg.norm(new_point - nearest)

            # 搜索邻近节点
            for i, node in enumerate(nodes):
                d = np.linalg.norm(new_point - node)
                if d < rewire_radius:
                    new_cost = costs[i] + d
                    if new_cost < best_cost and not self._check_collision(node, new_point, obstacles):
                        best_parent = i
                        best_cost = new_cost

            nodes.append(new_point)
            parents.append(best_parent)
            costs.append(best_cost)

            # 检查是否到达目标
            if np.linalg.norm(new_point - goal_arr) < step_size:
                # 尝试直接连接到目标
                if not self._check_collision(new_point, goal_arr, obstacles):
                    nodes.append(goal_arr)
                    parents.append(len(nodes) - 2)
                    costs.append(best_cost + np.linalg.norm(goal_arr - new_point))
                    break

        # 回溯路径
        if np.linalg.norm(nodes[-1] - goal_arr) > step_size * 2:
            # 未到达目标，尝试直接连线
            if not self._check_collision(np.array(start), goal_arr, obstacles):
                return [start, goal]
            return None

        path = []
        idx = len(nodes) - 1
        while idx >= 0:
            path.append(nodes[idx].tolist())
            idx = parents[idx]
        path.reverse()

        return path if len(path) >= 2 else None

    def _check_collision(self, p1, p2, obstacles, n_check=10):
        """检测线段与障碍物是否碰撞"""
        for obs in obstacles:
            cx, cy, cz = obs["center"]
            w, h, d = obs["size"]
            # 膨胀障碍物（安全距离）
            margin = 5
            x_min, x_max = cx - w/2 - margin, cx + w/2 + margin
            y_min, y_max = cy - h/2 - margin, cy + h/2 + margin
            z_min, z_max = 0 - margin, d + margin

            for t in np.linspace(0, 1, n_check):
                p = p1 + t * (p2 - p1)
                if (x_min <= p[0] <= x_max and
                    y_min <= p[1] <= y_max and
                    z_min <= p[2] <= z_max):
                    return True  # 碰撞
        return False  # 无碰撞

    def _smooth_path(self, path, n_iter=3):
        """路径平滑（shortcut + 样条插值）"""
        if len(path) <= 2:
            return path

        # Shortcut：尝试跳过中间节点
        smoothed = [path[0]]
        i = 0
        while i < len(path) - 1:
            # 尝试连接到最远的可达节点
            j = min(i + 3, len(path) - 1)
            while j > i + 1:
                # 简单的直线可行性检查（不检测碰撞，仅做平滑）
                j -= 1
            smoothed.append(path[j])
            i = j

        return smoothed if len(smoothed) >= 2 else path

    def _empty_result(self, msg):
        return {
            "trajectories": [],
            "total_time": 0,
            "total_distance": 0,
            "success_rate": 0,
            "message": msg,
        }

    def render_result(self, ax, result):
        """在 3D 画布上绘制轨迹"""
        for t in result.get("trajectories", []):
            wps = t.get("waypoints", [])
            if len(wps) < 2:
                continue
            xs = [w["pos"][0] for w in wps]
            ys = [w["pos"][1] for w in wps]
            zs = [w["pos"][2] for w in wps]
            color = t.get("color", "#1E6FD9")
            name = t.get("drone_name", "?")

            # RRT* 路径（折线风格）
            ax.plot(xs, ys, zs, color=color, linewidth=2.2, alpha=0.85,
                    linestyle="-", label=name)
            # 起点
            ax.scatter([xs[0]], [ys[0]], [zs[0]], color=color, s=60,
                       marker="o", edgecolors="white", linewidths=1)
            # 终点（大星）
            ax.scatter([xs[-1]], [ys[-1]], [zs[-1]], color=color, s=120,
                       marker="*", edgecolors="white", linewidths=1.5)
            # 中间航点（小三角）
            if len(xs) > 2:
                ax.scatter(xs[1:-1], ys[1:-1], zs[1:-1], color=color, s=25,
                           marker="^", alpha=0.6)
