import numpy as np
from dispatch_page import BaseMap


class Map(BaseMap):
    name = "城市地震场景"
    desc = "以天津为原型的北方城市震后场景，天塔地标、网格街区、CBD商务区、传统居民区"

    def get_obstacles(self):
        obstacles = []

        # ── 天津广播电视塔（天塔）—— 城市地标 ──
        obstacles.append({"center": [0, 0, 65], "size": [45, 45, 130], "type": "tower"})

        # ── CBD现代高层商务区（东北方向，友谊路/滨海金融区）──
        cbd_highrises = [
            ( 160,  170, 104, 88, 82),   # 津塔
            ( 240,  140, 78, 94, 74),   # 金融中心A
            ( 190,  250, 91, 72, 68),   # 金融中心B
            ( 290,  200, 68, 83, 60),   # 商务大厦
        ]
        for x, y, w, h, z in cbd_highrises:
            obstacles.append({"center": [x, y, z / 2], "size": [w, h, z], "type": "highrise"})

        # ── 中层公共/商业建筑（沿主干道分布，散布全城）──
        midrises = [
            # 沿海河两岸
            (-130,   40, 85, 75, 45),   # 天津站
            (  80,  -50, 75, 94, 40),   # 滨江道商业
            (-200,  130, 88, 68, 48),   # 南开大学
            (  50,  190, 68, 81, 38),   # 体育馆
            # 城市南部
            (-80, -180, 81, 72, 42),   # 文化中心
            ( 170, -100, 71, 85, 36),   # 医院
            # 城市西部
            (-260,  -30, 75, 65, 44),   # 科技园
            ( -60, -290, 68, 75, 35),   # 会展中心
            # 城市北部
            (  90,  290, 81, 72, 40),   # 奥体中心
            (-170, -260, 71, 62, 38),   # 图书馆
        ]
        for x, y, w, h, z in midrises:
            obstacles.append({"center": [x, y, z / 2], "size": [w, h, z], "type": "midrise"})

        # ── 传统低层居民区（网格状分布，模拟天津老城街区）──
        buildings = [
            # 西北片区（红桥/河北老城）
            (-280,  250, 68, 59, 15),
            (-330,  200, 59, 72, 18),
            (-250,  310, 71, 59, 14),
            (-360,  280, 59, 65, 16),
            # 东北片区（河东/东丽）
            ( 280,  290, 62, 65, 17),
            ( 340,  250, 71, 59, 20),
            ( 310,  330, 59, 62, 13),
            # 西南片区（南开/西青老城）
            (-310, -210, 65, 62, 16),
            (-350, -290, 59, 72, 19),
            (-270, -330, 71, 59, 14),
            (-360, -170, 62, 65, 15),
            # 东南片区（河西/津南）
            ( 270, -230, 65, 59, 18),
            ( 320, -290, 59, 65, 15),
            ( 350, -190, 71, 62, 20),
            ( 290, -340, 62, 59, 13),
        ]
        for x, y, w, h, z in buildings:
            obstacles.append({"center": [x, y, z / 2], "size": [w, h, z], "type": "building"})

        return obstacles

    def get_service_areas(self):
        return [
            {"name": "城北服务区", "x": 0.0, "y": 340.0, "z": 0.0, "scene": "城市地震场景"},
            {"name": "城南服务区", "x": 0.0, "y": -340.0, "z": 0.0, "scene": "城市地震场景"},
            {"name": "城东服务区", "x": 340.0, "y": 0.0, "z": 0.0, "scene": "城市地震场景"},
            {"name": "城西服务区", "x": -340.0, "y": 0.0, "z": 0.0, "scene": "城市地震场景"},
            {"name": "中心服务区", "x": 200.0, "y": 320.0, "z": 0.0, "scene": "城市地震场景"},
        ]

    def get_rescue_points(self):
        return [
            {"name": "居民区A-河北区", "x": -280.0, "y": 250.0, "z": 9.0, "priority": 0, "priority_text": "紧急(P0)", "note": "", "scene": "城市地震场景"},
            {"name": "医院-和平区", "x": 170.0, "y": -100.0, "z": 12.0, "priority": 0, "priority_text": "紧急(P0)", "note": "", "scene": "城市地震场景"},
            {"name": "学校-南开区", "x": -200.0, "y": 130.0, "z": 15.0, "priority": 1, "priority_text": "高(P1)", "note": "", "scene": "城市地震场景"},
            {"name": "商业街-滨江道", "x": 80.0, "y": -50.0, "z": 30.0, "priority": 2, "priority_text": "中(P2)", "note": "", "scene": "城市地震场景"},
            {"name": "避难所-河西区", "x": -80.0, "y": -180.0, "z": 24.0, "priority": 1, "priority_text": "高(P1)", "note": "", "scene": "城市地震场景"},
        ]

    def get_bounds(self):
        return ((-420, 420), (-390, 390), (0, 160))

    def _draw_box(self, ax, cx, cy, w, h, z_top, color, alpha):
        x = [cx - w / 2, cx + w / 2]
        y = [cy - h / 2, cy + h / 2]
        xx, yy = np.meshgrid(x, y)
        ax.plot_surface(xx, yy, np.full_like(xx, z_top), color=color, alpha=alpha, linewidth=0)

        z = [0, z_top]
        for xi in x:
            yz_y, yz_z = np.meshgrid(y, z)
            ax.plot_surface(np.full_like(yz_y, xi), yz_y, yz_z, color=color, alpha=alpha * 0.90, linewidth=0)
        for yi in y:
            xz_x, xz_z = np.meshgrid(x, z)
            ax.plot_surface(xz_x, np.full_like(xz_x, yi), xz_z, color=color, alpha=alpha * 0.90, linewidth=0)

    def _draw_tower(self, ax, cx, cy, w, h, z_top, color, alpha):
        # 底部平台
        pw, ph = w * 1.8, h * 1.8
        pz = 8
        self._draw_box(ax, cx, cy, pw, ph, pz, color="#D4B860", alpha=1.0)

        # 塔身（窄高柱体）
        tower_w, tower_h = w * 0.5, h * 0.5
        self._draw_box(ax, cx, cy, tower_w, tower_h, z_top, color=color, alpha=alpha)

        # 顶部观景台
        obs_w, obs_h = w * 1.2, h * 1.2
        obs_z = 120
        self._draw_box(ax, cx, cy, obs_w, obs_h, obs_z, color="#B08A40", alpha=1.0)

        # 天线
        ax.plot([cx, cx], [cy, cy], [obs_z, z_top], color="#FFD700", linewidth=2.5, alpha=1.0)

    def _draw_grid_roads(self, ax, x_range, y_range):
        """绘制网格状城市道路（模拟天津棋盘式路网）"""
        road_color_main = "#C0CDD8"
        road_color_sec = "#A0B0B8"
        road_z = 1

        # 主干道
        for x_pos in [-300, -150, 0, 150, 300]:
            lw = 2.0 if x_pos == 0 else 1.4
            ax.plot([x_pos, x_pos], [y_range[0], y_range[1]],
                    [road_z, road_z], color=road_color_main, alpha=0.85, linewidth=lw)
        for y_pos in [-270, -90, 90, 270]:
            lw = 2.0 if y_pos == 0 else 1.4
            ax.plot([x_range[0], x_range[1]], [y_pos, y_pos],
                    [road_z, road_z], color=road_color_main, alpha=0.85, linewidth=lw)

        # 次干道
        for x_pos in range(-350, 351, 75):
            if x_pos not in [-300, -150, 0, 150, 300]:
                ax.plot([x_pos, x_pos], [y_range[0], y_range[1]],
                        [road_z, road_z], color=road_color_sec, alpha=0.55, linewidth=0.8)
        for y_pos in range(-350, 351, 75):
            if y_pos not in [-270, -90, 90, 270]:
                ax.plot([x_range[0], x_range[1]], [y_pos, y_pos],
                        [road_z, road_z], color=road_color_sec, alpha=0.55, linewidth=0.8)

    def render_3d(self, ax):
        x_range, y_range, z_range = self.get_bounds()

        # 地面平面
        gx = np.linspace(x_range[0], x_range[1], 24)
        gy = np.linspace(y_range[0], y_range[1], 24)
        GX, GY = np.meshgrid(gx, gy)
        GZ = np.zeros_like(GX)
        ax.plot_surface(GX, GY, GZ, alpha=0.06, color="#1A2830", linewidth=0)

        # 绘制网格道路
        self._draw_grid_roads(ax, x_range, y_range)

        # 渲染建筑（贴合现实的颜色，黑底可辨认）
        color_map = {
            "tower":    ("#F0D060", 1.0),   # 金色天塔（地标，醒目）
            "highrise": ("#50C0E8", 1.0),   # 钢蓝灰（玻璃幕墙）
            "midrise":  ("#D4B890", 1.0),   # 暖灰（混凝土/砖混）
            "building": ("#E0D0B8", 1.0),   # 浅暖灰（老城砖墙）
        }

        for obs in self.get_obstacles():
            cx, cy, _ = obs["center"]
            w, h, z = obs["size"]
            otype = obs["type"]
            color, alpha = color_map.get(otype, ("#D8C8B0", 0.95))

            if otype == "tower":
                self._draw_tower(ax, cx, cy, w, h, z, color=color, alpha=alpha)
            else:
                self._draw_box(ax, cx, cy, w, h, z, color=color, alpha=alpha)

        ax.set_xlim(*x_range)
        ax.set_ylim(*y_range)
        ax.set_zlim(*z_range)
        ax.set_title(self.name, fontsize=10, color="#E6E8EC", pad=8)








