import importlib.util
import os
import traceback

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QTextEdit, QSplitter, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from config import (
    DARK_BG, PANEL_BG, INPUT_BG, TEXT_MAIN, TEXT_SUB, SUCCESS, ERROR, WARNING, BORDER,
    MAPS_FILE, ALGORITHMS_FILE, DEFAULT_MAPS, DEFAULT_ALGORITHMS,
    MATERIALS_FILE, SERVICE_AREAS_FILE, RESCUE_POINTS_FILE,
    DEFAULT_SERVICE_AREAS, DEFAULT_RESCUE_POINTS, BASE_DIR
)
from utils import load_json

import matplotlib
matplotlib.use("Qt5Agg")
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS"]
matplotlib.rcParams["axes.unicode_minus"] = False
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401


class BaseMap:
    name = "未命名地图"
    desc = ""

    def get_obstacles(self):
        return []

    def get_service_areas(self):
        return []

    def get_rescue_points(self):
        return []

    def get_bounds(self):
        return ((-500, 500), (-500, 500), (0, 200))

    def render_3d(self, ax):
        pass


class BaseAlgorithm:
    name = "未命名算法"
    desc = ""

    def solve(self, drones, materials, service_areas, rescue_points, map_obj):
        raise NotImplementedError("Please implement solve()")

    def render_result(self, ax, result):
        pass


class MapCanvas3D(FigureCanvasQTAgg):
    def __init__(self, parent=None):
        self.fig = Figure(facecolor=DARK_BG, dpi=100)
        super().__init__(self.fig)
        self.setParent(parent)
        self.setMinimumSize(600, 400)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ax = self.fig.add_subplot(111, projection="3d", facecolor=INPUT_BG)
        self.ax.computed_zorder = False
        self._style_axes()
        self.fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        self._fixed_elev = 26
        self._azim = -60
        self._drag_btn = None
        self._drag_x = 0
        self._drag_y = 0
        self._pan_xlim = None
        self._pan_ylim = None
        # Disable matplotlib default 3D mouse rotation to prevent wobble
        try:
            self.ax.disable_mouse_rotation()
        except Exception:
            pass
        self._bind_mouse()

    def _bind_mouse(self):
        canvas = self.fig.canvas
        canvas.mpl_connect("scroll_event", self._on_scroll)
        canvas.mpl_connect("button_press_event", self._on_press)
        canvas.mpl_connect("button_release_event", self._on_release)
        canvas.mpl_connect("motion_notify_event", self._on_motion)

    def _style_axes(self):
        ax = self.ax
        ax.set_facecolor(INPUT_BG)
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
        ax.xaxis.pane.set_edgecolor(BORDER)
        ax.yaxis.pane.set_edgecolor(BORDER)
        ax.zaxis.pane.set_edgecolor(BORDER)
        ax.tick_params(colors=TEXT_SUB, labelsize=7)
        ax.xaxis.label.set_color(TEXT_SUB)
        ax.yaxis.label.set_color(TEXT_SUB)
        ax.zaxis.label.set_color(TEXT_SUB)
        ax.set_xlabel("X (m)", fontsize=8)
        ax.set_ylabel("Y (m)", fontsize=8)
        ax.set_zlabel("Z (m)", fontsize=8)

    def clear_plot(self):
        self.fig.clear()
        self.ax = self.fig.add_subplot(111, projection="3d", facecolor=INPUT_BG)
        self.ax.computed_zorder = False
        self._style_axes()
        self.fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        try:
            self.ax.disable_mouse_rotation()
        except Exception:
            pass
        self._bind_mouse()

    def refresh(self):
        self.draw_idle()

    def _on_press(self, event):
        if event.inaxes != self.ax:
            return
        self._drag_btn = event.button
        self._drag_x = event.x
        self._drag_y = event.y
        self._pan_xlim = self.ax.get_xlim()
        self._pan_ylim = self.ax.get_ylim()

    def _on_release(self, event):
        self._drag_btn = None

    def _on_motion(self, event):
        if self._drag_btn is None or event.inaxes != self.ax:
            return
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        if self._drag_btn == 1:
            # Left drag: rotate around Z axis only (azimuth)
            self._azim -= dx * 0.15
            self.ax.view_init(elev=self._fixed_elev, azim=self._azim)
            self._drag_x = event.x
            self._drag_y = event.y
            self.draw_idle()
        elif self._drag_btn == 3:
            # Right drag: pan (shift xlim/ylim)
            if self._pan_xlim is None:
                return
            x_range = self._pan_xlim[1] - self._pan_xlim[0]
            y_range = self._pan_ylim[1] - self._pan_ylim[0]
            px = -dx * x_range / max(event.canvas.width(), 1) * 1.2
            py = -dy * y_range / max(event.canvas.height(), 1) * 1.2
            self.ax.set_xlim(self._pan_xlim[0] + px, self._pan_xlim[1] + px)
            self.ax.set_ylim(self._pan_ylim[0] + py, self._pan_ylim[1] + py)
            self.draw_idle()

    def _on_scroll(self, event):
        if event.button == "up":
            factor = 0.85
        elif event.button == "down":
            factor = 1.18
        else:
            return
        ax = self.ax
        try:
            xlim, ylim, zlim = ax.get_xlim(), ax.get_ylim(), ax.get_zlim()
            xm = (xlim[0] + xlim[1]) / 2
            ym = (ylim[0] + ylim[1]) / 2
            zm = (zlim[0] + zlim[1]) / 2
            ax.set_xlim(xm - (xm - xlim[0]) * factor, xm + (xlim[1] - xm) * factor)
            ax.set_ylim(ym - (ym - ylim[0]) * factor, ym + (ylim[1] - ym) * factor)
            ax.set_zlim(zm - (zm - zlim[0]) * factor, zm + (zlim[1] - zm) * factor)
            self.draw_idle()
        except Exception:
            pass

