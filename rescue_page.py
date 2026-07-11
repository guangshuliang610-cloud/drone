"""
应急无人机调度系统 — 救援点管理页面
文件：rescue_page.py
"""

import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QDoubleSpinBox, QComboBox, QDialog, QFormLayout,
    QDialogButtonBox, QMessageBox, QAbstractItemView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from config import (
    SCENES,
    PRIORITY_MAP, PRIORITY_COLORS, TEXT_MAIN, TEXT_SUB, ACCENT,
    RESCUE_POINTS_FILE, DEFAULT_RESCUE_POINTS, CONTOUR_DATA_FILE
)
from utils import load_json, save_json, hc

# Terrain height cache (lazy-loaded)
_terrain_cache = None

# SCENES imported from config
SCENE_BOUNDS = {
    "山区避障场景": (-320, 320, -300, 300, 0, 220),
    "城市地震场景": (-420, 420, -390, 390, 0, 160),
}


def _load_terrain_cache():
    global _terrain_cache
    if _terrain_cache is not None:
        return _terrain_cache

    import json
    import os
    if not os.path.exists(CONTOUR_DATA_FILE):
        try:
            from map_flood import Map
            m = Map()
            data = m.get_contour_lines(grid_size=170)
            _terrain_cache = {
                "gx": np.array(data["grid"]["x"]),
                "gy": np.array(data["grid"]["y"]),
                "gz": np.array(data["grid"]["z"]),
            }
            return _terrain_cache
        except Exception:
            return None

    with open(CONTOUR_DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    _terrain_cache = {
        "gx": np.array(data["grid"]["x"]),
        "gy": np.array(data["grid"]["y"]),
        "gz": np.array(data["grid"]["z"]),
    }
    return _terrain_cache


def _get_terrain_height_at(x, y):
    cache = _load_terrain_cache()
    if cache is None:
        return 0.0

    gx = cache["gx"]
    gy = cache["gy"]
    gz = cache["gz"]

    if x < gx[0] or x > gx[-1] or y < gy[0] or y > gy[-1]:
        return 0.0

    xi = np.searchsorted(gx, x) - 1
    yi = np.searchsorted(gy, y) - 1
    xi = max(0, min(xi, len(gx) - 2))
    yi = max(0, min(yi, len(gy) - 2))

    x0, x1 = gx[xi], gx[xi + 1]
    y0, y1 = gy[yi], gy[yi + 1]

    if x1 == x0 or y1 == y0:
        return float(gz[yi][xi])

    fx = (x - x0) / (x1 - x0)
    fy = (y - y0) / (y1 - y0)

    z00 = gz[yi][xi]
    z10 = gz[yi][xi + 1]
    z01 = gz[yi + 1][xi]
    z11 = gz[yi + 1][xi + 1]

    z = (z00 * (1 - fx) * (1 - fy) +
         z10 * fx * (1 - fy) +
         z01 * (1 - fx) * fy +
         z11 * fx * fy)

    return float(z)


class RescuePointEditDialog(QDialog):
    def __init__(self, parent=None, point=None, scene="山区避障场景"):
        super().__init__(parent)
        self.setWindowTitle("编辑救援点" if point else "添加救援点")
        self.setMinimumWidth(520)
        self.point = point
        self.scene = scene
        self.result_data = None
        self._build_ui()
        if point:
            self._load(point)
        else:
            self._update_z_from_terrain()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(28, 28, 28, 28)

        scene_label = QLabel(f"📍 {'编辑' if self.point else '添加'}救援点 — {self.scene}")
        scene_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        scene_label.setStyleSheet(f"color: {TEXT_MAIN}; background: transparent;")
        layout.addWidget(scene_label)

        form = QFormLayout()
        form.setSpacing(16)
        form.setLabelAlignment(Qt.AlignRight)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：灾区A - 居民区、中心医院...")
        self.name_edit.setMinimumHeight(40)
        form.addRow("救援点名称：", self.name_edit)

        bounds = SCENE_BOUNDS.get(self.scene, (-320, 320, -300, 300, 0, 220))
        x_min, x_max, y_min, y_max, z_min, z_max = bounds

        coord_widget = QWidget()
        cl = QHBoxLayout(coord_widget)
        cl.setSpacing(12)

        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(x_min, x_max)
        self.x_spin.setDecimals(1)
        self.x_spin.setPrefix("X: ")
        self.x_spin.setMinimumHeight(40)
        self.x_spin.valueChanged.connect(self._update_z_from_terrain)
        cl.addWidget(self.x_spin)

        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(y_min, y_max)
        self.y_spin.setDecimals(1)
        self.y_spin.setPrefix("Y: ")
        self.y_spin.setMinimumHeight(40)
        self.y_spin.valueChanged.connect(self._update_z_from_terrain)
        cl.addWidget(self.y_spin)

        self.z_spin = QDoubleSpinBox()
        self.z_spin.setRange(z_min, z_max)
        self.z_spin.setDecimals(1)
        self.z_spin.setPrefix("Z: ")
        self.z_spin.setMinimumHeight(40)
        self.z_spin.setReadOnly(True)
        self.z_spin.setStyleSheet("QDoubleSpinBox { color: #888; background: #1A1F26; }")
        cl.addWidget(self.z_spin)
        form.addRow("三维坐标：", coord_widget)

        hint = QLabel("  Z坐标根据X/Y自动匹配地形高度")
        hint.setStyleSheet(f"color: {TEXT_SUB}; font-size: 12px;")
        form.addRow("", hint)

        pri_combo_widget = QWidget()
        pl = QHBoxLayout(pri_combo_widget)
        self.pri_combo = QComboBox()
        self.pri_combo.addItems(PRIORITY_MAP.keys())
        self.pri_combo.setMinimumHeight(40)
        pl.addWidget(self.pri_combo)
        form.addRow("配送优先级：", pri_combo_widget)

        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("可选，填写特殊情况说明")
        self.note_edit.setMinimumHeight(40)
        form.addRow("备    注：", self.note_edit)

        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("确 认")
        btns.button(QDialogButtonBox.Cancel).setText("取 消")
        btns.button(QDialogButtonBox.Ok).setObjectName("primary")
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _update_z_from_terrain(self):
        x = self.x_spin.value()
        y = self.y_spin.value()
        if self.scene == "山区避障场景":
            z = _get_terrain_height_at(x, y)
        else:
            z = 0.0
        self.z_spin.setValue(z)

    def _load(self, p):
        self.name_edit.setText(p.get("name", ""))
        self.x_spin.setValue(p.get("x", 0))
        self.y_spin.setValue(p.get("y", 0))
        self.z_spin.setValue(p.get("z", 0))
        idx = self.pri_combo.findText(p.get("priority_text", "高(P1)"))
        if idx >= 0:
            self.pri_combo.setCurrentIndex(idx)
        self.note_edit.setText(p.get("note", ""))

    def _on_ok(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请输入救援点名称")
            return
        pri_text = self.pri_combo.currentText()
        self.result_data = {
            "name": self.name_edit.text().strip(),
            "x": self.x_spin.value(),
            "y": self.y_spin.value(),
            "z": self.z_spin.value(),
            "priority": PRIORITY_MAP.get(pri_text, 2),
            "priority_text": pri_text,
            "note": self.note_edit.text().strip(),
            "scene": self.scene,
        }
        self.accept()


class RescuePointPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_points = load_json(RESCUE_POINTS_FILE, DEFAULT_RESCUE_POINTS)
        self.points = self.all_points[:]
        self._build_ui()
        self._refresh_table()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        header = QHBoxLayout()
        self.title_label = QLabel("📍 救援点管理")
        self.title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        self.title_label.setStyleSheet(f"color: {TEXT_MAIN}; background: transparent;")
        header.addWidget(self.title_label)
        header.addStretch()

        self.scene_combo = QComboBox()
        self.scene_combo.addItems(SCENES)
        self.scene_combo.setMinimumHeight(34)
        self.scene_combo.setMaximumWidth(180)
        self.scene_combo.currentTextChanged.connect(self._on_scene_changed)
        header.addWidget(QLabel("场景:"))
        header.addWidget(self.scene_combo)

        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet(f"color: {TEXT_SUB}; font-size: 14px; background: transparent;")
        header.addWidget(self.stats_label)
        layout.addLayout(header)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        add_btn = QPushButton("➕ 添加救援点")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._add)
        btn_row.addWidget(add_btn)
        edit_btn = QPushButton("✏️ 编辑")
        edit_btn.clicked.connect(self._edit)
        btn_row.addWidget(edit_btn)
        del_btn = QPushButton("🗑️ 删除")
        del_btn.setObjectName("danger")
        del_btn.clicked.connect(self._delete)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "救援点名称", "X 坐标", "Y 坐标", "Z 坐标", "配送优先级", "场景", "备注"
        ])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 5):
            h.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(6, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table, stretch=1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        scale = max(0.7, min(2.0, w / 900))
        self.title_label.setFont(QFont("Microsoft YaHei", max(14, int(18 * scale)), QFont.Bold))

    def _on_scene_changed(self, scene):
        if scene == "全部场景":
            self.points = self.all_points[:]
        else:
            self.points = [p for p in self.all_points if p.get("scene", "") == scene]
        self._refresh_table()

    def _refresh_table(self):
        self.table.setRowCount(len(self.points))
        for i, p in enumerate(self.points):
            name_item = QTableWidgetItem(p.get("name", ""))
            name_item.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
            self.table.setItem(i, 0, name_item)

            for j, key in enumerate(["x", "y", "z"]):
                val_item = QTableWidgetItem(f"{p.get(key, 0):.1f}")
                val_item.setTextAlignment(Qt.AlignCenter)
                val_item.setFont(QFont("Consolas", 14))
                self.table.setItem(i, j + 1, val_item)

            pri = p.get("priority", 2)
            pri_item = QTableWidgetItem(p.get("priority_text", f"P{pri}"))
            pri_item.setTextAlignment(Qt.AlignCenter)
            pri_item.setForeground(hc(PRIORITY_COLORS.get(pri, TEXT_SUB)))
            pri_item.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
            self.table.setItem(i, 4, pri_item)

            scene_item = QTableWidgetItem(p.get("scene", ""))
            scene_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 5, scene_item)

            note_item = QTableWidgetItem(p.get("note", ""))
            self.table.setItem(i, 6, note_item)

        self.stats_label.setText(f"共{len(self.points)} 个救援点")

    def _current_scene(self):
        scene = self.scene_combo.currentText()
        if scene == "全部场景":
            return "山区避障场景"
        return scene

    def _add(self):
        dlg = RescuePointEditDialog(self, scene=self._current_scene())
        if dlg.exec_() == QDialog.Accepted and dlg.result_data:
            self.all_points.append(dlg.result_data)
            save_json(RESCUE_POINTS_FILE, self.all_points)
            self._on_scene_changed(self.scene_combo.currentText())

    def _edit(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选中一个救援点")
            return
        real_idx = self._real_index(row)
        if real_idx is None:
            return
        dlg = RescuePointEditDialog(self, point=self.all_points[real_idx], scene=self.all_points[real_idx].get("scene", "山区避障场景"))
        if dlg.exec_() == QDialog.Accepted and dlg.result_data:
            self.all_points[real_idx] = dlg.result_data
            save_json(RESCUE_POINTS_FILE, self.all_points)
            self._on_scene_changed(self.scene_combo.currentText())

    def _delete(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选中一个救援点")
            return
        real_idx = self._real_index(row)
        if real_idx is None:
            return
        name = self.all_points[real_idx].get("name", "")
        if QMessageBox.question(self, "确认", f"删除救援点\"{name}\"？",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.all_points.pop(real_idx)
            save_json(RESCUE_POINTS_FILE, self.all_points)
            self._on_scene_changed(self.scene_combo.currentText())

    def _real_index(self, display_row):
        if self.scene_combo.currentText() == "全部场景":
            return display_row
        p = self.points[display_row]
        for i, ap in enumerate(self.all_points):
            if ap is p:
                return i
        return None


