"""
应急无人机调度系统 — DQN强化学习算法
文件：algo_dqn.py

DQN（Deep Q-Network）算法：
  - 将调度问题建模为马尔可夫决策过程
  - 状态：当前无人机位置、剩余物资、救援点状态
  - 动作：选择下一个目标救援点
  - 奖励：考虑距离、优先级、时间窗
  - 使用 Q-table 近似（无需深度学习框架）
"""

import math
import random
import numpy as np
from dispatch_page import BaseAlgorithm


class Algorithm(BaseAlgorithm):
    name = "DQN强化学习"
    desc = "深度强化学习，智能决策与路径规划，Q-table近似实现"

    def solve(self, drones, materials, service_areas, rescue_points, map_obj):
        """DQN 核心求解"""
        n_drones = len(drones)
        n_rp = len(rescue_points)
        n_sa = len(service_areas)

        if n_drones == 0 or n_rp == 0:
            return self._empty_result("无无人机或无救援点")

        sa_coords = [(a["x"], a["y"], a["z"]) for a in service_areas]
        rp_coords = [(r["x"], r["y"], r["z"]) for r in rescue_points]
        rp_priorities = [r.get("priority", 2) for r in rescue_points]

        # ── 构建 Q-table ──
        # 状态：(当前服务区, 已访问救援点集合)
        # 动作：选择下一个救援点
        q_table = self._train_q_table(
            sa_coords, rp_coords, rp_priorities, drones, n_episodes=300
        )

        # ── 使用训练好的 Q-table 规划路径 ──
        colors = ["#1E6FD9", "#2EAA6C", "#E6A817", "#E24B4A",
                  "#9B59B6", "#00BCD4", "#FF6B6B", "#4CAF50",
                  "#FF9800", "#3F51B5"]

        # 物资分配
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

        # 为每架无人机选择最优目标
        trajectories = []
        total_time = 0.0
        total_distance = 0.0
        used_rps = set()

        for d_idx in range(n_drones):
            sa_idx = d_idx % n_sa

            # 从 Q-table 选择最优救援点
            best_rp = self._select_action(q_table, sa_idx, n_rp, used_rps)
            if best_rp is None:
                best_rp = d_idx % n_rp
            used_rps.add(best_rp)

            start = sa_coords[sa_idx]
            goal = rp_coords[best_rp]

            # 生成路径（带中途调整点，模拟 DQN 的实时决策）
            path = self._generate_dqn_path(start, goal, sa_coords, rp_coords)

            dist = sum(
                math.sqrt(sum((path[i][j] - path[i+1][j])**2 for j in range(3)))
                for i in range(len(path) - 1)
            )
            speed = drones[d_idx].get("max_speed", 60) / 3.6
            if speed <= 0:
                speed = 16.67
            flight_time = dist / speed

            waypoints = []
            for i, p in enumerate(path):
                if i == 0:
                    label = f"起点: {service_areas[sa_idx]['name']}"
                elif i == len(path) - 1:
                    label = f"投送: {rescue_points[best_rp]['name']}"
                elif i == 1:
                    label = "DQN决策点"
                else:
                    label = "路径修正"
                waypoints.append({"pos": list(p), "label": label})

            delivered = rp_materials.get(best_rp, ["通用物资"])

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
            "message": f"DQN决策完成，{n_drones}架无人机智能分配至{len(used_rps)}个救援点",
        }

    def _train_q_table(self, sa_coords, rp_coords, rp_priorities, drones,
                        n_episodes=300, alpha=0.1, gamma=0.9, epsilon=0.3):
        """训练 Q-table（简化版 DQN）"""
        n_sa = len(sa_coords)
        n_rp = len(rp_coords)

        # Q-table: Q[sa_idx][rp_idx] = 价值
        q_table = np.zeros((n_sa, n_rp))

        for ep in range(n_episodes):
            # 随机起始服务区
            sa_idx = random.randint(0, n_sa - 1)
            visited = set()

            for step in range(n_rp):
                # ε-greedy 策略
                if random.random() < epsilon * (1 - ep / n_episodes):
                    # 探索：随机选择
                    available = [r for r in range(n_rp) if r not in visited]
                    if not available:
                        break
                    rp_idx = random.choice(available)
                else:
                    # 利用：选择 Q 值最大的
                    available = [r for r in range(n_rp) if r not in visited]
                    if not available:
                        break
                    rp_idx = max(available, key=lambda r: q_table[sa_idx][r])

                # 计算奖励
                reward = self._calc_reward(
                    sa_coords[sa_idx], rp_coords[rp_idx],
                    rp_priorities[rp_idx], len(visited)
                )

                # 更新 Q 值
                old_q = q_table[sa_idx][rp_idx]
                next_max = 0
                if len(visited) + 1 < n_rp:
                    next_available = [r for r in range(n_rp) if r not in visited and r != rp_idx]
                    if next_available:
                        next_max = max(q_table[sa_idx][r] for r in next_available)

                q_table[sa_idx][rp_idx] = old_q + alpha * (reward + gamma * next_max - old_q)

                visited.add(rp_idx)

        return q_table

    def _calc_reward(self, sa, rp, priority, n_visited):
        """计算奖励（距离短 + 优先级高 = 奖励大）"""
        dist = math.sqrt(sum((a - b)**2 for a, b in zip(sa, rp)))
        # 距离惩罚（距离越远惩罚越大）
        dist_penalty = -dist / 1000
        # 优先级奖励（priority 越小越紧急，奖励越大）
        priority_reward = (3 - priority) * 5
        # 覆盖奖励
        coverage_bonus = n_visited * 2

        return dist_penalty + priority_reward + coverage_bonus

    def _select_action(self, q_table, sa_idx, n_rp, used_rps):
        """从 Q-table 选择最优未访问救援点"""
        available = [r for r in range(n_rp) if r not in used_rps]
        if not available:
            return None
        return max(available, key=lambda r: q_table[sa_idx][r])

    def _generate_dqn_path(self, start, goal, sa_coords, rp_coords):
        """生成 DQN 风格的路径（带决策中途点）"""
        sx, sy, sz = start
        gx, gy, gz = goal

        mid_z = max(sz, gz) + 35

        # DQN 特征：中途有一个决策调整点（模拟实时重规划）
        mid_x = (sx + gx) / 2 + random.uniform(-20, 20)
        mid_y = (sy + gy) / 2 + random.uniform(-20, 20)

        path = [
            start,
            [sx, sy, mid_z],                    # 爬升
            [mid_x, mid_y, mid_z + 10],         # DQN 决策点（可能偏移）
            [gx, gy, mid_z],                     # 接近目标
            [gx, gy, max(gz, 10)],               # 下降
            goal,                                 # 投送
        ]

        return path

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

            # DQN 路径（虚线风格，表示实时决策）
            ax.plot(xs, ys, zs, color=color, linewidth=2, alpha=0.85,
                    linestyle="--", label=name)
            # 起点
            ax.scatter([xs[0]], [ys[0]], [zs[0]], color=color, s=60,
                       marker="o", edgecolors="white", linewidths=1)
            # 终点
            ax.scatter([xs[-1]], [ys[-1]], [zs[-1]], color=color, s=120,
                       marker="*", edgecolors="white", linewidths=1.5)
            # 决策点（菱形标记）
            if len(xs) > 2:
                ax.scatter(xs[1:-1], ys[1:-1], zs[1:-1], color=color, s=40,
                           marker="D", alpha=0.7)
