import numpy as np

from mpl_toolkits.mplot3d.art3d import Poly3DCollection
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
            ( 120,  140, 104, 88, 82),   # 津塔
            ( 290,  100, 78, 94, 74),   # 金融中心A
            ( 150,  290, 91, 72, 68),   # 金融中心B
            ( 350,  220, 68, 83, 60),   # 商务大厦
        ]
        for x, y, w, h, z in cbd_highrises:
            obstacles.append({"center": [x, y, z / 2], "size": [w, h, z], "type": "highrise"})

        # ── 中层公共/商业建筑（沿主干道分布，散布全城）──
        midrises = [
            # 沿海河两岸
            (-130,   40, 85, 75, 45),   # 天津站
            (  80,  -50, 75, 94, 40),   # 滨江道商业
            (-200,  130, 88, 68, 48),   # 南开大学
            (  50,  240, 68, 81, 38),   # 体育馆
            # 城市南部
            (-80, -180, 81, 72, 42),   # 文化中心
            ( 170, -100, 71, 85, 36),   # 医院
            # 城市西部
            (-260,  -30, 75, 65, 44),   # 科技园
            ( -60, -290, 68, 75, 35),   # 会展中心
            # 城市北部
            ( -30,  350, 81, 72, 40),   # 奥体中心
            (-170, -260, 71, 62, 38),   # 图书馆
        ]
        for x, y, w, h, z in midrises:
            obstacles.append({"center": [x, y, z / 2], "size": [w, h, z], "type": "midrise"})

        # ── 传统低层居民区（网格状分布，模拟天津老城街区）──
        buildings = [
            # 西北片区（红桥/河北老城）
            (-270,  250, 68, 59, 15),
            (-350,  180, 59, 72, 18),
            (-240,  340, 71, 59, 14),
            (-380,  290, 59, 65, 16),
            # 东北片区（河东/东丽）
            ( 240,  340, 62, 65, 17),
            ( 400,  320, 71, 59, 20),
            ( 320,  380, 59, 62, 13),
            # 西南片区（南开/西青老城）
            (-300, -220, 65, 62, 16),
            (-370, -310, 59, 72, 19),
            (-250, -350, 71, 59, 14),
            (-380, -160, 62, 65, 15),
            # 东南片区（河西/津南）
            ( 260, -240, 65, 59, 18),
            ( 350, -300, 59, 65, 15),
            ( 380, -180, 71, 62, 20),
            ( 260, -380, 62, 59, 13),
        ]
        for x, y, w, h, z in buildings:
            obstacles.append({"center": [x, y, z / 2], "size": [w, h, z], "type": "building"})

        return obstacles

    def get_service_areas(self):
        return [
            {"name": "城北服务区", "x": 60.0, "y": 380.0, "z": 5.0, "scene": "城市地震场景"},
            {"name": "城南服务区", "x": 0.0, "y": -380.0, "z": 5.0, "scene": "城市地震场景"},
            {"name": "城东服务区", "x": 380.0, "y": 0.0, "z": 5.0, "scene": "城市地震场景"},
            {"name": "城西服务区", "x": -380.0, "y": 0.0, "z": 5.0, "scene": "城市地震场景"},
            {"name": "中心服务区", "x": 300.0, "y": 280.0, "z": 5.0, "scene": "城市地震场景"},
        ]



    def get_rescue_points(self):
        return [
            {"name": "居民区A", "x": -280.0, "y": 310.0, "z": 2, "priority": 0, "priority_text": "紧急(P0)", "note": "", "scene": "城市地震场景"},
            {"name": "医院", "x": 210.0, "y": -100.0, "z": 36, "priority": 0, "priority_text": "紧急(P0)", "note": "", "scene": "城市地震场景"},
            {"name": "学校", "x": -200.0, "y": 180.0, "z": 42, "priority": 1, "priority_text": "高(P1)", "note": "", "scene": "城市地震场景"},
            {"name": "商业街", "x": 80.0, "y": -120.0, "z": 2, "priority": 2, "priority_text": "中(P2)", "note": "", "scene": "城市地震场景"},
            {"name": "避难所", "x": -80.0, "y": -240.0, "z": 35, "priority": 1, "priority_text": "高(P1)", "note": "", "scene": "城市地震场景"},
        ]



    def get_bounds(self):
        return ((-420, 420), (-390, 390), (0, 160))

    def _draw_box(self, ax, cx, cy, w, h, z_top, color, alpha):
        x = [cx - w / 2, cx + w / 2]
        y = [cy - h / 2, cy + h / 2]
        xx, yy = np.meshgrid(x, y)
        # 顶面透明
        ax.plot_surface(xx, yy, np.full_like(xx, z_top), color=color, alpha=0.12, linewidth=0, shade=False)
        # 侧面不透明
        z = [0, z_top]
        for xi in x:
            yz_y, yz_z = np.meshgrid(y, z)
            ax.plot_surface(np.full_like(yz_y, xi), yz_y, yz_z, color=color, alpha=alpha, linewidth=0, shade=False)
        for yi in y:
            xz_x, xz_z = np.meshgrid(x, z)
            ax.plot_surface(xz_x, np.full_like(xz_x, yi), xz_z, color=color, alpha=alpha, linewidth=0, shade=False)
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
        ax.plot_wireframe(GX, GY, GZ, color="#2A3848", alpha=0.3, linewidth=0.3)

        # 绘制网格道路
        self._draw_grid_roads(ax, x_range, y_range)

        # 渲染建筑（贴合现实的颜色，黑底可辨认）
        color_map = {
            "tower":    ("#E8C850", 1.0),   # 金色天塔
            "highrise": ("#60B0D8", 1.0),   # 钢蓝灰
            "midrise":  ("#C0A888", 1.0),   # 暖灰
            "building": ("#D8C8B0", 1.0),   # 浅暖灰
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
        ax.set_title(self.name, fontsize=10, color="#C8D0DC", pad=8)









    def render_plotly(self):
        """返回 Plotly Figure 对象"""
        import plotly.graph_objects as go
        x_range, y_range, z_range = self.get_bounds()

        traces = []

        # 地面网格
        gx = np.linspace(x_range[0], x_range[1], 12)
        gy = np.linspace(y_range[0], y_range[1], 12)
        GX, GY = np.meshgrid(gx, gy)
        GZ = np.zeros_like(GX)
        traces.append(go.Surface(
            x=GX, y=GY, z=GZ,
            colorscale=[[0, '#1A2830'], [1, '#1A2830']],
            opacity=0.15, showscale=False, name='地面'
        ))

        # 道路
        road_z = 1
        road_main = '#C0CDD8'
        road_sec = '#A0B0B8'
        for x_pos in [-300, -150, 0, 150, 300]:
            traces.append(go.Scatter3d(
                x=[x_pos, x_pos], y=[y_range[0], y_range[1]], z=[road_z, road_z],
                mode='lines', line=dict(color=road_main, width=2), showlegend=False
            ))
        for y_pos in [-270, -90, 90, 270]:
            traces.append(go.Scatter3d(
                x=[x_range[0], x_range[1]], y=[y_pos, y_pos], z=[road_z, road_z],
                mode='lines', line=dict(color=road_main, width=2), showlegend=False
            ))
        for x_pos in range(-350, 351, 75):
            if x_pos not in [-300, -150, 0, 150, 300]:
                traces.append(go.Scatter3d(
                    x=[x_pos, x_pos], y=[y_range[0], y_range[1]], z=[road_z, road_z],
                    mode='lines', line=dict(color=road_sec, width=1), showlegend=False
                ))
        for y_pos in range(-350, 351, 75):
            if y_pos not in [-270, -90, 90, 270]:
                traces.append(go.Scatter3d(
                    x=[x_range[0], x_range[1]], y=[y_pos, y_pos], z=[road_z, road_z],
                    mode='lines', line=dict(color=road_sec, width=1), showlegend=False
                ))

        # 建筑
        color_map = {
            'tower':    '#E8C850',
            'highrise': '#60B0D8',
            'midrise':  '#C0A888',
            'building': '#D8C8B0',
        }

        for obs in self.get_obstacles():
            cx, cy, _ = obs['center']
            w, h, z = obs['size']
            otype = obs['type']
            color = color_map.get(otype, '#D8C8B0')

            x0, x1 = cx - w/2, cx + w/2
            y0, y1 = cy - h/2, cy + h/2

            # 8 vertices
            verts_x = [x0, x1, x1, x0, x0, x1, x1, x0]
            verts_y = [y0, y0, y1, y1, y0, y0, y1, y1]
            verts_z = [0,  0,  0,  0,  z,  z,  z,  z]

            # 12 triangles (2 per face)
            i_vals = [0,0, 4,4, 0,0, 1,1, 0,0, 3,3]
            j_vals = [1,2, 5,6, 1,5, 2,6, 3,7, 2,6]
            k_vals = [2,3, 6,7, 5,4, 6,5, 7,4, 6,7]

            traces.append(go.Mesh3d(
                x=verts_x, y=verts_y, z=verts_z,
                i=i_vals, j=j_vals, k=k_vals,
                color=color, opacity=1.0,
                flatshading=True, lighting=dict(ambient=0.8, diffuse=0.3, specular=0.1),
                name=otype, showlegend=(otype == 'tower')
            ))


        # 服务区
        first = True
        for sa in self.get_service_areas():
            traces.append(go.Scatter3d(
                x=[sa["x"]], y=[sa["y"]], z=[max(sa["z"], 5)],
                mode="markers+text",
                marker=dict(size=10, color="#FFD700", symbol="diamond",
                            line=dict(color="white", width=1)),
                text=[sa["name"]], textposition="top center",
                textfont=dict(color="#FFD700", size=10),
                name="服务区", showlegend=first
            ))
            first = False

        # 救援点
        first = True
        for rp in self.get_rescue_points():
            traces.append(go.Scatter3d(
                x=[rp["x"]], y=[rp["y"]], z=[max(rp["z"], 5)],
                mode="markers+text",
                marker=dict(size=10, color="#FF4444", symbol="cross",
                            line=dict(color="white", width=1)),
                text=[rp["name"]], textposition="top center",
                textfont=dict(color="#FF4444", size=10),
                name="救援点", showlegend=first
            ))
            first = False

        fig = go.Figure(data=traces)
        fig.update_layout(
            scene=dict(
                bgcolor='#080B10',
                xaxis=dict(range=list(x_range), gridcolor='#1A2230', color='#5A6A7E', title='X (m)', showbackground=False),
                yaxis=dict(range=list(y_range), gridcolor='#1A2230', color='#5A6A7E', title='Y (m)', showbackground=False),
                zaxis=dict(range=list(z_range), gridcolor='#1A2230', color='#5A6A7E', title='Z (m)', showbackground=False),
                aspectratio=dict(x=1, y=1, z=0.55),
                camera=dict(eye=dict(x=1.6, y=-1.6, z=1.1)),
            ),
            paper_bgcolor='#080B10',
            margin=dict(l=0, r=0, t=30, b=0),
            showlegend=True,
            legend=dict(x=0, y=1, bgcolor='rgba(10,14,19,0.9)', font=dict(color='#C8D0DC', size=11)),
            font=dict(color='#5A6A7E'),
            title=dict(text=self.name, font=dict(color='#C8D0DC', size=14)),
        )
        return fig