class DispatchPage(QWidget):
    def __init__(self, get_drones_func=None, parent=None):
        super().__init__(parent)
        self.get_drones_func = get_drones_func
        self.maps = self._keep_supported_maps(load_json(MAPS_FILE, DEFAULT_MAPS))
        self.algorithms = load_json(ALGORITHMS_FILE, DEFAULT_ALGORITHMS)
        self.current_map = None
        self.current_algo = None
        self._build_ui()

    def _keep_supported_maps(self, maps):
        supported = {"map_city_quake.py", "map_flood.py"}
        filtered = [m for m in maps if m.get("file") in supported]
        return filtered if filtered else maps

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(16, 10, 16, 10)

        # Top bar: title + controls + status, all in one compact row
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        top_bar.addWidget(QLabel("场景:"))
        self.map_combo = QComboBox()
        self.map_combo.setMinimumHeight(34)
        self.map_combo.setMaximumWidth(200)
        for m in self.maps:
            self.map_combo.addItem(m["name"], m)
        self.map_combo.currentIndexChanged.connect(self._on_map_changed)
        top_bar.addWidget(self.map_combo)

        top_bar.addWidget(QLabel("算法:"))
        self.algo_combo = QComboBox()
        self.algo_combo.setMinimumHeight(34)
        self.algo_combo.setMaximumWidth(200)
        for a in self.algorithms:
            self.algo_combo.addItem(a["name"], a)
        self.algo_combo.currentIndexChanged.connect(self._on_algo_changed)
        top_bar.addWidget(self.algo_combo)

        self.start_btn = QPushButton("开始调度")
        self.start_btn.setObjectName("start_btn")
        self.start_btn.setMinimumHeight(34)
        self.start_btn.setMinimumWidth(120)
        self.start_btn.clicked.connect(self._on_start)
        top_bar.addWidget(self.start_btn)

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet(f"color: {TEXT_SUB}; font-size: 13px; background: transparent;")
        top_bar.addWidget(self.status_label)

        top_bar.addStretch()

        self.title_label = QLabel("救援调度")
        self.title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        self.title_label.setStyleSheet(f"color: {TEXT_MAIN}; background: transparent;")
        top_bar.addWidget(self.title_label)
        layout.addLayout(top_bar)

        # Map canvas + log splitter, map gets most space
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)

        self.canvas = MapCanvas3D()
        splitter.addWidget(self.canvas)

        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(0, 4, 0, 0)
        log_layout.setSpacing(2)
        log_label = QLabel("运行日志")
        log_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        log_label.setStyleSheet(f"color: {TEXT_SUB}; background: transparent;")
        log_layout.addWidget(log_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet(
            f"QTextEdit {{ background-color: {INPUT_BG}; color: {TEXT_SUB}; border: 1px solid {BORDER}; border-radius: 6px; padding: 6px; }}"
        )
        self.log_text.setMaximumHeight(120)
        log_layout.addWidget(self.log_text)

        splitter.addWidget(log_widget)
        splitter.setStretchFactor(0, 10)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, stretch=1)

        # Placeholder refs for compatibility (no longer shown)
        self.map_desc = QLabel("")
        self.algo_desc = QLabel("")

        self._on_map_changed()
        self._on_algo_changed()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        scale = max(0.7, min(2.0, w / 900))
        self.title_label.setFont(QFont("Microsoft YaHei", max(14, int(18 * scale)), QFont.Bold))

    def _on_map_changed(self):
        data = self.map_combo.currentData()
        if data:
            self.map_desc.setText(data.get("desc", ""))

    def _on_algo_changed(self):
        data = self.algo_combo.currentData()
        if data:
            self.algo_desc.setText(data.get("desc", ""))

    def _log(self, msg):
        self.log_text.append(msg)

    def _load_module(self, file_name, class_name):
        path = os.path.join(BASE_DIR, file_name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")

        spec = importlib.util.spec_from_file_location(file_name.replace(".py", ""), path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        cls = getattr(module, class_name, None)
        if cls is None:
            raise AttributeError(f"{class_name} not found in {file_name}")
        return cls()

    def reload_config(self):
        self.maps = self._keep_supported_maps(load_json(MAPS_FILE, DEFAULT_MAPS))
        self.algorithms = load_json(ALGORITHMS_FILE, DEFAULT_ALGORITHMS)

    def _on_start(self):
        self.log_text.clear()
        self._log("=" * 40)
        self._log("调度任务启动")

        map_data = self.map_combo.currentData()
        if not map_data:
            self._log("未选择场景")
            return

        algo_data = self.algo_combo.currentData()
        if not algo_data:
            self._log("未选择算法")
            return

        try:
            self.current_map = self._load_module(map_data["file"], "Map")
            self.current_algo = self._load_module(algo_data["file"], "Algorithm")
        except Exception as e:
            self._log(f"加载失败: {e}")
            return

        materials = load_json(MATERIALS_FILE, [])
        service_areas = load_json(SERVICE_AREAS_FILE, DEFAULT_SERVICE_AREAS)
        rescue_points = load_json(RESCUE_POINTS_FILE, DEFAULT_RESCUE_POINTS)
        drones = self.get_drones_func() if self.get_drones_func else []

        map_sa = self.current_map.get_service_areas()
        if map_sa:
            service_areas = map_sa
        map_rp = self.current_map.get_rescue_points()
        if map_rp:
            rescue_points = map_rp

        if not drones:
            self._log("没有无人机，请先在无人机管理页配置")
            return
        if not materials:
            self._log("没有物资，请先在物资管理页添加")
            return

        self.canvas.clear_plot()
        try:
            self.current_map.render_3d(self.canvas.ax)
            self.canvas.ax.set_box_aspect((1.0, 1.0, 0.65))
        except Exception as e:
            self._log(f"地图渲染失败: {e}")

        self.status_label.setText("调度中...")
        self.status_label.setStyleSheet(f"color: {WARNING}; font-size: 14px; background: transparent;")
        self.start_btn.setEnabled(False)

        try:
            result = self.current_algo.solve(drones, materials, service_areas, rescue_points, self.current_map)
            self._log(result.get("message", "调度完成"))

            try:
                self.current_algo.render_result(self.canvas.ax, result)
            except Exception as e:
                self._log(f"轨迹渲染失败: {e}")

            try:
                self.canvas.ax.legend(
                    loc="upper left",
                    fontsize=8,
                    facecolor=PANEL_BG,
                    edgecolor=BORDER,
                    labelcolor=TEXT_MAIN,
                    prop={"family": "Microsoft YaHei"},
                )
            except Exception:
                pass

            self.canvas._azim = 128
            self.canvas._fixed_elev = 26
            self.canvas.ax.view_init(elev=26, azim=128)
            self.canvas.refresh()
            self.status_label.setText("调度完成")
            self.status_label.setStyleSheet(f"color: {SUCCESS}; font-size: 14px; background: transparent;")

        except Exception as e:
            self._log(f"算法运行出错: {e}")
            self._log(traceback.format_exc())
            self.status_label.setText("调度失败")
            self.status_label.setStyleSheet(f"color: {ERROR}; font-size: 14px; background: transparent;")

        self.start_btn.setEnabled(True)
        self._log("调度任务结束")
        self._log("=" * 40)

