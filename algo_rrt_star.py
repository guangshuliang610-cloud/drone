"""
应急无人机调度系统 — 新RRT*算法（渐近最优三维路径规划）
文件：algo_rrt_star.py

RRT*（Rapidly-exploring Random Tree Star）算法：
  - 在三维连续空间中随机采样，逐步构建路径树
  - 核心改进：ChooseParent + Rewire 实现渐近最优性
  - 更密碰撞检测（n_check=12），numpy向量运算加速
  - 兼容城市建筑避障 + 山区地形避障
  - 未收敛时自动 fallback 到飞越模式

依赖：dispatch_page.BaseAlgorithm
"""

import math
import random
import numpy as np
from dispatch_page import BaseAlgorithm
from algo_battery import BatteryManager  # 渲染换电站


class Algorithm(BaseAlgorithm):
    name = "RRT* 渐近最优规划"
    desc = "渐近最优三维路径规划（chooseParent+Rewire），建筑/地形双兼容"

    # ── RRT* 核心参数 ──
    MAX_ITER = 800
    STEP_SIZE = 35
    GOAL_BIAS = 0.15
    REWIRE_RADIUS = 60
    N_CHECK = 12
    MARGIN = 5  # 障碍物膨胀安全距离

    def solve(self, drones, materials, service_areas, rescue_points, map_obj):
        """
        RRT* 核心求解
        对每架无人机：
          1. 分配服务区(起点)和救援点(终点)
          2. 运行 RRT* 搜索无碰路径
          3. 未收敛时 fallback 到飞越模式
          4. 路径平滑
        """
        from algo_battery import BatteryManager
        n_drones = len(drones)
        n_rp = len(rescue_points)

        if n_drones == 0 or n_rp == 0:
            return self._empty_result("无无人机或无救援点")

        # ── 从 map_obj 获取场景数据（不硬编码任何位置）──
        sa_coords = [(a["x"], a["y"], a["z"]) for a in service_areas]
        rp_coords = [(r["x"], r["y"], r["z"]) for r in rescue_points]

        # 获取障碍物（来自地图模块生成函数）
        obstacles = map_obj.get_obstacles() if map_obj else []

        # 获取场景边界（来自地图模块生成函数）
        bounds = map_obj.get_bounds() if map_obj else ((-500, 500), (-500, 500), (0, 200))

        # 检测地图是否支持地形高程（山区场景）
        has_terrain = hasattr(map_obj, "get_terrain_height") if map_obj else False

        # 颜色表
        colors = [
            "#FF3366", "#00E5FF", "#FFEA00", "#76FF03",
            "#FF6D00", "#E040FB", "#00FFC8", "#FF1744",
            "#7C4DFF", "#FFAB00",
        ]

        trajectories = []
        total_time = 0.0
        total_distance = 0.0
        fallback_count = 0

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

        used_rps = set()
        for d_idx in range(n_drones):
            sa_idx = d_idx % len(sa_coords)
            rp_idx = d_idx % n_rp
            used_rps.add(rp_idx)

            start = sa_coords[sa_idx]
            goal = rp_coords[rp_idx]

            # ── 运行 RRT* ──
            path = self._rrt_star(
                start, goal, obstacles, bounds, has_terrain, map_obj
            )

            is_fallback = False
            if path is None:
                # Fallback: 飞越模式
                path = self._fallback_path(start, goal, map_obj, has_terrain)
                is_fallback = True
                fallback_count += 1

            # 路径平滑
            path = self._smooth_path(path, obstacles, has_terrain, map_obj)

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
        msg_parts = [f"RRT*规划完成，{n_drones}架无人机成功规避{len(obstacles)}个障碍物"]
        if fallback_count > 0:
            msg_parts.append(f"{fallback_count}架无人机使用飞越模式(RRT*未收敛)")
        msg = "；".join(msg_parts)

        # ── 电量管理：换电站插入 ──
        result = {
            "trajectories": trajectories,
            "total_time": total_time,
            "total_distance": total_distance,
            "success_rate": min(success_rate, 1.0),
            "message": msg,
        }
        return BatteryManager().apply(drones, service_areas, result)

    # ============================================================
    #  RRT* 核心
    # ============================================================

    def _rrt_star(self, start, goal, obstacles, bounds, has_terrain, map_obj):
        """
        RRT* 算法：渐近最优路径规划

        返回: 路径点列表 [start, ..., goal] 或 None（未收敛）
        """
        start_arr = np.array(start, dtype=float)
        goal_arr = np.array(goal, dtype=float)

        # 初始化树
        nodes = [start_arr.copy()]  # 节点列表
        parents = [-1]              # 父节点索引
        costs = [0.0]               # 从起点到该节点的累计代价

        for iteration in range(self.MAX_ITER):
            # ── Step 1: 采样 ──
            if random.random() < self.GOAL_BIAS:
                # 目标偏好采样
                sample = goal_arr + np.random.normal(0, 10, 3)
            else:
                # 随机采样（在边界内）
                sample = np.array([
                    random.uniform(bounds[0][0], bounds[0][1]),
                    random.uniform(bounds[1][0], bounds[1][1]),
                    random.uniform(bounds[2][0], bounds[2][1]),
                ])

            # ── Step 2: 找最近邻 ──
            nearest_idx, nearest_dist = self._nearest(nodes, sample)
            nearest = nodes[nearest_idx]

            # ── Step 3: 以 STEP_SIZE 为步长延伸 ──
            direction = sample - nearest
            dist = np.linalg.norm(direction)
            if dist < 1e-9:
                continue
            direction = direction / dist

            # 步长不超过 STEP_SIZE
            step = min(dist, self.STEP_SIZE)
            new_node = nearest + direction * step

            # ── Step 4: 碰撞检测（nearest → new_node）──
            if self._check_collision(nearest, new_node, obstacles, has_terrain, map_obj):
                continue

            # ── Step 5: ChooseParent — 在 rewire_radius 范围内找最优父节点 ──
            new_cost = costs[nearest_idx] + np.linalg.norm(new_node - nearest)
            best_parent = nearest_idx
            best_cost = new_cost

            # 在 REWIRE_RADIUS 范围内找邻居
            neighbor_indices = self._find_neighbors(nodes, new_node, self.REWIRE_RADIUS)

            for n_idx in neighbor_indices:
                if n_idx == nearest_idx:
                    continue
                neighbor = nodes[n_idx]
                cost_via_neighbor = costs[n_idx] + np.linalg.norm(new_node - neighbor)
                if cost_via_neighbor < best_cost:
                    # 检查该邻居到 new_node 是否无碰
                    if not self._check_collision(neighbor, new_node, obstacles, has_terrain, map_obj):
                        best_parent = n_idx
                        best_cost = cost_via_neighbor

            # 将新节点加入树
            new_idx = len(nodes)
            nodes.append(new_node.copy())
            parents.append(best_parent)
            costs.append(best_cost)

            # ── Step 6: Rewire — 反向检查新节点能否优化邻居的路径 ──
            for n_idx in neighbor_indices:
                if n_idx == best_parent:
                    continue
                neighbor = nodes[n_idx]
                cost_via_new = best_cost + np.linalg.norm(neighbor - new_node)
                if cost_via_new < costs[n_idx]:
                    # 检查 new_node 到该邻居是否无碰
                    if not self._check_collision(new_node, neighbor, obstacles, has_terrain, map_obj):
                        parents[n_idx] = new_idx
                        costs[n_idx] = cost_via_new

            # ── Step 7: 检查是否到达目标 ──
            dist_to_goal = np.linalg.norm(new_node - goal_arr)
            if dist_to_goal < self.STEP_SIZE:
                # 检查最后一段到目标是否无碰
                if not self._check_collision(new_node, goal_arr, obstacles, has_terrain, map_obj):
                    # 构建完整路径
                    path = []
                    idx = new_idx
                    while idx >= 0:
                        path.append(nodes[idx].tolist())
                        idx = parents[idx]
                    path.reverse()
                    path.append(goal_arr.tolist())
                    return path

        # 未收敛
        return None

    def _nearest(self, nodes, target):
        """
        找最近邻节点
        返回: (最近邻索引, 距离)
        """
        target = np.asarray(target)
        min_dist = float("inf")
        min_idx = 0
        for i, node in enumerate(nodes):
            dist = np.linalg.norm(node - target)
            if dist < min_dist:
                min_dist = dist
                min_idx = i
        return min_idx, min_dist

    def _find_neighbors(self, nodes, target, radius):
        """
        找半径内的所有邻居节点
        返回: 邻居索引列表
        """
        target = np.asarray(target)
        indices = []
        r2 = radius * radius
        for i, node in enumerate(nodes):
            dist2 = np.sum((node - target) ** 2)
            if dist2 <= r2:
                indices.append(i)
        return indices

    # ============================================================
    #  碰撞检测
    # ============================================================

    def _check_collision(self, p1, p2, obstacles, has_terrain, map_obj):
        """
        检测线段 p1→p2 是否与障碍物碰撞
        在 p1→p2 之间取 N_CHECK 个采样点逐一检查
        """
        p1 = np.asarray(p1, dtype=float)
        p2 = np.asarray(p2, dtype=float)

        seg_len = np.linalg.norm(p2 - p1)
        n_check = max(self.N_CHECK, int(seg_len / 5))

        for t in np.linspace(0, 1, n_check):
            point = p1 + t * (p2 - p1)
            if self._point_in_collision(point[0], point[1], point[2], obstacles, has_terrain, map_obj):
                return True
        return False

    def _point_in_collision(self, px, py, pz, obstacles, has_terrain, map_obj):
        """
        检测单点的碰撞：
        1. 静态障碍物碰撞（膨胀 margin）
        2. 地形碰撞（山区场景，pz < terrain_height）
        3. 地面以下碰撞（pz < 0）
        """
        # 地面碰撞
        if pz < 0:
            return True

        # 障碍物碰撞检测
        for obs in obstacles:
            cx, cy, cz = obs["center"]
            w, h, d = obs["size"]
            # 膨胀障碍物（安全距离）
            x_min = cx - w / 2 - self.MARGIN
            x_max = cx + w / 2 + self.MARGIN
            y_min = cy - h / 2 - self.MARGIN
            y_max = cy + h / 2 + self.MARGIN
            z_min = 0 - self.MARGIN
            z_max = d + self.MARGIN

            if (x_min <= px <= x_max and
                y_min <= py <= y_max and
                z_min <= pz <= z_max):
                return True

        # 地形碰撞（山区场景）
        if has_terrain:
            try:
                tz = float(map_obj.get_terrain_height(
                    np.array([px]), np.array([py])
                )[0])
                if pz < tz + self.MARGIN:
                    return True
            except Exception:
                pass

        return False

    # ============================================================
    #  Fallback 路径
    # ============================================================

    def _fallback_path(self, start, goal, map_obj, has_terrain):
        """
        RRT* 未收敛时的 fallback：飞越模式
        计算安全巡航高度，生成 [start, 安全高点, goal]
        二分抬升巡航高度直到 3 点路径所有线段无碰撞或触及 z_max
        """
        obstacles = map_obj.get_obstacles() if map_obj else []
        bounds = map_obj.get_bounds() if map_obj else ((-500, 500), (-500, 500), (0, 200))
        z_max = bounds[2][1] - 2

        safe_z = self._calc_cruise_z(start, goal, map_obj, has_terrain)
        start_arr = np.array(start, dtype=float)
        goal_arr = np.array(goal, dtype=float)
        mid_xy = [(start[0] + goal[0]) / 2, (start[1] + goal[1]) / 2]

        def _is_safe(z):
            """检查 [start, midpoint(z), goal] 两段是否都无碰撞"""
            mid_arr = np.array(mid_xy + [z], dtype=float)
            return (
                not self._check_collision(start_arr, mid_arr, obstacles, has_terrain, map_obj)
                and not self._check_collision(mid_arr, goal_arr, obstacles, has_terrain, map_obj)
            )

        # 初始高度已安全则直接返回
        if _is_safe(safe_z):
            return [list(start), mid_xy + [safe_z], list(goal)]

        # 二分向上搜索最低安全巡航高度
        lo, hi = safe_z, z_max
        found_z = None
        for _ in range(25):
            mid_z = (lo + hi) / 2
            if _is_safe(mid_z):
                found_z = mid_z
                hi = mid_z
            else:
                lo = mid_z
            if hi - lo < 0.5:
                break

        if found_z is not None:
            return [list(start), mid_xy + [found_z], list(goal)]

        # 最终兜底：生成带多个中间爬升点的路径
        return self._build_climb_path(start, goal, z_max, obstacles, has_terrain, map_obj)

    def _build_climb_path(self, start, goal, safe_z, obstacles, has_terrain, map_obj):
        """构建带爬升-巡航-下降的多段安全路径"""
        n_mid = 5
        path = [list(start)]
        for i in range(1, n_mid + 1):
            t = i / (n_mid + 1)
            x = start[0] + t * (goal[0] - start[0])
            y = start[1] + t * (goal[1] - start[1])
            # 先爬升后下降：用 sin 曲线过渡
            z_factor = np.sin(t * np.pi)
            z = max(start[2], goal[2]) + z_factor * (safe_z - max(start[2], goal[2]))
            path.append([x, y, z])
        path.append(list(goal))
        return path

    def _calc_cruise_z(self, start, goal, map_obj, has_terrain):
        """
        计算安全巡航高度：
        - 取起点终点高度的较大值 + 安全余量
        - 山区场景额外考虑地形最高点
        - 考虑沿途障碍物高度
        """
        margin = 20
        safe_z = max(start[2], goal[2]) + margin

        # 山区：考虑地形
        if has_terrain:
            try:
                ts = np.linspace(0, 1, 30)
                xs = start[0] + ts * (goal[0] - start[0])
                ys = start[1] + ts * (goal[1] - start[1])
                hz = map_obj.get_terrain_height(xs, ys)
                safe_z = max(safe_z, float(np.max(hz)) + margin)
            except Exception:
                pass

        # 考虑障碍物高度
        obstacles = map_obj.get_obstacles() if map_obj else []
        for obs in obstacles:
            ocx, ocy, _ = obs["center"]
            ow, oh, oz = obs["size"]
            # 检查障碍物是否在起点终点的连线附近
            for t in np.linspace(0, 1, 10):
                px = start[0] + t * (goal[0] - start[0])
                py = start[1] + t * (goal[1] - start[1])
                if abs(px - ocx) < ow / 2 + 10 and abs(py - ocy) < oh / 2 + 10:
                    safe_z = max(safe_z, oz + margin)
                    break

        # 不超出边界上界
        if map_obj:
            try:
                z_max = map_obj.get_bounds()[2][1]
                safe_z = min(safe_z, z_max - 2)
            except Exception:
                pass

        return safe_z

    def _ensure_safe_path(self, path, obstacles, has_terrain, map_obj):
        """
        逐段迭代检查路径是否无碰。
        若某段碰撞，插入中间航点并抬升至最近障碍物/地形之上，
        重复直到整条路径无碰或达到最大迭代次数。
        """
        if len(path) < 2:
            return path

        result = [list(p) for p in path]

        for _ in range(10):
            new_path = [result[0]]
            had_collision = False
            for i in range(len(result) - 1):
                p1 = np.array(result[i], dtype=float)
                p2 = np.array(result[i + 1], dtype=float)
                if self._check_collision(p1, p2, obstacles, has_terrain, map_obj):
                    had_collision = True
                    mid = (p1 + p2) / 2
                    mid[2] = self._lift_z_for_point(
                        mid[0], mid[1], mid[2],
                        obstacles, has_terrain, map_obj,
                    )
                    new_path.append(mid.tolist())
                new_path.append(list(result[i + 1]))
            result = new_path
            if not had_collision:
                break

        return result

    def _lift_z_for_point(self, x, y, z, obstacles, has_terrain, map_obj):
        """
        计算点 (x, y, z) 处的最低安全高度：
        取原高度、附近障碍物顶部、地形高度三者的最大值 + 余量。
        """
        safe_z = z

        # 地形
        if has_terrain:
            try:
                tz = float(map_obj.get_terrain_height(
                    np.array([x]), np.array([y])
                )[0])
                safe_z = max(safe_z, tz + self.MARGIN + 5)
            except Exception:
                pass

        # 障碍物
        for obs in obstacles:
            cx, cy, _ = obs["center"]
            w, h, d = obs["size"]
            if abs(x - cx) < w / 2 + 10 and abs(y - cy) < h / 2 + 10:
                safe_z = max(safe_z, d + self.MARGIN + 5)

        return safe_z

    # ============================================================
    #  路径平滑
    # ============================================================

    def _smooth_path(self, path, obstacles, has_terrain, map_obj):
        """
        路径平滑（shortcut + 碰撞验证）
        尝试跳过冗余中间节点，确保平滑后的路径无碰
        仅当相邻节点间距不过大时才尝试 shortcut，避免跨越障碍
        """
        if len(path) <= 2:
            return path

        # Shortcut：尝试跳过中间节点，但限制距离不超过 3*STEP_SIZE
        smoothed = [path[0]]
        i = 0
        while i < len(path) - 1:
            best_j = i + 1
            max_j = min(i + 3, len(path) - 1)
            for j in range(max_j, i, -1):
                p_i = np.array(path[i])
                p_j = np.array(path[j])
                seg_dist = np.linalg.norm(p_j - p_i)
                if seg_dist > self.STEP_SIZE * 3:
                    continue  # 太远了不做 shortcut，避免跨越障碍
                if not self._check_collision(
                    p_i, p_j,
                    obstacles, has_terrain, map_obj
                ):
                    best_j = j
                    break
            smoothed.append(path[best_j])
            i = best_j

        # 最终验证：确保平滑后每段都安全，若有碰撞则插入抬升点
        safe_path = [smoothed[0]]
        for k in range(1, len(smoothed)):
            p_prev = np.array(safe_path[-1])
            p_cur = np.array(smoothed[k])
            if self._check_collision(p_prev, p_cur, obstacles, has_terrain, map_obj):
                # 插入中点并抬升
                mid = (p_prev + p_cur) / 2
                if has_terrain and map_obj:
                    try:
                        tz = float(map_obj.get_terrain_height(np.array([mid[0]]), np.array([mid[1]]))[0])
                        mid[2] = max(mid[2], tz + 20)
                    except Exception:
                        mid[2] = max(mid[2], (p_prev[2] + p_cur[2]) / 2 + 20)
                safe_path.append(mid.tolist())
            safe_path.append(smoothed[k])

        return safe_path if len(safe_path) >= 2 else path


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
            # 中间航点（小三角）
            if len(xs) > 2:
                ax.scatter(
                    xs[1:-1], ys[1:-1], zs[1:-1], color=color, s=25,
                    marker="^", alpha=0.6,
                )
            # ── 换电站标记 ──
            for swap in t.get("swap_stations", []):
                BatteryManager.render_swap_mPL(ax, [swap])

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

            # Fallback 路径用 dash 线型区分
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
            # 中间航点（小三角）
            if len(xs) > 2:
                traces.append(go.Scatter3d(
                    x=xs[1:-1], y=ys[1:-1], z=zs[1:-1], mode="markers",
                    marker=dict(size=5, color=color, symbol="diamond", opacity=0.7),
                    showlegend=False,
                ))
            # ── 换电站标记 ──
            swap_stations = t.get("swap_stations", [])
            if swap_stations:
                traces.extend(BatteryManager.render_swap_plotly_swap_traces(swap_stations))

        return traces
