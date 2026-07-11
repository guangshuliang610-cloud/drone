"""
应急无人机调度系统 — 改进HHO算法（哈里斯鹰优化）
文件：algo_hho.py

HHO 算法模拟哈里斯鹰的协同捕猎行为：
  - 探索阶段：随机搜索全局空间
  - 开发阶段：围捕猎物（全局最优解）
  - 改进：引入自适应逃逸能量 + Lévy 飞行增强全局搜索
"""

import math
import random
import numpy as np
from dispatch_page import BaseAlgorithm


class Algorithm(BaseAlgorithm):
    name = "改进HHO算法"
    desc = "哈里斯鹰优化算法，全局路径寻优，自适应逃逸能量 + Lévy飞行增强"

    def solve(self, drones, materials, service_areas, rescue_points, map_obj):
        """
        HHO 核心求解：
        1. 将「哪架无人机去哪个救援点送什么物资」编码为解向量
        2. 用 HHO 优化总配送时间（飞行距离 / 速度 + 中转时间）
        3. 返回各无人机的飞行轨迹
        """
        n_drones = len(drones)
        n_rp = len(rescue_points)
        n_materials = len(materials)

        if n_drones == 0 or n_rp == 0:
            return self._empty_result("无无人机或无救援点")

        # ── 构建距离矩阵 ──
        # 节点：服务区(起点) + 救援点(终点)
        sa_coords = [(a["x"], a["y"], a["z"]) for a in service_areas]
        rp_coords = [(r["x"], r["y"], r["z"]) for r in rescue_points]

        # ── HHO 参数 ──
        n_hawks = min(50, max(20, n_drones * n_rp * 5))
        max_iter = 100

        # ── 解的维度：每架无人机分配的救援点序列 ──
        dim = n_drones * 2  # 每架无人机: [起始服务区索引, 目标救援点索引]

        # ── 初始化鹰群 ──
        hawks = np.random.uniform(0, 1, (n_hawks, dim))
        fitness = np.full(n_hawks, float('inf'))

        # 评估函数
        def evaluate(hawk):
            return self._eval_solution(
                hawk, n_drones, sa_coords, rp_coords,
                drones, materials, rescue_points, service_areas
            )

        # 初始评估
        for i in range(n_hawks):
            fitness[i] = evaluate(hawks[i])

        best_idx = np.argmin(fitness)
        rabbit = hawks[best_idx].copy()
        rabbit_fitness = fitness[best_idx]

        # ── HHO 主循环 ──
        for t in range(max_iter):
            E0 = 2 * (1 - t / max_iter)  # 逃逸能量（线性递减）

            for i in range(n_hawks):
                E = E0 * (2 * random.random() - 1)  # 自适应逃逸能量
                J = 2 * (1 - random.random())        # 跳跃强度

                if abs(E) >= 1:
                    # ── 探索阶段：随机搜索 ──
                    rand_idx = random.randint(0, n_hawks - 1)
                    rand_hawk = hawks[rand_idx]
                    q = random.random()
                    if q < 0.5:
                        # 随机包围
                        r1, r2 = random.random(), random.random()
                        hawks[i] = rand_hawk - abs(rand_hawk - 2*r1*hawks[i]) * r2
                    else:
                        # Lévy 飞行
                        levy = self._levy_flight(dim)
                        hawks[i] = (rabbit - hawks[i].mean()) - levy * np.random.uniform(0, 1, dim)
                else:
                    # ── 开发阶段：围捕猎物 ──
                    r = random.random()
                    if r >= 0.5 and abs(E) < 0.5:
                        # 硬围捕
                        hawks[i] = rabbit - E * abs(rabbit - hawks[i])
                    elif r >= 0.5 and abs(E) >= 0.5:
                        # 软围捕
                        hawks[i] = rabbit - E * abs(J * rabbit - hawks[i])
                    elif r < 0.5 and abs(E) >= 0.5:
                        # 渐进式快速俯冲
                        Y = rabbit - E * abs(J * rabbit - hawks[i])
                        Z = Y + np.random.uniform(-0.5, 0.5, dim) * self._levy_flight(dim)
                        if evaluate(Y) < evaluate(hawks[i]):
                            hawks[i] = Y
                        elif evaluate(Z) < evaluate(hawks[i]):
                            hawks[i] = Z
                    else:
                        # 快速俯冲（软围捕变体）
                        Y = rabbit - E * abs(J * rabbit - hawks[i].mean())
                        hawks[i] = (Y - np.random.uniform(-0.5, 0.5, dim) *
                                    self._levy_flight(dim))

                # 边界约束
                hawks[i] = np.clip(hawks[i], 0, 1)

                # 评估
                fitness[i] = evaluate(hawks[i])

                if fitness[i] < rabbit_fitness:
                    rabbit = hawks[i].copy()
                    rabbit_fitness = fitness[i]

        # ── 从最优解构建轨迹 ──
        return self._build_result(
            rabbit, n_drones, sa_coords, rp_coords,
            drones, materials, rescue_points, service_areas
        )

    def _levy_flight(self, dim, beta=1.5):
        """Lévy 飞行（增强全局搜索能力）"""
        sigma = (math.gamma(1 + beta) * math.sin(math.pi * beta / 2) /
                 (math.gamma((1 + beta) / 2) * beta * 2**((beta - 1) / 2))) ** (1 / beta)
        u = np.random.normal(0, sigma, dim)
        v = np.random.normal(0, 1, dim)
        step = u / (np.abs(v) ** (1 / beta))
        return step * 0.01

    def _eval_solution(self, hawk, n_drones, sa_coords, rp_coords,
                       drones, materials, rescue_points, service_areas):
        """评估解的适应度（总配送时间）"""
        total_time = 0.0
        n_sa = len(sa_coords)
        n_rp = len(rp_coords)

        for d_idx in range(n_drones):
            # 起始服务区
            sa_idx = int(hawk[d_idx * 2] * (n_sa - 1e-6)) % n_sa
            # 目标救援点
            rp_idx = int(hawk[d_idx * 2 + 1] * (n_rp - 1e-6)) % n_rp

            start = sa_coords[sa_idx]
            end = rp_coords[rp_idx]

            dist = math.sqrt(sum((a - b)**2 for a, b in zip(start, end)))
            speed = drones[d_idx].get("max_speed", 60) / 3.6  # km/h -> m/s
            if speed <= 0:
                speed = 16.67

            flight_time = dist / speed
            total_time += flight_time

        return total_time

    def _build_result(self, hawk, n_drones, sa_coords, rp_coords,
                      drones, materials, rescue_points, service_areas):
        """从解向量构建调度结果"""
        trajectories = []
        total_time = 0.0
        total_distance = 0.0
        n_sa = len(sa_coords)
        n_rp = len(rp_coords)

        colors = ["#FF3366", "#00E5FF", "#FFEA00", "#76FF03",
                  "#FF6D00", "#E040FB", "#00FFC8", "#FF1744",
                  "#7C4DFF", "#FFAB00"]

        # 统计每个救援点被分配了哪些物资
        rp_materials = {i: [] for i in range(n_rp)}
        mat_idx = 0
        for m in materials:
            rp_name = m.get("rescue_point", "")
            for rp_i, rp in enumerate(rescue_points):
                if rp["name"] == rp_name:
                    rp_materials[rp_i].append(m["name"])
                    break
            else:
                # 未指定救援点，按顺序分配
                rp_materials[mat_idx % n_rp].append(m["name"])
                mat_idx += 1

        used_rps = set()
        for d_idx in range(n_drones):
            sa_idx = int(hawk[d_idx * 2] * (n_sa - 1e-6)) % n_sa
            rp_idx = int(hawk[d_idx * 2 + 1] * (n_rp - 1e-6)) % n_rp
            used_rps.add(rp_idx)

            start = sa_coords[sa_idx]
            end = rp_coords[rp_idx]

            dist = math.sqrt(sum((a - b)**2 for a, b in zip(start, end)))
            speed = drones[d_idx].get("max_speed", 60) / 3.6
            if speed <= 0:
                speed = 16.67
            flight_time = dist / speed

            # 高度中间点（爬升 → 平飞 → 下降）
            mid_z = max(start[2], end[2]) + 30

            waypoints = [
                {"pos": list(start), "label": f"起点: {service_areas[sa_idx]['name']}"},
                {"pos": [start[0], start[1], mid_z], "label": "爬升"},
                {"pos": [(start[0]+end[0])/2, (start[1]+end[1])/2, mid_z], "label": "巡航"},
                {"pos": [end[0], end[1], mid_z], "label": "下降"},
                {"pos": list(end), "label": f"投送: {rescue_points[rp_idx]['name']}"},
            ]

            delivered = rp_materials.get(rp_idx, [])
            if not delivered:
                delivered = ["通用物资"]

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
            "message": f"HHO优化完成，{n_drones}架无人机分配至{len(used_rps)}个救援点",
        }

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

            # 轨迹线
            ax.scatter(xs, ys, zs, c=color, s=10, alpha=0.9, label=name, zorder=10, depthshade=False)
            ax.plot(xs, ys, zs, color=color, linewidth=1.5, alpha=0.6, zorder=10)
            # 起点
            ax.scatter([xs[0]], [ys[0]], [zs[0]], color=color, s=60, marker="o", edgecolors="white", linewidths=1)
            # 终点
            ax.scatter([xs[-1]], [ys[-1]], [zs[-1]], color=color, s=100, marker="*", edgecolors="white", linewidths=1)
            # 中间航点
            if len(xs) > 2:
                ax.scatter(xs[1:-1], ys[1:-1], zs[1:-1], color=color, s=20, marker="^", alpha=0.6)
