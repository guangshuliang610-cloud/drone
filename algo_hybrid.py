"""
应急无人机调度系统 — 混合启发式算法
文件：algo_hhybrid.py

双阶段混合启发式算法：
  - 第一阶段：遗传算法（GA）进行全局任务分配（哪架无人机去哪个救援点）
  - 第二阶段：蚁群算法（ACO）进行局部路径优化（经过哪些航点）
  - 结合全局搜索和局部优化的优势
"""

import math
import random
import numpy as np
from dispatch_page import BaseAlgorithm


class Algorithm(BaseAlgorithm):
    name = "混合启发式算法"
    desc = "双阶段混合启发式，遗传算法全局分配 + 蚁群算法局部路径优化"

    def solve(self, drones, materials, service_areas, rescue_points, map_obj):
        """混合启发式核心求解"""
        n_drones = len(drones)
        n_rp = len(rescue_points)
        n_sa = len(service_areas)

        if n_drones == 0 or n_rp == 0:
            return self._empty_result("无无人机或无救援点")

        sa_coords = [(a["x"], a["y"], a["z"]) for a in service_areas]
        rp_coords = [(r["x"], r["y"], r["z"]) for r in rescue_points]
        rp_priorities = [r.get("priority", 2) for r in rescue_points]

        # ══════════════════════════════════════════════════
        #  第一阶段：遗传算法 — 全局任务分配
        # ══════════════════════════════════════════════════
        assignment = self._ga_assign(
            n_drones, n_sa, n_rp, sa_coords, rp_coords, rp_priorities
        )

        # ══════════════════════════════════════════════════
        #  第二阶段：蚁群算法 — 局部路径优化
        # ══════════════════════════════════════════════════
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

        trajectories = []
        total_time = 0.0
        total_distance = 0.0
        used_rps = set()

        for d_idx in range(n_drones):
            sa_idx = assignment[d_idx]["sa"]
            rp_idx = assignment[d_idx]["rp"]
            used_rps.add(rp_idx)

            start = sa_coords[sa_idx]
            goal = rp_coords[rp_idx]

            # ACO 路径优化
            path = self._aco_path(start, goal)

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
                    label = f"投送: {rescue_points[rp_idx]['name']}"
                elif i == 1:
                    label = "ACO优化航点"
                else:
                    label = "路径节点"
                waypoints.append({"pos": list(p), "label": label})

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
            "message": f"混合启发式完成：GA分配+ACO路径优化，{n_drones}架→{len(used_rps)}个救援点",
        }

    # ── 第一阶段：遗传算法 ──────────────────────────────
    def _ga_assign(self, n_drones, n_sa, n_rp, sa_coords, rp_coords,
                   rp_priorities, n_pop=40, n_gen=80, mutation_rate=0.15):
        """遗传算法求解最优任务分配"""
        # 染色体编码：[sa_0, rp_0, sa_1, rp_1, ...] 每架无人机分配 (服务区, 救援点)
        chrom_len = n_drones * 2

        # 初始化种群
        pop = []
        for _ in range(n_pop):
            chrom = []
            for d in range(n_drones):
                chrom.append(random.randint(0, n_sa - 1))  # 起始服务区
                chrom.append(random.randint(0, n_rp - 1))  # 目标救援点
            pop.append(chrom)

        def fitness(chrom):
            total = 0.0
            for d in range(n_drones):
                sa_idx = chrom[d * 2] % n_sa
                rp_idx = chrom[d * 2 + 1] % n_rp
                dist = math.sqrt(sum(
                    (a - b)**2 for a, b in zip(sa_coords[sa_idx], rp_coords[rp_idx])
                ))
                # 距离 + 优先级权重
                priority_weight = 1 + (3 - rp_priorities[rp_idx]) * 0.3
                total += dist * priority_weight
            # 多样性奖励（覆盖更多救援点）
            covered = len(set(chrom[d*2+1] for d in range(n_drones)))
            total -= covered * 200  # 覆盖越多越好
            return -total  # 最小化

        # 进化循环
        for gen in range(n_gen):
            scores = [fitness(c) for c in pop]

            # 选择（锦标赛）
            new_pop = []
            # 保留精英
            elite_idx = np.argmin(scores)
            new_pop.append(pop[elite_idx][:])

            while len(new_pop) < n_pop:
                # 锦标赛选择
                t1 = random.sample(range(n_pop), min(3, n_pop))
                t2 = random.sample(range(n_pop), min(3, n_pop))
                p1 = pop[min(t1, key=lambda i: scores[i])]
                p2 = pop[min(t2, key=lambda i: scores[i])]

                # 交叉
                if random.random() < 0.8:
                    point = random.randint(1, chrom_len - 1)
                    child = p1[:point] + p2[point:]
                else:
                    child = p1[:]

                # 变异
                for i in range(chrom_len):
                    if random.random() < mutation_rate:
                        if i % 2 == 0:
                            child[i] = random.randint(0, n_sa - 1)
                        else:
                            child[i] = random.randint(0, n_rp - 1)

                new_pop.append(child)

            pop = new_pop

        # 返回最优解
        scores = [fitness(c) for c in pop]
        best = pop[np.argmin(scores)]

        assignment = []
        for d in range(n_drones):
            assignment.append({
                "sa": best[d * 2] % n_sa,
                "rp": best[d * 2 + 1] % n_rp,
            })
        return assignment

    # ── 第二阶段：蚁群算法 ──────────────────────────────
    def _aco_path(self, start, goal, n_ants=20, n_iter=50, alpha=1.0, beta=3.0, rho=0.3):
        """蚁群算法优化路径（在起点和终点之间找最优中间航点）"""
        sx, sy, sz = start
        gx, gy, gz = goal
        mid_z = max(sz, gz) + 30

        # 候选航点（网格采样）
        n_candidates = 8
        candidates = []
        for i in range(n_candidates):
            t = (i + 1) / (n_candidates + 1)
            cx = sx + t * (gx - sx) + random.uniform(-30, 30)
            cy = sy + t * (gy - sy) + random.uniform(-30, 30)
            cz = mid_z + random.uniform(-10, 10)
            candidates.append((cx, cy, cz))

        n_nodes = len(candidates)

        # 信息素矩阵
        pheromone = np.ones((n_nodes, n_nodes))

        # 距离矩阵
        all_points = [start] + candidates + [goal]
        n_all = len(all_points)
        dist_matrix = np.zeros((n_all, n_all))
        for i in range(n_all):
            for j in range(n_all):
                dist_matrix[i][j] = math.sqrt(
                    sum((all_points[i][k] - all_points[j][k])**2 for k in range(3))
                )

        best_path = None
        best_length = float('inf')

        for _ in range(n_iter):
            ant_paths = []
            ant_lengths = []

            for _ in range(n_ants):
                # 蚂蚁从起点出发，选择中间航点，到达终点
                visited = set()
                path = [0]  # 起点索引
                current = 0

                for step in range(min(n_nodes, 5)):  # 最多选 5 个中间点
                    available = [j for j in range(1, n_all - 1) if j not in visited]
                    if not available:
                        break

                    # 计算转移概率
                    probs = []
                    for j in available:
                        tau = pheromone[min(current, n_nodes-1)][min(j-1, n_nodes-1)] ** alpha
                        eta = (1.0 / (dist_matrix[current][j] + 1e-6)) ** beta
                        probs.append(tau * eta)

                    total = sum(probs)
                    if total < 1e-10:
                        break
                    probs = [p / total for p in probs]

                    next_node = np.random.choice(available, p=probs)
                    path.append(next_node)
                    visited.add(next_node)
                    current = next_node

                path.append(n_all - 1)  # 终点

                # 计算路径长度
                length = sum(dist_matrix[path[i]][path[i+1]] for i in range(len(path) - 1))
                ant_paths.append(path)
                ant_lengths.append(length)

                if length < best_length:
                    best_length = length
                    best_path = path[:]

            # 更新信息素
            pheromone *= (1 - rho)
            for path, length in zip(ant_paths, ant_lengths):
                for i in range(len(path) - 1):
                    a = min(path[i], n_nodes - 1)
                    b = min(path[i+1] - 1, n_nodes - 1)
                    if 0 <= a < n_nodes and 0 <= b < n_nodes:
                        pheromone[a][b] += 1.0 / length

        # 构建最终路径
        if best_path:
            result_path = [all_points[i] for i in best_path]
        else:
            result_path = [start, [sx, sy, mid_z], [gx, gy, mid_z], goal]

        return result_path

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

            # 混合路径（实线 + 渐变效果）
            ax.plot(xs, ys, zs, color=color, linewidth=2.5, alpha=0.9,
                    linestyle="-", label=name)
            # 起点
            ax.scatter([xs[0]], [ys[0]], [zs[0]], color=color, s=70,
                       marker="o", edgecolors="white", linewidths=1.2)
            # 终点
            ax.scatter([xs[-1]], [ys[-1]], [zs[-1]], color=color, s=130,
                       marker="*", edgecolors="white", linewidths=1.5)
            # ACO 优化航点（五角星）
            if len(xs) > 2:
                ax.scatter(xs[1:-1], ys[1:-1], zs[1:-1], color=color, s=50,
                           marker="p", alpha=0.7)
