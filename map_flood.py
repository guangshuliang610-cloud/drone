import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from dispatch_page import BaseMap
import matplotlib.pyplot as plt


class Map(BaseMap):
    name = "山区避障场景"
    desc = "连续山脉地形 + 规范分层等高线，用于山地避障"

    def get_obstacles(self):
        return [
            # West highland belt
            {"center": [-250, 170, 66], "size": [120, 92, 132], "type": "mountain"},
            {"center": [-215, 20, 72], "size": [132, 98, 144], "type": "mountain"},
            {"center": [-235, -130, 64], "size": [120, 90, 128], "type": "mountain"},
            # Central transition mountains
            {"center": [-85, 115, 52], "size": [98, 78, 104], "type": "mountain"},
            {"center": [-30, -20, 56], "size": [110, 84, 112], "type": "mountain"},
            {"center": [45, -135, 50], "size": [94, 74, 100], "type": "mountain"},
            # Northeast branch mountain chain
            {"center": [110, 170, 44], "size": [86, 66, 88], "type": "mountain"},
            {"center": [190, 120, 40], "size": [80, 62, 80], "type": "mountain"},
        ]

    def get_service_areas(self):
        return [
            {"name": "北山服务区", "x": 0.0, "y": 260.0, "z": 40.0, "scene": "山区避障场景"},
            {"name": "南谷服务区", "x": 0.0, "y": -260.0, "z": 41.0, "scene": "山区避障场景"},
            {"name": "东岭服务区", "x": 260.0, "y": 0.0, "z": 27.0, "scene": "山区避障场景"},
            {"name": "西峰服务区", "x": -280.0, "y": -280.0, "z": 43.0, "scene": "山区避障场景"},
            {"name": "中心营地", "x": 150.0, "y": -60.0, "z": 50.0, "scene": "山区避障场景"},
        ]



    def get_rescue_points(self):
        return [
            {"name": "灾区A-北坡居民点", "x": -170.0, "y": 200.0, "z": 88.0, "priority": 0, "priority_text": "紧急(P0)", "note": "", "scene": "山区避障场景"},
            {"name": "灾区B-河谷村庄", "x": 100.0, "y": -80.0, "z": 78.0, "priority": 0, "priority_text": "紧急(P0)", "note": "", "scene": "山区避障场景"},
            {"name": "灾区C-西岭小学", "x": -140.0, "y": -170.0, "z": 66.0, "priority": 1, "priority_text": "高(P1)", "note": "", "scene": "山区避障场景"},
            {"name": "灾区D-东坡林场", "x": 160.0, "y": 200.0, "z": 85.0, "priority": 1, "priority_text": "高(P1)", "note": "", "scene": "山区避障场景"},
            {"name": "灾区E-南谷农田", "x": -50.0, "y": -200.0, "z": 54.0, "priority": 2, "priority_text": "中(P2)", "note": "", "scene": "山区避障场景"},
        ]



    def get_bounds(self):
        return ((-320, 320), (-300, 300), (0, 220))

    def _ridge(self, gx, gy, x0, y0, amp, sx, sy, theta_deg):
        t = np.deg2rad(theta_deg)
        xr = (gx - x0) * np.cos(t) + (gy - y0) * np.sin(t)
        yr = -(gx - x0) * np.sin(t) + (gy - y0) * np.cos(t)
        return amp * np.exp(-((xr / sx) ** 2 + (yr / sy) ** 2))

    def get_terrain_height(self, gx, gy):
        """Calculate terrain height at given x, y coordinates.
        
        Args:
            gx: scalar or numpy array of x coordinates
            gy: scalar or numpy array of y coordinates (same shape as gx)
        
        Returns:
            terrain height z (same shape as gx/gy), clipped to [0, 216]
        """
        x_range, y_range, z_range = self.get_bounds()
        gx = np.asarray(gx, dtype=float)
        gy = np.asarray(gy, dtype=float)

        terrain = 26 - 0.048 * gx
        terrain += 2.4 * np.sin((gy + 60) / 230.0) + 1.7 * np.cos((gx - 40) / 270.0)

        # Western highlands (broad uplift)
        terrain += self._ridge(gx, gy, -245, 10, 62, 240, 120, -12)
        terrain += self._ridge(gx, gy, -230, -170, 42, 190, 88, -30)

        # Central mountain system (north-south arc)
        terrain += self._ridge(gx, gy, -120, 140, 46, 170, 66, -28)
        terrain += self._ridge(gx, gy, -55, 15, 52, 185, 70, -20)
        terrain += self._ridge(gx, gy, 20, -120, 44, 175, 64, -25)

        # Northeast branch mountains
        terrain += self._ridge(gx, gy, 110, 165, 36, 125, 56, 34)
        terrain += self._ridge(gx, gy, 205, 115, 28, 110, 48, 30)

        # Southwest basin depression for stronger contrast.
        basin = 30 * np.exp(-(((gx + 190) / 125) ** 2 + ((gy + 220) / 90) ** 2))
        terrain -= basin

        # Distinct summit bumps.
        peaks = [
            (-235, 40, 62, 46, 56),
            (-85, 120, 50, 36, 46),
            (-20, 5, 54, 38, 52),
            (55, -120, 50, 36, 44),
            (145, 160, 46, 32, 38),
        ]
        for cx, cy, sx, sy, amp in peaks:
            terrain += amp * np.exp(-(((gx - cx) / sx) ** 2 + ((gy - cy) / sy) ** 2))

        terrain = np.clip(terrain, 0, z_range[1] - 4)
        return terrain

    def get_contour_lines(self, grid_size=170):
        """Extract contour line coordinates from the terrain.
        
        Returns:
            dict with 'levels', 'contours' (list of {level, paths}), and 'grid' (x, y, z arrays)
        """
        x_range, y_range, z_range = self.get_bounds()

        gx = np.linspace(x_range[0], x_range[1], grid_size)
        gy = np.linspace(y_range[0], y_range[1], grid_size)
        GX, GY = np.meshgrid(gx, gy)
        terrain = self.get_terrain_height(GX, GY)

        levels = np.linspace(8, float(np.max(terrain)) - 1, 40)
        contours_data = []

        if levels.size > 1:
            cs = plt.contour(GX, GY, terrain, levels=levels)
            for i, level in enumerate(cs.levels):
                paths = []
                for seg in cs.allsegs[i]:
                    paths.append(seg.tolist())
                contours_data.append({"level": float(level), "paths": paths})
            plt.close('all')

        return {
            "levels": levels.tolist(),
            "contours": contours_data,
            "grid": {
                "x": gx.tolist(),
                "y": gy.tolist(),
                "z": terrain.tolist(),
            }
        }

    def render_plotly(self):
        """Render Plotly Figure with contour terrain + markers"""
        import plotly.graph_objects as go
        x_range, y_range, z_range = self.get_bounds()
        traces = []

        gx = np.linspace(x_range[0], x_range[1], 100)
        gy = np.linspace(y_range[0], y_range[1], 100)
        GX, GY = np.meshgrid(gx, gy)
        GZ = self.get_terrain_height(GX.ravel(), GY.ravel()).reshape(GX.shape)
        GZ = np.clip(GZ, 0, z_range[1] - 4)

        # Terrain surface — very light, just a subtle base
        traces.append(go.Surface(
            x=GX, y=GY, z=GZ,
            colorscale=[[0, '#1B5E20'], [0.2, '#2E7D32'], [0.4, '#43A047'], [0.6, '#66BB6A'], [0.8, '#A5D6A7'], [1, '#E8F5E9']],
            opacity=0.45, showscale=False, name="地形",
            contours=dict(
                z=dict(
                    show=True, usecolormap=False,
                    highlightcolor="#ffffff", project_z=False,
                    start=20, end=float(np.max(GZ)) - 4, size=12
                )
            ),
            lightposition=dict(x=200, y=-200, z=800),
            lighting=dict(ambient=0.65, diffuse=0.6, specular=0.15, roughness=0.7)
        ))

        # Green contour lines — topo_green colormap
        levels = np.linspace(8, float(np.max(GZ)) - 1, 40)
        topo_colors = [
            '#1B5E20', '#2E7D32', '#43A047', '#66BB6A',
            '#A5D6A7', '#C8E6C9', '#E8F5E9'
        ]
        try:
            import matplotlib.pyplot as plt
            from matplotlib.colors import LinearSegmentedColormap
            topo_cmap = LinearSegmentedColormap.from_list('topo_green', topo_colors, N=256)
            cs = plt.contour(GX, GY, GZ, levels=levels)
            n_levels = len(cs.levels)
            for i, level in enumerate(cs.levels):
                segs = cs.allsegs[i]
                if not segs:
                    continue
                # Color from dark green (low) to light green (high)
                t = i / max(n_levels - 1, 1)
                c_idx = int(t * (len(topo_colors) - 1))
                line_color = topo_colors[min(c_idx, len(topo_colors) - 1)]
                for seg in segs:
                    if len(seg) > 2:
                        # On terrain surface
                        traces.append(go.Scatter3d(
                            x=seg[:, 0], y=seg[:, 1],
                            z=np.full(len(seg), level) + 0.3,
                            mode="lines",
                            line=dict(color=line_color, width=3.5),
                            showlegend=False, hoverinfo="skip"
                        ))
                        # Projected to ground
                        traces.append(go.Scatter3d(
                            x=seg[:, 0], y=seg[:, 1],
                            z=np.full(len(seg), 0.5),
                            mode="lines",
                            line=dict(color=line_color, width=1.8),
                            showlegend=False, hoverinfo="skip", opacity=0.55
                        ))
            plt.close("all")
        except Exception:
            pass

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
                bgcolor="#080B10",
                xaxis=dict(range=list(x_range), gridcolor="#1A2230", color="#5A6A7E", title="X (m)", showbackground=False),
                yaxis=dict(range=list(y_range), gridcolor="#1A2230", color="#5A6A7E", title="Y (m)", showbackground=False),
                zaxis=dict(range=list(z_range), gridcolor="#1A2230", color="#5A6A7E", title="Z (m)", showbackground=False),
                aspectratio=dict(x=1, y=1, z=0.55),
                camera=dict(eye=dict(x=1.6, y=-1.6, z=1.1)),
            ),
            paper_bgcolor="#080B10",
            margin=dict(l=0, r=0, t=30, b=0),
            showlegend=True,
            legend=dict(x=0, y=1, bgcolor="rgba(10,14,19,0.9)", font=dict(color="#C8D0DC", size=11)),
            font=dict(color="#5A6A7E"),
            title=dict(text=self.name, font=dict(color="#C8D0DC", size=14)),
        )
        return fig

