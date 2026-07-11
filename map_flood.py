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
            {"name": "北山服务区", "x": 0.0, "y": 260.0, "z": 30.0, "scene": "山区避障场景"},
            {"name": "南谷服务区", "x": 0.0, "y": -260.0, "z": 31.0, "scene": "山区避障场景"},
            {"name": "东岭服务区", "x": 260.0, "y": 0.0, "z": 17.0, "scene": "山区避障场景"},
            {"name": "西峰服务区", "x": -280.0, "y": -280.0, "z": 33.0, "scene": "山区避障场景"},
            {"name": "中心营地", "x": 150.0, "y": -60.0, "z": 40.0, "scene": "山区避障场景"},
        ]

    def get_rescue_points(self):
        return [
            {"name": "灾区A-北坡居民点", "x": -170.0, "y": 200.0, "z": 73.0, "priority": 0, "priority_text": "紧急(P0)", "note": "", "scene": "山区避障场景"},
            {"name": "灾区B-河谷村庄", "x": 100.0, "y": -80.0, "z": 63.0, "priority": 0, "priority_text": "紧急(P0)", "note": "", "scene": "山区避障场景"},
            {"name": "灾区C-西岭小学", "x": -140.0, "y": -170.0, "z": 51.0, "priority": 1, "priority_text": "高(P1)", "note": "", "scene": "山区避障场景"},
            {"name": "灾区D-东坡林场", "x": 160.0, "y": 200.0, "z": 58.0, "priority": 1, "priority_text": "高(P1)", "note": "", "scene": "山区避障场景"},
            {"name": "灾区E-南谷农田", "x": -50.0, "y": -200.0, "z": 39.0, "priority": 2, "priority_text": "中(P2)", "note": "", "scene": "山区避障场景"},
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

    def render_3d(self, ax):
        x_range, y_range, z_range = self.get_bounds()

        gx = np.linspace(x_range[0], x_range[1], 170)
        gy = np.linspace(y_range[0], y_range[1], 170)
        GX, GY = np.meshgrid(gx, gy)
        terrain = self.get_terrain_height(GX, GY)

        # Standard topographic-like contour colors:
        # low elevation green -> yellow -> brown -> high elevation gray-white
        topo_cmap = LinearSegmentedColormap.from_list(
            "topo_green",
            ["#1B5E20", "#2E7D32", "#43A047", "#66BB6A", "#A5D6A7", "#C8E6C9", "#E8F5E9"],
            N=256,
        )

        levels = np.linspace(8, float(np.max(terrain)) - 1, 40)
        if levels.size > 1:
            contour_colors = topo_cmap(np.linspace(0.05, 0.98, len(levels)))
            ax.contour3D(GX, GY, terrain, levels=levels, colors=contour_colors, linewidths=1.3, alpha=1.0)
            # Ground plane (opaque, no shadow projection)
            gx_flat = np.linspace(x_range[0], x_range[1], 8)
            gy_flat = np.linspace(y_range[0], y_range[1], 8)
            GX0, GY0 = np.meshgrid(gx_flat, gy_flat)
            ax.plot_surface(GX0, GY0, np.zeros_like(GX0), color="#1A2830", alpha=0.02, linewidth=0)

        ax.set_xlim(*x_range)
        ax.set_ylim(*y_range)
        ax.set_zlim(*z_range)
        ax.set_title(self.name, fontsize=10, color="#E6E8EC", pad=8)




