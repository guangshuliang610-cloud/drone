import importlib.util
import os
import traceback
import json

import site as _site
for _sp in _site.getsitepackages() + [_site.getusersitepackages()]:
    _candidate = os.path.join(_sp, "PyQt5", "Qt5", "bin")
    if os.path.isdir(_candidate):
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(_candidate)
        os.environ["PATH"] = _candidate + os.pathsep + os.environ.get("PATH", "")
        break

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QTextEdit, QSplitter, QSizePolicy
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel

from config import (
    DARK_BG, PANEL_BG, INPUT_BG, TEXT_MAIN, TEXT_SUB, SUCCESS, ERROR, WARNING, BORDER,
    MAPS_FILE, ALGORITHMS_FILE, DEFAULT_MAPS, DEFAULT_ALGORITHMS,
    MATERIALS_FILE, SERVICE_AREAS_FILE, RESCUE_POINTS_FILE,
    DEFAULT_SERVICE_AREAS, DEFAULT_RESCUE_POINTS, BASE_DIR
)
from utils import load_json


class BaseMap:
    name = "\u672a\u547d\u540d\u5730\u56fe"
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
    name = "\u672a\u547d\u540d\u7b97\u6cd5"
    desc = ""

    def solve(self, drones, materials, service_areas, rescue_points, map_obj):
        raise NotImplementedError("Please implement solve()")

    def render_result(self, ax, result):
        pass


