"""
应急无人机调度系统 — NSGA-II多目标选择算法
文件：algo_nsga2.py

NSGA-II（Non-dominated Sorting Genetic Algorithm II）：
  - 三目标优化：飞行时间(f1)、风险评分(f2)、能耗(f3)
  - 为每架无人机生成3条候选路径（最短/最安全/折中）
  - 非支配排序 + 拥挤度计算
  - Knee point 选择帕累托前沿最均衡解
  - 兼容城市建筑避障 + 山区地形避障

依赖：dispatch_page.BaseAlgorithm, algo_rrt_star.Algorithm
"""

import math
import random
import numpy as np
from dispatch_page import BaseAlgorithm


class Algorithm(BaseAlgorithm):
    name = "NSGA-II多目标选择算法"
    desc = "帕累托最优路径规划，飞行时间/风险/能耗三目标权衡，推荐+备选方案"

    # ── 风险模型参数 ──
    RISK_TAU = 60.0       # 静态势风险衰减距离(m)
    TERRAIN_MARGIN = 5.0  # 地形安全余量(m)

    # ── 能耗模型参数 ──
    ENERGY_BASE = 0.0008     # 基础能耗率(kWh/m)
    ENERGY_WEIGHT = 0.00005  # 载重能耗系数(kWh/m/kg)
    ENERGY_CLIMB = 0.002     # 爬升能耗率(kWh/m)

    # ── 候选路径参数 ──
    SAFE_Z_OFFSET = 25.0   # 较安全路径高度偏移(m)

    def solve(self, drones, materials, service_areas, rescue_points, map_obj):
        """
        NSGA-II 核心求解
        对每架无人机：
          1. 分配服务区(起点)和救援点(终点)
          2. 生成3条候选路径（RRT*最短/高度偏移最安全/插值折中）
          3. 评估三目标（时间/风险/能耗）
          4. 非支配排序 + 拥挤度计算
          5. 选 knee point 作为推荐解
          6. 返回推荐方案 + 备选方案
        """
        n_drones = len(drones)
        n_rp = len(rescue_points)

        if n_drones == 0 or n_rp == 0:
            return self._empty_result("无无人机或无救援点")

        # ── 从 map_obj 获取场景数据（不硬编码任何位置）
        sa_coords = [(a["x"], a["y"], a["z"]) for a in service_areas]
        rp_coords = [(r["x"], r["y"], r["z"]) for r in rescue_points]
        obstacles = map_obj.get_obstacles() if map_obj else []
        bounds = map_obj.get_bounds() if map_obj else ((-500, 500), (-500, 500), (0, 200))
        has_terrain = hasattr(map_obj, "get_terrain_height") if map_obj else False

        # 颜色表
        colors = [
            "#FF3366", "#00E5FF", "#FFEA00", "#76FF03",
            "#FF6D00", "#E040FB", "#00FFC8", "#FF1744",
            "#7C4DFF", "#FFAB00",
        ]

        # ── 物资分配统计 ──
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

        # ── 延迟导入 RRT* ──
        from algo_rrt_star import Algorithm as RRTStar
        rrt_solver = RRTStar()

        all_trajectories = []
        total_time_rec = 0.0
        total_distance_rec = 0.0
        success_count = 0
        pareto_front_sizes = []

        used_rps = set()
        for d_idx in range(n_drones):
            sa_idx = d_idx % len(sa_coords)
            rp_idx = d_idx % n_rp
            used_rps.add(rp_idx)

            start = sa_coords[sa_idx]
            goal = rp_coords[rp_idx]
            drone = drones[d_idx]

            # ── 步骤1：生成3条候选路径 ──
            candidates = self._generate_candidates(
                start, goal, obstacles, bounds, has_terrain, map_obj, rrt_solver
            )

            if not candidates:
                continue

            # ── 步骤2：评估三目标 ──
            candidate_objs = []
            for path in candidates:
                f1 = self._calc_time(path, drone)
                f2 = self._calc_risk(path, obstacles, map_obj, has_terrain)
                f3 = self._calc_energy(path, drone, rp_materials.get(rp_idx, []), materials)
                candidate_objs.append((f1, f2, f3))

            # ── 步骤3：非支配排序 ──
            fronts = self._non_dominated_sort(candidate_objs)
            if fronts:
                pareto_front_sizes.append(len(fronts[0]))

            # ── 步骤4：从帕累托前沿选 knee point ──
            knee_idx = self._find_knee_point(fronts[0], candidate_objs) if fronts else 0

            # ── 步骤5：构建轨迹条目 ──
            label_map = {0: "A(最短)", 1: "B(最安全)", 2: "C(折中)"}
            for cand_idx, (path, (f1, f2, f3)) in enumerate(zip(candidates, candidate_objs)):
                dist = sum(
                    math.sqrt(sum((path[i][j] - path[i + 1][j]) ** 2 for j in range(3)))
                    for i in range(len(path) - 1)
                )
                speed = drone.get("max_speed", 60) / 3.6
                if speed <= 0:
                    speed = 16.67
                flight_time = dist / speed

                waypoints = [{"pos": list(p), "label": ""} for p in path]
                waypoints[0]["label"] = f"起点: {service_areas[sa_idx]['name']}"
                waypoints[-1]["label"] = f"投送: {rescue_points[rp_idx]['name']}"
                if len(waypoints) > 2:
                    for w in waypoints[1:-1]:
                        w["label"] = "航点"

                # 帕累托等级
                rank = 0
                for fi, front in enumerate(fronts):
                    if cand_idx in front:
                        rank = fi
                        break

                is_recommended = (cand_idx == knee_idx)
                candidate_label = label_map.get(cand_idx, f"候选{cand_idx + 1}")

                traj = {
                    "drone_id": drone.get("id", d_idx + 1),
                    "drone_name": drone.get("name", f"无人机-{d_idx + 1:02d}"),
                    "color": colors[d_idx % len(colors)],
                    "waypoints": waypoints,
                    "total_distance": round(dist, 1),
                    "total_time": round(flight_time, 1),
                    "delivered_materials": rp_materials.get(rp_idx, ["通用物资"]),
                    "pareto_rank": rank,
                    "f1_time": round(f1, 2),
                    "f2_risk": round(f2, 4),
                    "f3_energy": round(f3, 5),
                    "is_recommended": is_recommended,
                    "candidate_label": candidate_label,
                }
                all_trajectories.append(traj)

                # 累加推荐方案的统计
                if is_recommended:
                    total_time_rec += flight_time
                    total_distance_rec += dist
                    success_count += 1

        # ── 构建消息 ──
        msg_parts = []
        for d_idx in range(n_drones):
            did = drones[d_idx].get("id", d_idx + 1)
            rec = [t for t in all_trajectories
                   if t["drone_id"] == did and t["is_recommended"]]
            alts = [t for t in all_trajectories
                    if t["drone_id"] == did and not t["is_recommended"]]
            drone_name = drones[d_idx].get("name", f"无人机-{d_idx + 1:02d}")
            if rec:
                rec_label = rec[0]["candidate_label"]
                alt_labels = "、".join([a["candidate_label"] for a in alts])
                msg_parts.append(f"{drone_name}选{rec_label}(备选{alt_labels})")

        avg_pareto = (sum(pareto_front_sizes) / len(pareto_front_sizes)
                       if pareto_front_sizes else 0)

        if not all_trajectories:
            return self._empty_result("NSGA-II未能生成有效路径")

        message = (
            f"NSGA-II帕累托规划完成，推荐方案：{'；'.join(msg_parts)}。"
            f"平均帕累托前沿大小{avg_pareto:.1f}。"
        )

        success_rate = success_count / n_drones if n_drones > 0 else 0

        return {
            "trajectories": all_trajectories,
            "total_time": round(total_time_rec, 1),
            "total_distance": round(total_distance_rec, 1),
            "success_rate": round(success_rate, 2),
            "pareto_front_count": int(round(avg_pareto)),
            "message": message,
        }

    # ============================================================
    #  候选路径生成
    # ============================================================

    def _generate_candidates(self, start, goal, obstacles, bounds,
                             has_terrain, map_obj, rrt_solver):
        """为每架无人机生成3条候选路径"""
        candidates = []

        # 候选A：RRT*最短路径
        path_a = rrt_solver._rrt_star(
            start, goal, obstacles, bounds, has_terrain, map_obj
        )
        if path_a is None:
            path_a = rrt_solver._fallback_path(start, goal, map_obj, has_terrain)
        path_a = rrt_solver._smooth_path(path_a, obstacles, has_terrain, map_obj)
        candidates.append(path_a)

        # 候选B：较安全路径（高度偏移）
        path_b = self._height_offset_path(path_a, bounds, self.SAFE_Z_OFFSET)
        candidates.append(path_b)

        # 候选C：折中路径（A/B之间插值）
        path_c = self._interpolate_path(path_a, path_b, 0.5)
        candidates.append(path_c)

        return candidates

    @staticmethod
    def _height_offset_path(path, bounds, offset):
        """对路径做高度偏移，得到较安全路径"""
        z_max = bounds[2][1] - 5
        return [[p[0], p[1], min(p[2] + offset, z_max)] for p in path]

    @staticmethod
    def _interpolate_path(path_a, path_b, t):
        """在两条路径之间线性插值"""
        n = min(len(path_a), len(path_b))
        result = []
        for i in range(n):
            x = path_a[i][0] + t * (path_b[i][0] - path_a[i][0])
            y = path_a[i][1] + t * (path_b[i][1] - path_a[i][1])
            z = path_a[i][2] + t * (path_b[i][2] - path_a[i][2])
            result.append([x, y, z])
        if len(path_a) > n:
            result.extend(path_a[n:])
        return result

    # ============================================================
    #  三目标评估
    # ============================================================

    @staticmethod
    def _calc_time(path, drone):
        """f1 = 总飞行时间(秒)"""
        dist = sum(
            math.sqrt(sum((path[i][j] - path[i + 1][j]) ** 2 for j in range(3)))
            for i in range(len(path) - 1)
        )
        speed = drone.get("max_speed", 60) / 3.6
        if speed <= 0:
            speed = 16.67
        return dist / speed

    @staticmethod
    def _dist_point_to_box_3d(px, py, pz, cx, cy, cz, w, h, z_h):
        """
        点到轴对齐包围盒(AABB)的3D距离。
        盒子中心 (cx,cy,cz)，半尺寸 (w/2, h/2, z_h/2)。
        """
        dx = max(0.0, abs(px - cx) - w / 2.0)
        dy = max(0.0, abs(py - cy) - h / 2.0)
        dz = max(0.0, abs(pz - cz) - z_h / 2.0)
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def _calc_risk(self, path, obstacles, map_obj, has_terrain):
        """
        f2 = 总风险评分
        - 静态势风险：路径点到最近障碍物包围盒的3D距离
        - 地形碰撞风险（山区）：路径点低于地形高度+余量
        """
        if not path:
            return 1.0

        total_risk = 0.0
        for p in path:
            # ── 静态势风险（3D距离）
            min_dist = float('inf')
            for obs in obstacles:
                ocx, ocy, ocz = obs['center']
                ow, oh, oz = obs['size']
                d = self._dist_point_to_box_3d(
                    p[0], p[1], p[2], ocx, ocy, ocz, ow, oh, oz
                )
                min_dist = min(min_dist, d)

            if min_dist < float('inf'):
                total_risk += math.exp(-min_dist / self.RISK_TAU)

            # ── 地形碰撞风险（山区）
            if has_terrain and map_obj:
                try:
                    terrain_z = map_obj.get_terrain_height(
                        np.array([p[0]]), np.array([p[1]])
                    )
                    if isinstance(terrain_z, np.ndarray):
                        terrain_z = float(terrain_z[0])
                    if p[2] < terrain_z + self.TERRAIN_MARGIN:
                        total_risk += 1.0
                except Exception:
                    pass

        return total_risk / len(path)

    def _calc_energy(self, path, drone, mat_names, all_materials):
        """
        f3 = 总能耗(kWh)
        - 基础能耗：距离 × 基础能耗率
        - 载重额外能耗：距离 × 载重 × 系数
        - 爬升额外能耗：总爬升高度 × 爬升系数
        """
        if not path or len(path) < 2:
            return 0.0

        total_dist = sum(
            math.sqrt(sum((path[i][j] - path[i + 1][j]) ** 2 for j in range(3)))
            for i in range(len(path) - 1)
        )

        # 载重
        payload = sum(
            m.get("weight", 0.0)
            for m in all_materials
            if m["name"] in mat_names
        )

        # 基础能耗
        energy = total_dist * self.ENERGY_BASE

        # 载重额外能耗
        energy += total_dist * payload * self.ENERGY_WEIGHT

        # 爬升额外能耗
        climb = sum(
            max(0.0, path[i + 1][2] - path[i][2])
            for i in range(len(path) - 1)
        )
        energy += climb * self.ENERGY_CLIMB

        return energy

    # ============================================================
    #  非支配排序 + Knee Point
    # ============================================================

    def _non_dominated_sort(self, objectives):
        """
        非支配排序（NSGA-II 标准算法）
        objectives: list of (f1, f2, f3) — 均为越小越好
        returns: list of fronts，每个 front 是目标索引的列表
        """
        n = len(objectives)
        if n == 0:
            return []

        dominated_count = [0] * n
        dominates = [[] for _ in range(n)]

        for i in range(n):
            for j in range(i + 1, n):
                if self._dominates(objectives[i], objectives[j]):
                    dominates[i].append(j)
                    dominated_count[j] += 1
                elif self._dominates(objectives[j], objectives[i]):
                    dominates[j].append(i)
                    dominated_count[i] += 1

        fronts = []
        current_front = [i for i in range(n) if dominated_count[i] == 0]

        while current_front:
            fronts.append(current_front)
            next_front = []
            for i in current_front:
                for j in dominates[i]:
                    dominated_count[j] -= 1
                    if dominated_count[j] == 0:
                        next_front.append(j)
            current_front = next_front

        return fronts

    @staticmethod
    def _dominates(a, b):
        """
        解 a 支配 解 b 当且仅当：
        - a 的所有目标都不差于 b
        - 至少一个目标严格好于 b
        """
        at_least_one_better = False
        for ai, bi in zip(a, b):
            if ai > bi:
                return False
            if ai < bi:
                at_least_one_better = True
        return at_least_one_better

    def _find_knee_point(self, front, objectives):
        """
        Knee point（拐点）：
        帕累托前沿中距离理想点（各目标最优值）曼哈顿距离最小的解。
        """
        if not front:
            return 0
        if len(front) == 1:
            return front[0]

        front_objs = [objectives[i] for i in front]
        n_obj = len(front_objs[0])
        ideal = [min(obj[k] for obj in front_objs) for k in range(n_obj)]

        best_idx = front[0]
        best_dist = float('inf')
        for i in front:
            dist = sum(abs(objectives[i][k] - ideal[k]) for k in range(n_obj))
            if dist < best_dist:
                best_dist = dist
                best_idx = i

        return best_idx

    # ============================================================
    #  结果构建
    # ============================================================

    def _empty_result(self, msg):
        return {
            "trajectories": [],
            "total_time": 0,
            "total_distance": 0,
            "success_rate": 0,
            "message": msg,
        }

    # ============================================================
    #  渲染（Matplotlib）
    # ============================================================

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

            is_recommended = t.get("is_recommended", False)
            cand_label = t.get("candidate_label", "")

            if is_recommended:
                ax.plot(
                    xs, ys, zs, color=color, linewidth=2.5, alpha=0.9,
                    linestyle="-", label=name,
                )
                ax.scatter(
                    [xs[0]], [ys[0]], [zs[0]], color=color, s=60,
                    marker="o", edgecolors="white", linewidths=1,
                )
                ax.scatter(
                    [xs[-1]], [ys[-1]], [zs[-1]], color=color, s=120,
                    marker="*", edgecolors="white", linewidths=1.5,
                )
            else:
                ax.plot(
                    xs, ys, zs, color=color, linewidth=1.5, alpha=0.35,
                    linestyle="--", label=f"{name} {cand_label}",
                )
                ax.scatter(
                    [xs[0]], [ys[0]], [zs[0]], color=color, s=30,
                    marker="o", alpha=0.35,
                )
                ax.scatter(
                    [xs[-1]], [ys[-1]], [zs[-1]], color=color, s=60,
                    marker="*", alpha=0.35,
                )

            if len(xs) > 2:
                ax.scatter(
                    xs[1:-1], ys[1:-1], zs[1:-1], color=color, s=25,
                    marker="^", alpha=0.5 if is_recommended else 0.2,
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

            is_recommended = t.get("is_recommended", False)
            cand_label = t.get("candidate_label", "")

            if is_recommended:
                traces.append(go.Scatter3d(
                    x=xs, y=ys, z=zs, mode="lines",
                    line=dict(color=color, width=5, dash="solid"),
                    name=name, showlegend=True,
                ))
                traces.append(go.Scatter3d(
                    x=[xs[0]], y=[ys[0]], z=[zs[0]], mode="markers",
                    marker=dict(
                        size=7, color=color, symbol="circle",
                        line=dict(color="white", width=1),
                    ),
                    name=f"{name} 起点", showlegend=False,
                ))
                traces.append(go.Scatter3d(
                    x=[xs[-1]], y=[ys[-1]], z=[zs[-1]], mode="markers",
                    marker=dict(
                        size=12, color=color, symbol="diamond",
                        line=dict(color="white", width=1.5),
                    ),
                    name=f"{name} 投送点", showlegend=False,
                ))
            else:
                traces.append(go.Scatter3d(
                    x=xs, y=ys, z=zs, mode="lines",
                    line=dict(color=color, width=3, dash="dash"),
                    name=f"{name} {cand_label}",
                    showlegend=True, opacity=0.4,
                ))
                traces.append(go.Scatter3d(
                    x=[xs[0]], y=[ys[0]], z=[zs[0]], mode="markers",
                    marker=dict(
                        size=5, color=color, symbol="circle", opacity=0.4,
                    ),
                    showlegend=False,
                ))
                traces.append(go.Scatter3d(
                    x=[xs[-1]], y=[ys[-1]], z=[zs[-1]], mode="markers",
                    marker=dict(
                        size=8, color=color, symbol="diamond", opacity=0.4,
                    ),
                    showlegend=False,
                ))

            if len(xs) > 2:
                traces.append(go.Scatter3d(
                    x=xs[1:-1], y=ys[1:-1], z=zs[1:-1], mode="markers",
                    marker=dict(
                        size=5, color=color, symbol="diamond",
                        opacity=0.7 if is_recommended else 0.3,
                    ),
                    showlegend=False,
                ))
        return traces
