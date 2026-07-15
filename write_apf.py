import os

code = """\
"""
应急无人机调度系统 — APF 轨迹平滑算法
文件：algo_apf.py

人工势场法 (Artificial Potential Field)：
  - 作为 RRT* 的后处理器，将离散路径点拟合为光滑可飞的曲线
  - 引力场将中间点拉向目标，斥力场推离障碍物
  - 迭代 30~50 步生成平滑曲线段
  - 兼容城市建筑避障 + 山区地形避障
  - 平滑后路径做碰撞验证，碰撞则回退到原路径点

依赖：dispatch_page.BaseAlgorithm，内部延迟调用 algo_rrt_star.Algorithm
"""

import math
import numpy as np
from dispatch_page import BaseAlgorithm


class Algorithm(BaseAlgorithm):
    name = "APF轨迹平滑算法"
    desc = "人工势场法，将RRT*离散路径点拟合为光滑可飞曲线，建筑/地形双兼容"

    # ── APF 核心参数 ──
    K_ATT = 0.5        # 引力系数
    K_REP = 50.0       # 斥力系数
    D0 = 30.0          # 斥力作用距离
    LR = 1.0           # 学习率（步长）
    MAX_ITER = 40      # 每段迭代步数
    INTERP_STEPS = 15  # 每两个路径点之间的插值点数
    MARGIN = 5.0       # 障碍物膨胀安全距离

    def solve(self, drones, materials, service_areas, rescue_points, map_obj):
        """
        APF 后处理器求解
        1. 内部调用 RRT* 获取离散路径
        2. 对每条轨迹的相邻路径点用 APF 插值平滑
        3. 碰撞验证，不通过则回退到原路径
        """
        n_drones = len(drones)
        n_rp = len(rescue_points)

        if n_drones == 0 or n_rp == 0:
            return self._empty_result("无无人机或无救援点")

        # ── 延迟导入 RRT*，避免循环依赖 ──
        from algo_rrt_star import Algorithm as RRTStarAlgorithm
        rrt_star = RRTStarAlgorithm()

        # 调用 RRT* 获取初始路径
        rrt_result = rrt_star.solve(drones, materials, service_areas, rescue_points, map_obj)

        if not rrt_result.get("trajectories"):
            return self._empty_result("RRT* 未生成有效轨迹，APF 无法平滑")

        # ── 从 map_obj 获取场景数据 ──
        obstacles = map_obj.get_obstacles() if map_obj else []
        bounds = map_obj.get_bounds() if map_obj else ((-500, 500), (-500, 500), (0, 200))
        has_terrain = hasattr(map_obj, "get_terrain_height") if map_obj else False

        # 物资分配统计（复用 RRT* 逻辑）
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

        sa_coords = [(a["x"], a["y"], a["z"]) for a in service_areas]
        rp_coords = [(r["x"], r["y"], r["z"]) for r in rescue_points]

        trajectories = []
        total_time = 0.0
        total_distance = 0.0
        used_rps = set()
        smooth_success_count = 0
        smooth_fallback_count = 0

        for d_idx in range(n_drones):
            sa_idx = d_idx % len(sa_coords)
            rp_idx = d_idx % n_rp
            used_rps.add(rp_idx)

            # 获取 RRT* 原始路径
            orig_traj = rrt_result["trajectories"][d_idx] if d_idx < len(rrt_result["trajectories"]) else None
            if orig_traj is None or len(orig_traj.get("waypoints", [])) < 2:
                continue

            orig_waypoints = orig_traj["waypoints"]
            orig_path = [w["pos"] for w in orig_waypoints]

            # ── APF 平滑处理 ──
            smoothed_path = self._apf_smooth(
                orig_path, obstacles, bounds, has_terrain, map_obj
            )

            # 统计平滑效果
            if len(smoothed_path) > len(orig_path):
                smooth_success_count += 1
            else:
                smooth_fallback_count += 1

            # 计算距离和时间
            dist = sum(
                math.sqrt(sum((smoothed_path[i][j] - smoothed_path[i + 1][j]) ** 2 for j in range(3)))
                for i in range(len(smoothed_path) - 1)
            )
            speed = drones[d_idx].get("max_speed", 60) / 3.6
            if speed <= 0:
                speed = 16.67
            flight_time = dist / speed

            # 构建航点标签
            waypoints = [{"pos": list(p), "label": ""} for p in smoothed_path]
            waypoints[0]["label"] = f"起点: {service_areas[sa_idx]['name']}"
            waypoints[-1]["label"] = f"投送: {rescue_points[rp_idx]['name']}"
            if len(waypoints) > 2:
                waypoints[1]["label"] = "APF平滑点"
                if len(waypoints) > 3:
                    waypoints[-2]["label"] = "接近目标"
                for w in waypoints[2:-2]:
                    w["label"] = "平滑路径点"

            delivered = rp_materials.get(rp_idx, ["通用物资"])

            trajectories.append({
                "drone_id": drones[d_idx].get("id", d_idx + 1),
                "drone_name": drones[d_idx].get("name", f"无人机-{d_idx + 1:02d}"),
                "color": orig_traj.get("color", "#1E6FD9"),
                "waypoints": waypoints,
                "orig_waypoints": orig_waypoints,
                "total_distance": dist,
                "total_time": flight_time,
                "delivered_materials": delivered,
                "smooth_points": len(smoothed_path),
                "is_fallback": orig_traj.get("is_fallback", False),
            })

            total_time = max(total_time, flight_time)
            total_distance += dist

        success_rate = len(used_rps) / n_rp if n_rp > 0 else 0

        # 构建消息
        msg_parts = [
            f"RRT*+APF规划完成，{n_drones}架无人机成功规避{len(obstacles)}个障碍物",
            f"APF平滑成功{smooth_success_count}架，回退{smooth_fallback_count}架"
        ]
        message = "；".join(msg_parts)

        return {
            "trajectories": trajectories,
            "total_time": total_time,
            "total_distance": total_distance,
            "success_rate": min(success_rate, 1.0),
            "message": message,
        }

    # ============================================================
    #  APF 核心平滑
    # ============================================================

    def _apf_smooth(self, path, obstacles, bounds, has_terrain, map_obj):
        """
        对整条路径逐段进行 APF 插值平滑。
        在 path[i] 与 path[i+1] 之间生成 INTERP_STEPS 个插值点，
        每个插值点受引力（拉向终点）和斥力（推离障碍物）作用迭代优化。
        """
        if len(path) < 2:
            return path

        full_smoothed = [list(path[0])]

        for i in range(len(path) - 1):
            seg_start = np.array(path[i], dtype=float)
            seg_end = np.array(path[i + 1], dtype=float)

            # 如果两点很近，直接加入终点
            dist = np.linalg.norm(seg_end - seg_start)
            if dist < 1e-3:
                full_smoothed.append(list(seg_end))
                continue

            # 在 seg_start 和 seg_end 之间生成初始插值点（直线）
            interp_points = []
            for j in range(1, self.INTERP_STEPS + 1):
                t = j / (self.INTERP_STEPS + 1)
                pt = seg_start + t * (seg_end - seg_start)
                interp_points.append(pt.copy())

            # 用 APF 迭代优化每个插值点位置
            for iteration in range(self.MAX_ITER):
                for k in range(len(interp_points)):
                    pos = interp_points[k]

                    # 引力：拉向 seg_end
                    f_att = -self.K_ATT * (pos - seg_end)

                    # 斥力：推离障碍物
                    f_rep = self._calc_repulsive_force(
                        pos, obstacles, has_terrain, map_obj
                    )

                    # 总力
                    f_total = f_att + f_rep
                    f_norm = np.linalg.norm(f_total)
                    if f_norm < 1e-6:
                        continue

                    # 沿合力方向移动
                    pos_new = pos + self.LR * f_total / f_norm

                    # 边界裁剪
                    pos_new = self._clip_to_bounds(pos_new, bounds)

                    interp_points[k] = pos_new

            # 碰撞验证
            pts_to_check = [seg_start] + interp_points + [seg_end]
            collision_free = True
            for j in range(len(pts_to_check) - 1):
                p1 = pts_to_check[j]
                p2 = pts_to_check[j + 1]
                if self._check_collision(p1, p2, obstacles, has_terrain, map_obj):
                    collision_free = False
                    break

            if collision_free:
                for pt in interp_points:
                    full_smoothed.append(list(pt))
                full_smoothed.append(list(seg_end))
            else:
                # 回退到原路径点
                full_smoothed.append(list(seg_end))

        return full_smoothed

    def _calc_repulsive_force(self, pos, obstacles, has_terrain, map_obj):
        """
        计算 pos 处的斥力（来自障碍物和地形）。
        F_rep = k_rep * (1/d - 1/d0) * (1/d^2) * grad_d  当 d < d0
        """
        f_rep = np.zeros(3, dtype=float)

        for obs in obstacles:
            cx, cy, cz = obs["center"]
            w, h, d = obs["size"]
            # 障碍物中心
            obs_center = np.array([cx, cy, d / 2.0], dtype=float)
            diff = pos - obs_center
            dist = np.linalg.norm(diff)

            # 使用膨胀后的有效距离
            min_dist = max(min(w, h) / 2.0, 1.0)
            effective_dist = max(dist - min_dist, 0.5)

            if effective_dist < self.D0:
                # 斥力方向：远离障碍物中心
                grad_d = diff / (dist + 1e-6)
                magnitude = self.K_REP * (
                    1.0 / effective_dist - 1.0 / self.D0
                ) / (effective_dist ** 2)
                f_rep += magnitude * grad_d

        # 地形斥力（山区场景）
        if has_terrain:
            try:
                tz = float(map_obj.get_terrain_height(
                    np.array([pos[0]]), np.array([pos[1]])
                )[0])
                terrain_dist = pos[2] - tz
                if terrain_dist < self.D0 and terrain_dist > 0:
                    # 地形斥力向上（+z方向）
                    magnitude = self.K_REP * (
                        1.0 / max(terrain_dist, 0.5) - 1.0 / self.D0
                    ) / (max(terrain_dist, 0.5) ** 2)
                    f_rep[2] += magnitude
            except Exception:
                pass

        return f_rep

    def _point_in_collision(self, px, py, pz, obstacles, has_terrain, map_obj):
        """检测单点碰撞（障碍物 + 地形 + 地面）"""
        if pz < 0:
            return True

        for obs in obstacles:
            cx, cy, cz = obs["center"]
            w, h, d = obs["size"]
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

    def _check_collision(self, p1, p2, obstacles, has_terrain, map_obj):
        """检测线段 p1->p2 是否碰撞（采样 12 个点）"""
        p1 = np.asarray(p1, dtype=float)
        p2 = np.asarray(p2, dtype=float)
        n_check = 12

        for t in np.linspace(0, 1, n_check):
            point = p1 + t * (p2 - p1)
            if self._point_in_collision(point[0], point[1], point[2], obstacles, has_terrain, map_obj):
                return True
        return False

    def _clip_to_bounds(self, pos, bounds):
        """将位置裁剪到场景边界内"""
        x_min, x_max = bounds[0]
        y_min, y_max = bounds[1]
        z_min, z_max = bounds[2]
        pos[0] = np.clip(pos[0], x_min + 1, x_max - 1)
        pos[1] = np.clip(pos[1], y_min + 1, y_max - 1)
        pos[2] = np.clip(pos[2], max(z_min, 1), z_max - 1)
        return pos

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
        """在 3D 画布上绘制轨迹：原始 RRT* 路径用虚线，平滑后用实线"""
        for t in result.get("trajectories", []):
            wps = t.get("waypoints", [])
            if len(wps) < 2:
                continue

            color = t.get("color", "#1E6FD9")
            name = t.get("drone_name", "?")

            # 原始 RRT* 路径（虚线，半透明）
            orig_wps = t.get("orig_waypoints", [])
            if len(orig_wps) >= 2:
                ox = [w["pos"][0] for w in orig_wps]
                oy = [w["pos"][1] for w in orig_wps]
                oz = [w["pos"][2] for w in orig_wps]
                ax.plot(
                    ox, oy, oz, color=color, linewidth=1.2, alpha=0.35,
                    linestyle="--", label=f"{name}(原始)",
                )

            # 平滑后路径（实线）
            xs = [w["pos"][0] for w in wps]
            ys = [w["pos"][1] for w in wps]
            zs = [w["pos"][2] for w in wps]

            ax.plot(
                xs, ys, zs, color=color, linewidth=2.5, alpha=0.9,
                linestyle="-", label=f"{name}(平滑)",
            )
            # 起点
            ax.scatter(
                [xs[0]], [ys[0]], [zs[0]], color=color, s=60,
                marker="o", edgecolors="white", linewidths=1,
            )
            # 终点
            ax.scatter(
                [xs[-1]], [ys[-1]], [zs[-1]], color=color, s=120,
                marker="*", edgecolors="white", linewidths=1.5,
            )
            # 平滑插值点
            if len(xs) > 2:
                ax.scatter(
                    xs[1:-1], ys[1:-1], zs[1:-1], color=color, s=20,
                    marker=".", alpha=0.5,
                )

    # ============================================================
    #  渲染（Plotly）
    # ============================================================

    def render_plotly(self, result):
        """返回 Plotly Scatter3d 轨迹列表，原始路径虚线 + 平滑路径实线叠加"""
        import plotly.graph_objects as go

        traces = []
        for t in result.get("trajectories", []):
            wps = t.get("waypoints", [])
            if len(wps) < 2:
                continue

            color = t.get("color", "#1E6FD9")
            name = t.get("drone_name", "?")

            # 原始 RRT* 路径（虚线，半透明）
            orig_wps = t.get("orig_waypoints", [])
            if len(orig_wps) >= 2:
                ox = [w["pos"][0] for w in orig_wps]
                oy = [w["pos"][1] for w in orig_wps]
                oz = [w["pos"][2] for w in orig_wps]
                traces.append(go.Scatter3d(
                    x=ox, y=oy, z=oz, mode="lines",
                    line=dict(color=color, width=2, dash="dash"),
                    opacity=0.4,
                    name=f"{name}(原始RRT*)",
                    showlegend=True,
                ))

            # 平滑后路径（实线）
            xs = [w["pos"][0] for w in wps]
            ys = [w["pos"][1] for w in wps]
            zs = [w["pos"][2] for w in wps]

            traces.append(go.Scatter3d(
                x=xs, y=ys, z=zs, mode="lines",
                line=dict(color=color, width=5, dash="solid"),
                name=f"{name}(APF平滑)",
                showlegend=True,
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
            # 终点
            traces.append(go.Scatter3d(
                x=[xs[-1]], y=[ys[-1]], z=[zs[-1]], mode="markers",
                marker=dict(
                    size=12, color=color, symbol="diamond",
                    line=dict(color="white", width=1.5),
                ),
                name=f"{name} 投送点", showlegend=False,
            ))
            # 平滑插值点
            if len(xs) > 2:
                traces.append(go.Scatter3d(
                    x=xs[1:-1], y=ys[1:-1], z=zs[1:-1], mode="markers",
                    marker=dict(size=4, color=color, symbol="circle", opacity=0.6),
                    showlegend=False,
                ))
        return traces
"""

with open("D:/Program Tools/python_project/drone/algo_apf.py", "w", encoding="utf-8") as f:
    f.write(code)
print("Written successfully")