class PlotlyCanvas(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 400)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._traces = []
        self._layout = {}
        self._init_page()

    def _init_page(self):
        html = """
<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>body{margin:0;padding:0;background:#12161B;overflow:hidden}
#plot{width:100vw;height:100vh}</style>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
</head><body>
<div id="plot"></div>
<script>
var layout = {
  paper_bgcolor:"#12161B",
  scene:{
    bgcolor:"#12161B",
    xaxis:{gridcolor:"#2B3441",color:"#A3AFBF",title:"X (m)"},
    yaxis:{gridcolor:"#2B3441",color:"#A3AFBF",title:"Y (m)"},
    zaxis:{gridcolor:"#2B3441",color:"#A3AFBF",title:"Z (m)"},
    aspectratio:{x:1,y:1,z:0.55},
    camera:{eye:{x:1.4,y:-1.8,z:0.8}}
  },
  margin:{l:0,r:0,t:30,b:0},
  showlegend:true,
  legend:{x:0,y:1,bgcolor:"rgba(26,32,40,0.8)",font:{color:"#E6E8EC",size:11}},
  font:{color:"#A3AFBF"}
};
Plotly.newPlot("plot",[],layout,{responsive:true,displayModeBar:false});
</script></body></html>
"""
        self.setHtml(html)
        self._loaded = False
        self.loadFinished.connect(self._on_load)

    def _on_load(self, ok):
        self._loaded = True

    def clear_plot(self):
        self._traces = []
        self._layout = {}
        if self._loaded:
            self.page().runJavaScript(
                "Plotly.purge(document.getElementById(\"plot\"));"
            )

    def set_figure(self, fig_json):
        if self._loaded:
            js = "Plotly.react(document.getElementById(\"plot\"), %s);" % fig_json
            self.page().runJavaScript(js)

    def add_traces(self, traces_json):
        if self._loaded:
            js = "Plotly.addTraces(document.getElementById(\"plot\"), %s);" % traces_json
            self.page().runJavaScript(js)

    def refresh(self):
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

        # Top bar: controls left, title right
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        top_bar.addWidget(QLabel("\u573a\u666f:"))
        self.map_combo = QComboBox()
        self.map_combo.setMinimumHeight(34)
        self.map_combo.setMaximumWidth(200)
        for m in self.maps:
            self.map_combo.addItem(m["name"], m)
        self.map_combo.currentIndexChanged.connect(self._on_map_changed)
        top_bar.addWidget(self.map_combo)

        top_bar.addWidget(QLabel("\u7b97\u6cd5:"))
        self.algo_combo = QComboBox()
        self.algo_combo.setMinimumHeight(34)
        self.algo_combo.setMaximumWidth(200)
        for a in self.algorithms:
            self.algo_combo.addItem(a["name"], a)
        self.algo_combo.currentIndexChanged.connect(self._on_algo_changed)
        top_bar.addWidget(self.algo_combo)

        self.start_btn = QPushButton("\u5f00\u59cb\u8c03\u5ea6")
        self.start_btn.setMinimumHeight(34)
        self.start_btn.setMinimumWidth(90)
        self.start_btn.setStyleSheet(
            "QPushButton{background:%s;color:white;border:none;border-radius:6px;font-size:14px;font-weight:bold}"
            "QPushButton:hover{background:#3A9A7A}" % SUCCESS
        )
        self.start_btn.clicked.connect(self._on_start)
        top_bar.addWidget(self.start_btn)

        self.status_label = QLabel("\u5c31\u7eea")
        self.status_label.setStyleSheet(f"color:{TEXT_SUB};font-size:14px;background:transparent;")
        top_bar.addWidget(self.status_label)

        top_bar.addStretch()

        self.title_label = QLabel("\u6551\u63f4\u8c03\u5ea6")
        self.title_label.setStyleSheet(f"color:{TEXT_MAIN};font-size:18px;font-weight:bold;background:transparent;")
        top_bar.addWidget(self.title_label)

        layout.addLayout(top_bar)

        # Main area: Plotly canvas + log panel
        self.canvas = PlotlyCanvas(self)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(80)
        self.log_text.setMaximumHeight(140)
        self.log_text.setStyleSheet(
            f"background:{INPUT_BG};color:{TEXT_SUB};border:1px solid {BORDER};border-radius:6px;font-size:12px;font-family:Consolas,monospace;padding:6px;"
        )

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.log_text)
        splitter.setStretchFactor(0, 10)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, stretch=1)

        # Placeholder refs for compatibility
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
        self._log("\u8c03\u5ea6\u4efb\u52a1\u542f\u52a8")

        map_data = self.map_combo.currentData()
        if not map_data:
            self._log("\u672a\u9009\u62e9\u573a\u666f")
            return

        algo_data = self.algo_combo.currentData()
        if not algo_data:
            self._log("\u672a\u9009\u62e9\u7b97\u6cd5")
            return

        try:
            self.current_map = self._load_module(map_data["file"], "Map")
            self.current_algo = self._load_module(algo_data["file"], "Algorithm")
        except Exception as e:
            self._log(f"\u52a0\u8f7d\u5931\u8d25: {e}")
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
            self._log("\u6ca1\u6709\u65e0\u4eba\u673a\uff0c\u8bf7\u5148\u5728\u65e0\u4eba\u673a\u7ba1\u7406\u9875\u914d\u7f6e")
            return
        if not materials:
            self._log("\u6ca1\u6709\u7269\u8d44\uff0c\u8bf7\u5148\u5728\u7269\u8d44\u7ba1\u7406\u9875\u6dfb\u52a0")
            return

        self.canvas.clear_plot()

        # Get map figure (Plotly)
        try:
            map_fig = self.current_map.render_plotly()
        except Exception as e:
            self._log(f"\u5730\u56fe\u6e32\u67d3\u5931\u8d25: {e}")
            return

        self.status_label.setText("\u8c03\u5ea6\u4e2d...")
        self.status_label.setStyleSheet(f"color:{WARNING};font-size:14px;background:transparent;")
        self.start_btn.setEnabled(False)

        try:
            result = self.current_algo.solve(drones, materials, service_areas, rescue_points, self.current_map)
            self._log(result.get("message", "\u8c03\u5ea6\u5b8c\u6210"))

            # Add trajectory traces to map figure
            try:
                traj_traces = self.current_algo.render_plotly(result)
                for trace in traj_traces:
                    map_fig.add_trace(trace)
            except Exception as e:
                self._log(f"\u8f68\u8ff9\u6e32\u67d3\u5931\u8d25: {e}")

            # Send figure to canvas
            fig_json = map_fig.to_json()
            self.canvas.set_figure(fig_json)

            self.status_label.setText("\u8c03\u5ea6\u5b8c\u6210")
            self.status_label.setStyleSheet(f"color:{SUCCESS};font-size:14px;background:transparent;")

        except Exception as e:
            self._log(f"\u7b97\u6cd5\u8fd0\u884c\u51fa\u9519: {e}")
            self._log(traceback.format_exc())
            self.status_label.setText("\u8c03\u5ea6\u5931\u8d25")
            self.status_label.setStyleSheet(f"color:{ERROR};font-size:14px;background:transparent;")

        self.start_btn.setEnabled(True)
        self._log("\u8c03\u5ea6\u4efb\u52a1\u7ed3\u675f")
        self._log("=" * 40)
