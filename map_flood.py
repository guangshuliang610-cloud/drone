import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from dispatch_page import BaseMap


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

    def get_bounds(self):
        return ((-320, 320), (-300, 300), (0, 220))

    def _ridge(self, gx, gy, x0, y0, amp, sx, sy, theta_deg):
        t = np.deg2rad(theta_deg)
        xr = (gx - x0) * np.cos(t) + (gy - y0) * np.sin(t)
        yr = -(gx - x0) * np.sin(t) + (gy - y0) * np.cos(t)
        return amp * np.exp(-((xr / sx) ** 2 + (yr / sy) ** 2))

    def render_3d(self, ax):
        x_range, y_range, z_range = self.get_bounds()

        gx = np.linspace(x_range[0], x_range[1], 170)
        gy = np.linspace(y_range[0], y_range[1], 170)
        GX, GY = np.meshgrid(gx, gy)

        # West-high / east-low macro gradient, like a simplified topographic map.
        terrain = 26 - 0.048 * GX
        terrain += 2.4 * np.sin((GY + 60) / 230.0) + 1.7 * np.cos((GX - 40) / 270.0)

        # Western highlands (broad uplift)
        terrain += self._ridge(GX, GY, -245, 10, 62, 240, 120, -12)
        terrain += self._ridge(GX, GY, -230, -170, 42, 190, 88, -30)

        # Central mountain system (north-south arc)
        terrain += self._ridge(GX, GY, -120, 140, 46, 170, 66, -28)
        terrain += self._ridge(GX, GY, -55, 15, 52, 185, 70, -20)
        terrain += self._ridge(GX, GY, 20, -120, 44, 175, 64, -25)

        # Northeast branch mountains
        terrain += self._ridge(GX, GY, 110, 165, 36, 125, 56, 34)
        terrain += self._ridge(GX, GY, 205, 115, 28, 110, 48, 30)

        # Southwest basin depression for stronger contrast.
        basin = 30 * np.exp(-(((GX + 190) / 125) ** 2 + ((GY + 220) / 90) ** 2))
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
            terrain += amp * np.exp(-(((GX - cx) / sx) ** 2 + ((GY - cy) / sy) ** 2))

        terrain = np.clip(terrain, 0, z_range[1] - 4)

        # Standard topographic-like contour colors:
        # low elevation green -> yellow -> brown -> high elevation gray-white
        topo_cmap = LinearSegmentedColormap.from_list(
            "topo_std",
            ["#5E9E4E", "#8FBF5C", "#C9C86A", "#C89A5A", "#9A6D46", "#8A8A82", "#E8E8E3"],
            N=256,
        )

        levels = np.linspace(8, float(np.max(terrain)) - 1, 40)
        if levels.size > 1:
            contour_colors = topo_cmap(np.linspace(0.05, 0.98, len(levels)))
            ax.contour3D(GX, GY, terrain, levels=levels, colors=contour_colors, linewidths=1.05, alpha=0.98)
            ax.contour(
                GX,
                GY,
                terrain,
                levels=levels,
                zdir="z",
                offset=0,
                colors=contour_colors,
                linewidths=0.82,
                alpha=0.80,
            )

        ax.set_xlim(*x_range)
        ax.set_ylim(*y_range)
        ax.set_zlim(*z_range)
        ax.set_title(self.name, fontsize=10, color="#E6E8EC", pad=8)
