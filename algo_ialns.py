"""
应急无人机调度系统 — IALNS 自适应大邻域搜索算法（VRP 任务分配器）
文件：algo_ialns.py

IALNS（Adaptive Large Neighborhood Search）算法：
  - 第一阶段：求解 VRP 任务分配（哪架无人机去哪个救援点）
      · 构建代价矩阵 cost[i][j] = distance(sa_i -> rp_j) / drone_speed + penalty(priority)
      · 初始解：pair assignment（每架无人机分配一个唯一救援点）
      · Adaptive Large Neighborhood Search（500~1000 次迭代）
          a. destroy(k=3): 随机移除 3 个分配
          b. repair: 对每个被移除点，找到代价增量最小的无人机和最优插入位置
          c. 若新解优于当前解 -> 接受；否则按 Metropolis 准则概率接受
  - 第二阶段：对每对 (drone, rescue_point) 用 RRT* 规划实际三维避障路径
  - 兼容城市建筑避障 + 山区地形避障

依赖：dispatch_page.BaseAlgorithm，内部延迟导入 algo_rrt_star
"""

import math
import random
import numpy as np
from algo_battery import BatteryManager
from dispatch_page import BaseAlgorithm


class Algorithm(BaseAlgorithm):
    name = "IALNS VRP 任务分配"
    desc = "自适应大邻域搜索，VRP任务分配优化 + RRT*路径规划"

    # ── IALNS 核心参数 ──
    MAX_ITER = 700          # 大邻域搜索迭代次数
    DESTROY_RATIO = 0.3     # 每次破坏的分配比例
    K_DESTROY = 3           # 每次移除的分配数
    PENALTY = {0: 0, 1: 50, 2: 200, 3: 1000}  # 优先级惩罚（距离单位：m）
    TEMP_INIT = 500.0       # Metropolis 初始温度
    COOLING = 0.995         # 冷却因子
    MIN_TEMP = 1e-3         # 最低温度

    def solve(self, drones, materials, service_areas, rescue_points, map_obj):
        """
        IALNS 核心求解
          1. 构建代价矩阵（距离 + 优先级惩罚）
          2. 初始 pair assignment
          3. Adaptive Large Neighborhood Search 优化分配
          4. 对每对 (drone, rp) 调用 RRT* 规划三维避障路径
        """
        from algo_battery import BatteryManager

        n_drones = len(drones)
        n_rp = len(rescue_points)
        n_sa = len(service_areas)

        if n_drones == 0 or n_rp == 0:
            return self._empty_result("无无人机或无救援点")

        # ── 从 map_obj 获取场景数据（不硬编码任何位置）──
        sa_coords = [(a["x"], a["y"], a["z"]) for a in service_areas]
        rp_coords = [(r["x"], r["y"], r["z"]) for r in rescue_points]
        rp_priorities = [r.get("priority", 2) for r in rescue_points]

        # 检测地图是否支持地形高程（山区场景）
        has_terrain = hasattr(map_obj, "get_terrain_height") if map_obj else False
        obstacles = map_obj.get_obstacles() if map_obj else []
        bounds = map_obj.get_bounds() if map_obj else ((-500, 500), (-500, 500), (0, 200))

        # ── 构建代价矩阵 ──
        # ?? ?? SA??? RP ???????? SA ?????? SA ????
        sa_index = {a["name"]: i for i, a in enumerate(service_areas)}
        rp_index = {r["name"]: i for i, r in enumerate(rescue_points)}
        sa_valid_rps = {}
        for m in materials:
            sa_name = m.get("service_area", "")
            rp_name = m.get("rescue_point", "")
            sa_i = sa_index.get(sa_name)
            rp_i = rp_index.get(rp_name)
            if sa_i is not None and rp_i is not None:
                sa_valid_rps.setdefault(sa_i, set()).add(rp_i)

        cost_matrix = self._build_cost_matrix(
            sa_coords, rp_coords, rp_priorities, drones, has_terrain, map_obj, sa_valid_rps=sa_valid_rps
        )

        # ── 第一阶段：IALNS 求解最优分配 ──
        assignment = self._ialns_optimize(
            cost_matrix, n_drones, n_rp, n_sa
        )

        # ── 第二阶段：RRT* 路径规划 ──
        # 延迟导入避免循环依赖
        try:
            from algo_rrt_star import Algorithm as RRTStarAlgo
            rrt_algo = RRTStarAlgo()
        except ImportError:
            rrt_algo = None

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

        trajectories = []
        total_time = 0.0
        total_distance = 0.0
        used_rps = set()
        fallback_count = 0

        for d_idx in range(n_drones):
            sa_idx = assignment[d_idx]["sa"]
            rp_idx = assignment[d_idx]["rp"]
            # rp=-1 ??? SA ?????????
            if rp_idx == -1:
                continue
            used_rps.add(rp_idx)

            start = sa_coords[sa_idx]
            goal = rp_coords[rp_idx]
            # ── 使用 RRT* 规划路径 ──
            path = None
            is_fallback = False
            if rrt_algo is not None:
                path = rrt_algo._rrt_star(
                    start, goal, obstacles, bounds, has_terrain, map_obj
                )
                if path is None:
                    path = rrt_algo._fallback_path(
                        start, goal, map_obj, has_terrain
                    )
                    is_fallback = True
                    fallback_count += 1
                path = rrt_algo._smooth_path(
                    path, obstacles, has_terrain, map_obj
                )
            else:
                # RRT* 不可用时使用直飞路径
                path = self._fallback_path(start, goal, map_obj, has_terrain)
                is_fallback = True
                fallback_count += 1

            # 计算距离和时间
            dist = sum(
                math.sqrt(sum((path[i][j] - path[i + 1][j]) ** 2 for j in range(3)))
                for i in range(len(path) - 1)
            )
            speed = drones[d_idx].get("max_speed", 60) / 3.6
            if speed <= 0:
                speed = 16.67
            flight_time = dist / speed

            # 构建航点标签
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
                "drone_name": drones[d_idx].get("name", f"无人机-{d_idx + 1:02d}"),
                "color": colors[d_idx % len(colors)],
                "waypoints": waypoints,
                "total_distance": dist,
                "total_time": flight_time,
                "delivered_materials": delivered,
                "is_fallback": is_fallback,
            })

            total_time = max(total_time, flight_time)
            total_distance += dist

        success_rate = len(used_rps) / n_rp if n_rp > 0 else 0

        # 构建消息
        msg_parts = [
            f"IALNS+RRT*规划完成，{n_drones}架无人机分配至{len(used_rps)}个救援点"
        ]
        if fallback_count > 0:
            msg_parts.append(f"{fallback_count}架无人机使用飞越模式(RRT*未收敛)")
        msg = "；".join(msg_parts)

        result = {
            "trajectories": trajectories,
            "total_time": total_time,
            "total_distance": total_distance,
            "success_rate": len(used_rps) / n_rp if n_rp > 0 else 0,
            "message": msg_parts[0] + ("，" + "，".join(msg_parts[1:]) if len(msg_parts) > 1 else ""),
        }
        return BatteryManager().apply(drones, service_areas, result)

    # ============================================================
    #  代价矩阵构建
    # ============================================================

    def _build_cost_matrix(self, sa_coords, rp_coords, rp_priorities,
                           drones, has_terrain, map_obj,
                           sa_valid_rps=None):
        """
        ?????? cost[i][j] = distance(sa_i -> rp_j) / drone_speed + penalty(priority)
        sa_valid_rps: dict[sa_idx, set(rp_idx)] ? ?? SA ??? RP ???
                      ? (sa,rp) ?????????? inf??????
        """
        n_sa = len(sa_coords)
        n_rp = len(rp_coords)
        cost_matrix = np.zeros((n_sa, n_rp))

        # ????????????????
        avg_speed = 16.67  # m/s (60 km/h)
        if drones:
            speeds = [d.get("max_speed", 60) / 3.6 for d in drones if d.get("max_speed", 60) > 0]
            if speeds:
                avg_speed = sum(speeds) / len(speeds)

        for i in range(n_sa):
            for j in range(n_rp):
                # SA i ???? RP j ????????????????
                if sa_valid_rps is not None and j not in sa_valid_rps.get(i, set()):
                    cost_matrix[i][j] = float('inf')
                    continue

                dx = sa_coords[i][0] - rp_coords[j][0]
                dy = sa_coords[i][1] - rp_coords[j][1]
                dz = sa_coords[i][2] - rp_coords[j][2]
                dist = math.sqrt(dx * dx + dy * dy + dz * dz)

                priority = rp_priorities[j] if j < len(rp_priorities) else 2
                penalty = self.PENALTY.get(priority, 0)
                cost_matrix[i][j] = dist / avg_speed + penalty

        return cost_matrix

    # ============================================================
    #  IALNS 核心算法
    # ============================================================

    def _ialns_optimize(self, cost_matrix, n_drones, n_rp, n_sa):
        """
        自适应大邻域搜索求解最优分配

        返回:
            assignment: list of dict, 每个元素 {"sa": sa_idx, "rp": rp_idx}
                        长度恒为 n_drones（每架无人机一个分配）
        """
        # ── 初始解：pair assignment（每架无人机分配一个救援点）──
        current_sol = self._initial_solution(cost_matrix, n_drones, n_rp, n_sa)
        current_cost = self._solution_cost(current_sol, cost_matrix)

        best_sol = [dict(a) for a in current_sol]
        best_cost = current_cost

        # ── 自适应大邻域搜索 ──
        temp = self.TEMP_INIT
        k_destroy = min(self.K_DESTROY, max(1, int(n_drones * self.DESTROY_RATIO)))

        for iteration in range(self.MAX_ITER):
            # ── Destroy: 随机移除 k 个救援点（对应无人机变为未分配）──
            destroyed_rps, partial_sol, destroyed_drone_idxs = self._destroy(
                current_sol, k_destroy, n_drones
            )

            # ── Repair: 贪心插入被移除的救援点 ──
            new_sol = self._repair(
                partial_sol, destroyed_rps, destroyed_drone_idxs,
                cost_matrix, n_sa, n_rp
            )
            new_cost = self._solution_cost(new_sol, cost_matrix)

            # ── 接受准则 ──
            delta = new_cost - current_cost
            if delta < 0:
                current_sol = [dict(a) for a in new_sol]
                current_cost = new_cost
                if new_cost < best_cost:
                    best_sol = [dict(a) for a in new_sol]
                    best_cost = new_cost
            else:
                # Metropolis 准则
                if temp > self.MIN_TEMP and random.random() < math.exp(-delta / temp):
                    current_sol = [dict(a) for a in new_sol]
                    current_cost = new_cost

            # 冷却
            temp *= self.COOLING
            temp = max(temp, self.MIN_TEMP)

        return best_sol

    def _initial_solution(self, cost_matrix, n_drones, n_rp, n_sa):
        """
        ????pair assignment
        ???????????????????????????
        ?? SA ??? RP ???? inf?? SA ?????rp ?? -1????
        """
        assignment = []
        for d_idx in range(n_drones):
            sa_idx = d_idx % n_sa
            best_rp = -1
            best_cost = float("inf")
            for rp_idx in range(n_rp):
                c = cost_matrix[sa_idx][rp_idx]
                if c < best_cost:
                    best_cost = c
                    best_rp = rp_idx
            if best_cost == float("inf"):
                best_rp = -1  # ? SA ?????????
            assignment.append({"sa": sa_idx, "rp": best_rp})
        return assignment
    def _solution_cost(self, solution, cost_matrix):
        """计算解的总代价"""
        total = 0.0
        for assign in solution:
            sa_idx = assign["sa"]
            rp_idx = assign["rp"]
            if 0 <= sa_idx < cost_matrix.shape[0] and 0 <= rp_idx < cost_matrix.shape[1]:
                total += cost_matrix[sa_idx][rp_idx]
        return total

    def _destroy(self, solution, k, n_drones):
        """
        随机移除 k 个分配

        返回:
            destroyed_rps: 被移除的救援点索引列表
            partial_sol: 移除后的部分解（保持长度，被移除的 drone rp=-1）
            destroyed_drone_idxs: 被移除的无人机索引列表
        """
        n = len(solution)
        if n == 0:
            return [], [], []

        k = min(k, n)
        destroy_indices = set(random.sample(range(n), k))

        destroyed_rps = []
        destroyed_drone_idxs = []
        partial_sol = []
        for i, assign in enumerate(solution):
            if i in destroy_indices:
                destroyed_rps.append(assign["rp"])
                destroyed_drone_idxs.append(i)
                # 保持长度，标记为未分配
                partial_sol.append({"sa": assign["sa"], "rp": -1})
            else:
                partial_sol.append(dict(assign))

        return destroyed_rps, partial_sol, destroyed_drone_idxs

    def _repair(self, partial_sol, destroyed_rps, destroyed_drone_idxs,
                cost_matrix, n_sa, n_rp):
        """
        贪心修复：对每个被移除的救援点，找到代价增量最小的无人机进行分配

        策略：
        1. 将被移除的 rp 按优先级惩罚从大到小排序（优先分配高优先级点）
        2. 对每个 rp，找到分配代价增量最小的无人机（可以是未分配的，也可以替换已有分配）
        3. 替换后释放的 rp 重新加入待分配队列
        """
        new_sol = [dict(a) for a in partial_sol]
        # 所有无人机索引
        all_drone_idxs = list(range(len(new_sol)))

        # 待分配的救援点队列（按优先级惩罚从大到小排序，优先处理高优先级）
        pending_rps = sorted(
            destroyed_rps,
            key=lambda rp: self.PENALTY.get(max(0, min(rp, 3)), 0),
            reverse=True
        )

        for rp in pending_rps:
            best_drone = -1
            best_cost_inc = float("inf")

            for d_idx in all_drone_idxs:
                sa_idx = new_sol[d_idx]["sa"]
                current_rp = new_sol[d_idx]["rp"]

                if current_rp == -1:
                    # 未分配的无人机：代价增量 = 新分配的代价
                    cost_inc = cost_matrix[sa_idx][rp]
                else:
                    # 已有分配的无人机：代价增量 = 新代价 - 旧代价
                    old_cost = cost_matrix[sa_idx][current_rp]
                    new_cost = cost_matrix[sa_idx][rp]
                    cost_inc = new_cost - old_cost

                if cost_inc < best_cost_inc:
                    best_cost_inc = cost_inc
                    best_drone = d_idx

            if best_drone >= 0:
                old_rp = new_sol[best_drone]["rp"]
                new_sol[best_drone]["rp"] = rp
                # 如果替换了已有分配且不是-1，将旧rp重新加入待分配队列
                if old_rp != -1 and old_rp not in pending_rps:
                    pending_rps.append(old_rp)

        # 确保所有无人机都有分配（未分配的随机分配）
        for d_idx in all_drone_idxs:
            if new_sol[d_idx]["rp"] == -1:
                sa_idx = new_sol[d_idx]["sa"]
                best_rp = 0
                best_cost = float("inf")
                for rp_idx in range(n_rp):
                    c = cost_matrix[sa_idx][rp_idx]
                    if c < best_cost:
                        best_cost = c
                        best_rp = rp_idx
                new_sol[d_idx]["rp"] = best_rp

        return new_sol

    # ============================================================
    #  Fallback 路径（RRT* 不可用时使用）
    # ============================================================

    def _fallback_path(self, start, goal, map_obj=None, has_terrain=False):
        """
        生成飞越模式路径（直飞 + 安全高度）
        当 RRT* 不可用或未收敛时使用
        """
        sx, sy, sz = start
        gx, gy, gz = goal

        # 计算安全飞越高度
        safe_z = max(sz, gz) + 30
        if map_obj and has_terrain:
            try:
                import numpy as _np
                ts = _np.linspace(0, 1, 30)
                xs = sx + ts * (gx - sx)
                ys = sy + ts * (gy - sy)
                hz = map_obj.get_terrain_height(xs, ys)
                safe_z = max(safe_z, float(_np.max(hz)) + 20)
            except Exception:
                pass
        if map_obj:
            obs = map_obj.get_obstacles() if hasattr(map_obj, 'get_obstacles') else []
            for o in obs:
                ocx, ocy, _ = o['center']
                ow, oh, oz = o['size']
                for t in [0.25, 0.5, 0.75]:
                    px = sx + t * (gx - sx)
                    py = sy + t * (gy - sy)
                    if abs(px - ocx) < ow / 2 + 10 and abs(py - ocy) < oh / 2 + 10:
                        safe_z = max(safe_z, oz + 15)
        if map_obj and hasattr(map_obj, 'get_bounds'):
            z_max = map_obj.get_bounds()[2][1]
            safe_z = min(safe_z, z_max - 2)

        # 生成路径点：起点 -> 爬升 -> 巡航 -> 下降 -> 终点
        path = [
            [sx, sy, sz],
            [sx, sy, safe_z],
            [gx, gy, safe_z],
            [gx, gy, gz],
        ]
        return path

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

            # Fallback 路径用虚线+红色区分
            if t.get("is_fallback", False):
                line_style = "--"
                line_alpha = 0.6
            else:
                line_style = "-"
                line_alpha = 0.85

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

            # ── 换电站标记 ──
            for swap in t.get("swap_stations", []):
                BatteryManager.render_swap_mPL(ax, [swap])

    # ============================================================
    #  渲染（Plotly）
    # ============================================================

    def render_plotly(self, result):
        """返回 Plotly Scatter3d 轨迹列表（路径 + 分配连线）"""
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

            # 轨迹线
            traces.append(go.Scatter3d(
                x=xs, y=ys, z=zs, mode="lines",
                line=dict(color=color, width=5, dash="solid"),
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

            # 分配连线：起点到终点的连线（表示分配关系）
            traces.append(go.Scatter3d(
                x=[xs[0], xs[-1]], y=[ys[0], ys[-1]], z=[zs[0], zs[-1]],
                mode="lines",
                line=dict(color=color, width=1, dash="solid"),
                showlegend=False,
                opacity=0.4,
                hoverinfo="skip",
            ))

            # ── 换电站标记 ──
            swap_stations = t.get("swap_stations", [])
            if swap_stations:
                traces.extend(BatteryManager.render_swap_plotly_swap_traces(swap_stations))

        return traces
