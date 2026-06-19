import numpy as np
from dispatch_page import BaseMap


class Map(BaseMap):
    name = "城市地震场景"
    desc = "城市震后场景，包含街区建筑、主干道和局部废墟障碍"

    def get_obstacles(self):
        obstacles = []
        blocks = [
            (-180, 180, 55, 60, 45),
            (-60, 170, 48, 52, 38),
            (80, 180, 60, 66, 46),
            (200, 170, 52, 58, 40),
            (-170, 20, 44, 56, 34),
            (-30, 25, 58, 60, 42),
            (120, 10, 46, 54, 34),
            (220, 0, 40, 50, 30),
            (-190, -150, 42, 50, 30),
            (-60, -170, 50, 58, 38),
            (90, -160, 62, 64, 48),
            (220, -140, 45, 54, 34),
        ]
        for x, y, w, h, z in blocks:
            obstacles.append({"center": [x, y, z / 2], "size": [w, h, z], "type": "building"})

        rubble = [
            (-20, -55, 16, 12, 10),
            (35, -80, 18, 14, 12),
            (70, -40, 14, 10, 9),
            (10, 35, 20, 12, 10),
        ]
        for x, y, w, h, z in rubble:
            obstacles.append({"center": [x, y, z / 2], "size": [w, h, z], "type": "debris"})

        return obstacles

    def get_bounds(self):
        return ((-280, 280), (-260, 260), (0, 160))

    def _draw_box(self, ax, cx, cy, w, h, z_top, color, alpha):
        x = [cx - w / 2, cx + w / 2]
        y = [cy - h / 2, cy + h / 2]
        xx, yy = np.meshgrid(x, y)
        ax.plot_surface(xx, yy, np.full_like(xx, z_top), color=color, alpha=alpha, linewidth=0)

        z = [0, z_top]
        for xi in x:
            yz_y, yz_z = np.meshgrid(y, z)
            ax.plot_surface(np.full_like(yz_y, xi), yz_y, yz_z, color=color, alpha=alpha * 0.72, linewidth=0)
        for yi in y:
            xz_x, xz_z = np.meshgrid(x, z)
            ax.plot_surface(xz_x, np.full_like(xz_x, yi), xz_z, color=color, alpha=alpha * 0.72, linewidth=0)

    def render_3d(self, ax):
        x_range, y_range, z_range = self.get_bounds()

        gx = np.linspace(x_range[0], x_range[1], 24)
        gy = np.linspace(y_range[0], y_range[1], 24)
        GX, GY = np.meshgrid(gx, gy)
        GZ = np.zeros_like(GX)
        ax.plot_surface(GX, GY, GZ, alpha=0.22, color="#3E4A58", linewidth=0)

        road_color = "#5D6776"
        for x_pos in range(-240, 241, 120):
            ax.plot([x_pos, x_pos], [y_range[0], y_range[1]], [1, 1], color=road_color, alpha=0.45, linewidth=1.2)
        for y_pos in range(-200, 201, 120):
            ax.plot([x_range[0], x_range[1]], [y_pos, y_pos], [1, 1], color=road_color, alpha=0.45, linewidth=1.2)

        for obs in self.get_obstacles():
            cx, cy, _ = obs["center"]
            w, h, z = obs["size"]
            if obs["type"] == "building":
                self._draw_box(ax, cx, cy, w, h, z, color="#8A5A3C", alpha=0.56)
            else:
                self._draw_box(ax, cx, cy, w, h, z, color="#6D7480", alpha=0.48)

        ax.set_xlim(*x_range)
        ax.set_ylim(*y_range)
        ax.set_zlim(*z_range)
        ax.set_title(self.name, fontsize=10, color="#E6E8EC", pad=8)
