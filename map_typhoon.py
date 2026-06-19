"""
应急无人机调度系统 — 台风沿海场景
文件：map_typhoon.py
"""

import numpy as np
from dispatch_page import BaseMap


class Map(BaseMap):
    name = "台风沿海场景"
    desc = "模拟沿海台风过境后的高风场环境，包含海面、损毁建筑、倒伏树木等障碍"

    def get_obstacles(self):
        """台风沿海障碍物"""
        obstacles = []

        # 沿海损毁建筑
        buildings = [
            {"center": [100, 180, 30],  "size": [40, 35, 60],  "type": "building"},
            {"center": [-80, 200, 25],  "size": [30, 25, 50],  "type": "building"},
            {"center": [200, 100, 20],  "size": [35, 30, 40],  "type": "building"},
            {"center": [-150, 150, 18], "size": [25, 20, 36],  "type": "building"},
            {"center": [50, 250, 35],   "size": [45, 40, 70],  "type": "building"},
            {"center": [-200, 250, 22], "size": [28, 22, 44],  "type": "building"},
        ]
        obstacles.extend(buildings)

        # 倒伏的树木/电线杆（细长障碍）
        fallen = [
            {"center": [30, 100, 5],    "size": [40, 4, 10],   "type": "fallen_tree"},
            {"center": [-60, 80, 4],    "size": [35, 3, 8],    "type": "fallen_tree"},
            {"center": [120, 50, 6],    "size": [45, 4, 12],   "type": "fallen_tree"},
            {"center": [-100, 120, 5],  "size": [30, 3, 10],   "type": "fallen_tree"},
            {"center": [80, 30, 4],     "size": [38, 4, 8],    "type": "fallen_tree"},
            {"center": [-30, 200, 5],   "size": [42, 3, 10],   "type": "fallen_tree"},
        ]
        obstacles.extend(fallen)

        # 沿海防波堤/堤坝损毁
        seawalls = [
            {"center": [0, -50, 12],    "size": [300, 8, 24],  "type": "seawall"},
            {"center": [150, -80, 10],  "size": [8, 60, 20],   "type": "seawall"},
            {"center": [-150, -80, 10], "size": [8, 60, 20],   "type": "seawall"},
        ]
        obstacles.extend(seawalls)

        # 积水/内涝区
        floods = [
            {"center": [0, 50, 2],      "size": [180, 100, 4], "type": "flood"},
            {"center": [-100, 30, 2],   "size": [80, 60, 4],   "type": "flood"},
        ]
        obstacles.extend(floods)

        return obstacles

    def get_service_areas(self):
        """沿海服务区"""
        return [
            {"name": "港口集结区",   "x": 0.0,    "y": -150.0, "z": 0.0},
            {"name": "城区救援站",   "x": 50.0,   "y": 200.0,  "z": 0.0},
            {"name": "沿海避难点",   "x": -100.0, "y": 100.0,  "z": 0.0},
            {"name": "内陆转运站",   "x": 0.0,    "y": 300.0,  "z": 0.0},
        ]

    def get_rescue_points(self):
        """沿海救援点"""
        return [
            {"name": "被困渔村",     "x": 120.0,  "y": -30.0,  "z": 10.0, "priority": 0, "priority_text": "紧急 (P0)", "note": "渔船被毁"},
            {"name": "沿海居民区",   "x": -80.0,  "y": 80.0,   "z": 15.0, "priority": 1, "priority_text": "高 (P1)",   "note": "积水严重"},
            {"name": "学校避难所",   "x": 60.0,   "y": 220.0,  "z": 20.0, "priority": 0, "priority_text": "紧急 (P0)", "note": "人员密集"},
            {"name": "工厂区",       "x": -150.0, "y": 200.0,  "z": 12.0, "priority": 2, "priority_text": "中 (P2)",   "note": "有化学品"},
        ]

    def get_bounds(self):
        return ((-300, 300), (-200, 350), (0, 180))

    def render_3d(self, ax):
        """绘制台风沿海场景"""
        bounds = self.get_bounds()
        x_range, y_range, z_range = bounds

        # 海面（y < -50 区域）
        sx = np.linspace(x_range[0], x_range[1], 20)
        sy = np.linspace(y_range[0], -50, 15)
        SX, SY = np.meshgrid(sx, sy)
        SZ = np.full_like(SX, -1.0) + 1.5 * np.sin(SX / 30 + SY / 20)
        ax.plot_surface(SX, SY, SZ, alpha=0.35, color="#1565C0")

        # 陆地（y >= -50 区域）
        lx = np.linspace(x_range[0], x_range[1], 20)
        ly = np.linspace(-50, y_range[1], 20)
        LX, LY = np.meshgrid(lx, ly)
        LZ = np.zeros_like(LX) + 2 * np.sin(LX / 60) * np.cos(LY / 50)
        LZ = np.maximum(LZ, 0)
        ax.plot_surface(LX, LY, LZ, alpha=0.15, color="#4A7C3F")

        # 海岸线
        ax.plot([x_range[0], x_range[1]], [-50, -50], [0, 0],
                color="#FFD700", linewidth=2, alpha=0.6, linestyle="--")

        # 绘制障碍物
        for obs in self.get_obstacles():
            cx, cy, cz = obs["center"]
            w, h, d = obs["size"]
            obs_type = obs["type"]

            if obs_type == "building":
                color = "#8B6914"
                alpha = 0.45
            elif obs_type == "fallen_tree":
                color = "#2E8B57"
                alpha = 0.4
            elif obs_type == "seawall":
                color = "#808080"
                alpha = 0.5
            elif obs_type == "flood":
                color = "#4169E1"
                alpha = 0.3
            else:
                color = "#696969"
                alpha = 0.3

            x = [cx - w/2, cx + w/2]
            y = [cy - h/2, cy + h/2]
            z = [0, d]

            xx, yy = np.meshgrid(x, y)
            ax.plot_surface(xx, yy, np.full_like(xx, z[1]), alpha=alpha, color=color)

            for xi in x:
                yz_y, yz_z = np.meshgrid(y, z)
                ax.plot_surface(np.full_like(yz_y, xi), yz_y, yz_z, alpha=alpha*0.6, color=color)
            for yi in y:
                xz_x, xz_z = np.meshgrid(x, z)
                ax.plot_surface(xz_x, np.full_like(xz_x, yi), xz_z, alpha=alpha*0.6, color=color)

        # 风向箭头（表示台风风向）
        for y_pos in range(-100, 300, 80):
            ax.quiver(250, y_pos, 80, -60, 0, 0,
                      color="#FF6B6B", alpha=0.4, arrow_length_ratio=0.3, linewidth=1.5)

        ax.set_xlim(*x_range)
        ax.set_ylim(*y_range)
        ax.set_zlim(*z_range)
        ax.set_title(f"🗺 {self.name}", fontsize=10, color="#E8F1FB", pad=10)
