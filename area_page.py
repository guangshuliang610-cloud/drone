"""
应急无人机调度系统 — 服务区管理页面
文件：area_page.py
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QDoubleSpinBox, QSpinBox, QComboBox, QDialog, QFormLayout,
    QDialogButtonBox, QMessageBox, QAbstractItemView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from config import (
    SCENES,
    TEXT_MAIN, TEXT_SUB, ACCENT, BORDER,
    SERVICE_AREAS_FILE, DEFAULT_SERVICE_AREAS
)
from utils import load_json, save_json, hc
from rescue_page import _get_terrain_height_at, _get_building_at_xy, _get_max_floor, FLOOR_HEIGHT

SCENE_BOUNDS = {
    "山区避障场景": (-320, 320, -300, 300, 0, 220),
    "城市地震场景": (-420, 420, -390, 390, 0, 160),
}


class ServiceAreaEditDialog(QDialog):
    def __init__(self, parent=None, area=None, scene="山区避障场景"):
        super().__init__(parent)
        self.setWindowTitle("编辑服务区" if area else "添加服务区")
        self.setMinimumWidth(520)
        self.area = area
        self.scene = scene
        self.result_data = None
        self._block_z_update = False
        self._build_ui()
        if area:
            self._load(area)
        else:
            self._update_z_auto()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(28, 28, 28, 28)

        title = QLabel(f"🏗 {'编辑' if self.area else '添加'}服务区 — {self.scene}")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT_MAIN}; background: transparent;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(16)
        form.setLabelAlignment(Qt.AlignRight)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例：北区服务区、一号集结点...")
        self.name_edit.setMinimumHeight(40)
        form.addRow("名    称：", self.name_edit)

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
        self.x_spin.valueChanged.connect(self._update_z_auto)
        cl.addWidget(self.x_spin)
        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(y_min, y_max)
        self.y_spin.setDecimals(1)
        self.y_spin.setPrefix("Y: ")
        self.y_spin.setMinimumHeight(40)
        self.y_spin.valueChanged.connect(self._update_z_auto)
        cl.addWidget(self.y_spin)
        self.z_spin = QDoubleSpinBox()
        self.z_spin.setRange(z_min, z_max)
        self.z_spin.setDecimals(1)
        self.z_spin.setPrefix("Z: ")
        self.z_spin.setMinimumHeight(40)
        self.z_spin.setReadOnly(True)
        self.z_spin.setStyleSheet("QDoubleSpinBox { background-color: #222830; color: #7C8796; }")
        cl.addWidget(self.z_spin)
        form.addRow("三维坐标：", coord_widget)

        # Floor selector for city scene (hidden by default)
        self.floor_widget = QWidget()
        fl = QHBoxLayout(self.floor_widget)
        fl.setSpacing(12)
        fl.setContentsMargins(0, 0, 0, 0)
        self.floor_spin = QSpinBox()
        self.floor_spin.setRange(1, 1)
        self.floor_spin.setValue(1)
        self.floor_spin.setMinimumHeight(40)
        self.floor_spin.setMinimumWidth(100)
        self.floor_spin.valueChanged.connect(self._on_floor_changed)
        fl.addWidget(self.floor_spin)
        self.floor_info_label = QLabel("")
        self.floor_info_label.setStyleSheet(f"color: {TEXT_SUB}; font-size: 13px; background: transparent;")
        fl.addWidget(self.floor_info_label)
        fl.addStretch()
        form.addRow("所在楼层：", self.floor_widget)

        self.z_hint_label = QLabel("")
        self.z_hint_label.setStyleSheet(f"color: {TEXT_SUB}; font-size: 12px; background: transparent;")
        form.addRow("", self.z_hint_label)

        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("确 认")
        btns.button(QDialogButtonBox.Cancel).setText("取 消")
        btns.button(QDialogButtonBox.Ok).setObjectName("primary")
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        # Initial UI state
        self._update_floor_visibility()

    def _update_floor_visibility(self):
        """Show/hide floor selector based on scene."""
        is_city = self.scene == "城市地震场景"
        self.floor_widget.setVisible(is_city)
        if not is_city:
            self.floor_info_label.setText("")

    def _update_z_auto(self):
        """Auto-calculate Z based on scene: mountain=terrain height, city=floor*3m."""
        if self._block_z_update:
            return
        x = self.x_spin.value()
        y = self.y_spin.value()

        if self.scene == "山区避障场景":
            z = _get_terrain_height_at(x, y)
            self._block_z_update = True
            self.z_spin.setValue(round(z, 1))
            self._block_z_update = False
            self.z_hint_label.setText(f"地形高程: {z:.1f}m（自动匹配山体表面）")
            self.floor_widget.setVisible(False)
        elif self.scene == "城市地震场景":
            building = _get_building_at_xy(x, y)
            if building:
                max_floor = _get_max_floor(building)
                self.floor_spin.setRange(1, max_floor)
                self.floor_spin.setValue(1)
                self.floor_info_label.setText(
                    f"建筑高度 {building['height']:.0f}m，共 {max_floor} 层"
                )
                self._on_floor_changed()
                self.z_hint_label.setText("服务区设在建筑内（选择楼层自动计算Z）")
            else:
                self._block_z_update = True
                self.z_spin.setValue(0.0)
                self._block_z_update = False
                self.floor_spin.setRange(1, 1)
                self.floor_spin.setValue(1)
                self.floor_info_label.setText("空旷地面")
                self.z_hint_label.setText("服务区在空旷地面，Z=0")
            self._update_floor_visibility()
        else:
            self._update_floor_visibility()

    def _on_floor_changed(self):
        """Update Z when floor changes (city scene)."""
        if self.scene != "城市地震场景":
            return
        floor = self.floor_spin.value()
        z = round(floor * FLOOR_HEIGHT, 1)
        self._block_z_update = True
        self.z_spin.setValue(z)
        self._block_z_update = False

    def _load(self, a):
        self._block_z_update = True
        self.name_edit.setText(a.get("name", ""))
        self.x_spin.setValue(a.get("x", 0))
        self.y_spin.setValue(a.get("y", 0))
        self.z_spin.setValue(a.get("z", 0))
        self._block_z_update = False

        # Set floor spin for city scene
        if self.scene == "城市地震场景":
            z = a.get("z", 0)
            floor = max(1, round(z / FLOOR_HEIGHT))
            self.floor_spin.setValue(floor)
            building = _get_building_at_xy(a.get("x", 0), a.get("y", 0))
            if building:
                max_floor = _get_max_floor(building)
                self.floor_spin.setRange(1, max_floor)
                self.floor_info_label.setText(
                    f"建筑高度 {building['height']:.0f}m，共 {max_floor} 层"
                )
            else:
                self.floor_info_label.setText("空旷地面")
            self._update_floor_visibility()
        else:
            self._update_floor_visibility()

    def _on_ok(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请输入名称")
            return
        self.result_data = {
            "name": self.name_edit.text().strip(),
            "x": self.x_spin.value(),
            "y": self.y_spin.value(),
            "z": self.z_spin.value(),
            "scene": self.scene,
        }
        self.accept()


class ServiceAreaPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_areas = load_json(SERVICE_AREAS_FILE, DEFAULT_SERVICE_AREAS)
        self.areas = self.all_areas[:]
        self._build_ui()
        self._refresh_table()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        header = QHBoxLayout()
        self.title_label = QLabel("🏗 服务区管理")
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
        add_btn = QPushButton("➕ 添加服务区")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._add)
        btn_row.addWidget(add_btn)
        edit_btn = QPushButton("✏️ 编辑")
        edit_btn.clicked.connect(self._edit)
        btn_row.addWidget(edit_btn)
        del_btn = QPushButton("🗑 删除")
        del_btn.setObjectName("danger")
        del_btn.clicked.connect(self._delete)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["服务区名称", "X 坐标", "Y 坐标", "Z 坐标", "场景"])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 4):
            h.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeToContents)
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
            self.areas = self.all_areas[:]
        else:
            self.areas = [a for a in self.all_areas if a.get("scene", "") == scene]
        self._refresh_table()

    def _refresh_table(self):
        self.table.setRowCount(len(self.areas))
        for i, a in enumerate(self.areas):
            name_item = QTableWidgetItem(a.get("name", ""))
            name_item.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
            self.table.setItem(i, 0, name_item)
            for j, key in enumerate(["x", "y", "z"]):
                val_item = QTableWidgetItem(f"{a.get(key, 0):.1f}")
                val_item.setTextAlignment(Qt.AlignCenter)
                val_item.setFont(QFont("Consolas", 14))
                self.table.setItem(i, j + 1, val_item)
            scene_item = QTableWidgetItem(a.get("scene", ""))
            scene_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 4, scene_item)
        self.stats_label.setText(f"共 {len(self.areas)} 个服务区")

    def _current_scene(self):
        scene = self.scene_combo.currentText()
        if scene == "全部场景":
            return "山区避障场景"
        return scene

    def _add(self):
        dlg = ServiceAreaEditDialog(self, scene=self._current_scene())
        if dlg.exec_() == QDialog.Accepted and dlg.result_data:
            self.all_areas.append(dlg.result_data)
            save_json(SERVICE_AREAS_FILE, self.all_areas)
            self._on_scene_changed(self.scene_combo.currentText())

    def _edit(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选中一个服务区")
            return
        real_idx = self._real_index(row)
        if real_idx is None:
            return
        dlg = ServiceAreaEditDialog(self, area=self.all_areas[real_idx], scene=self.all_areas[real_idx].get("scene", "山区避障场景"))
        if dlg.exec_() == QDialog.Accepted and dlg.result_data:
            self.all_areas[real_idx] = dlg.result_data
            save_json(SERVICE_AREAS_FILE, self.all_areas)
            self._on_scene_changed(self.scene_combo.currentText())

    def _delete(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选中一个服务区")
            return
        real_idx = self._real_index(row)
        if real_idx is None:
            return
        name = self.all_areas[real_idx].get("name", "")
        if QMessageBox.question(self, "确认", f"删除服务区 \"{name}\"？",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.all_areas.pop(real_idx)
            save_json(SERVICE_AREAS_FILE, self.all_areas)
            self._on_scene_changed(self.scene_combo.currentText())

    def _real_index(self, display_row):
        if self.scene_combo.currentText() == "全部场景":
            return display_row
        a = self.areas[display_row]
        for i, aa in enumerate(self.all_areas):
            if aa is a:
                return i
        return None
