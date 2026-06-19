"""
应急无人机调度系统 — 物资管理页面
文件：material_page.py
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QComboBox, QDoubleSpinBox, QSpinBox, QDialog, QFormLayout,
    QDialogButtonBox, QMessageBox, QAbstractItemView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from config import (
    PRIORITY_MAP, PRIORITY_COLORS, TEXT_MAIN, TEXT_SUB, ACCENT,
    BORDER, MATERIALS_FILE, SERVICE_AREAS_FILE, RESCUE_POINTS_FILE,
    DEFAULT_SERVICE_AREAS, DEFAULT_RESCUE_POINTS
)
from utils import load_json, save_json, hc


class MaterialDialog(QDialog):
    """物资编辑对话框"""
    def __init__(self, parent=None, material=None, service_areas=None, rescue_points=None):
        super().__init__(parent)
        self.setWindowTitle("编辑物资" if material else "添加物资")
        self.setMinimumWidth(520)
        self.material = material
        self.service_areas = service_areas or []
        self.rescue_points = rescue_points or []
        self.result_data = None
        self._build_ui()
        if material:
            self._load_data(material)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(28, 28, 28, 28)

        title = QLabel("📦 编辑物资" if self.material else "📦 添加物资")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT_MAIN}; background: transparent;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignRight)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例：医疗急救包、饮用水、帐篷...")
        self.name_edit.setMinimumHeight(40)
        form.addRow("物资名称：", self.name_edit)

        self.priority_combo = QComboBox()
        self.priority_combo.addItems(PRIORITY_MAP.keys())
        self.priority_combo.setMinimumHeight(40)
        form.addRow("配送优先级：", self.priority_combo)

        self.weight_spin = QDoubleSpinBox()
        self.weight_spin.setRange(0.1, 500.0)
        self.weight_spin.setSuffix(" kg")
        self.weight_spin.setDecimals(1)
        self.weight_spin.setValue(1.0)
        self.weight_spin.setMinimumHeight(40)
        form.addRow("物资重量：", self.weight_spin)

        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 10000)
        self.quantity_spin.setValue(1)
        self.quantity_spin.setMinimumHeight(40)
        form.addRow("物资数量：", self.quantity_spin)

        self.area_combo = QComboBox()
        for a in self.service_areas:
            self.area_combo.addItem(a.get("name", ""), a)
        self.area_combo.setMinimumHeight(40)
        form.addRow("初始服务区：", self.area_combo)

        self.rescue_combo = QComboBox()
        for r in self.rescue_points:
            self.rescue_combo.addItem(r.get("name", ""), r)
        self.rescue_combo.setMinimumHeight(40)
        form.addRow("配送救援点：", self.rescue_combo)

        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("可选，填写特殊要求...")
        self.note_edit.setMinimumHeight(40)
        form.addRow("备    注：", self.note_edit)

        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("确 认")
        btns.button(QDialogButtonBox.Cancel).setText("取 消")
        btns.button(QDialogButtonBox.Ok).setObjectName("primary")
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _load_data(self, m):
        self.name_edit.setText(m.get("name", ""))
        idx = self.priority_combo.findText(m.get("priority_text", "中 (P2)"))
        if idx >= 0:
            self.priority_combo.setCurrentIndex(idx)
        self.weight_spin.setValue(m.get("weight", 1.0))
        self.quantity_spin.setValue(m.get("quantity", 1))
        for i in range(self.area_combo.count()):
            if self.area_combo.itemText(i) == m.get("service_area", ""):
                self.area_combo.setCurrentIndex(i)
                break
        for i in range(self.rescue_combo.count()):
            if self.rescue_combo.itemText(i) == m.get("rescue_point", ""):
                self.rescue_combo.setCurrentIndex(i)
                break
        self.note_edit.setText(m.get("note", ""))

    def _on_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请输入物资名称")
            return
        self.result_data = {
            "name": self.name_edit.text().strip(),
            "priority": PRIORITY_MAP[self.priority_combo.currentText()],
            "priority_text": self.priority_combo.currentText(),
            "weight": self.weight_spin.value(),
            "quantity": self.quantity_spin.value(),
            "service_area": self.area_combo.currentText(),
            "rescue_point": self.rescue_combo.currentText(),
            "note": self.note_edit.text().strip(),
        }
        self.accept()


class MaterialPage(QWidget):
    """物资管理页面"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.materials = load_json(MATERIALS_FILE, [])
        self.service_areas = load_json(SERVICE_AREAS_FILE, DEFAULT_SERVICE_AREAS)
        self.rescue_points = load_json(RESCUE_POINTS_FILE, DEFAULT_RESCUE_POINTS)
        self._build_ui()
        self._refresh_table()

    def reload_data(self):
        self.service_areas = load_json(SERVICE_AREAS_FILE, DEFAULT_SERVICE_AREAS)
        self.rescue_points = load_json(RESCUE_POINTS_FILE, DEFAULT_RESCUE_POINTS)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        header = QHBoxLayout()
        self.title_label = QLabel("📦 物资管理")
        self.title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        self.title_label.setStyleSheet(f"color: {TEXT_MAIN}; background: transparent;")
        header.addWidget(self.title_label)
        header.addStretch()
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet(f"color: {TEXT_SUB}; background: transparent;")
        header.addWidget(self.stats_label)
        layout.addLayout(header)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        add_btn = QPushButton("➕ 添加物资")
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

        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 搜索物资名称...")
        self.search_edit.textChanged.connect(self._on_filter)
        search_row.addWidget(self.search_edit)
        self.pri_filter = QComboBox()
        self.pri_filter.addItem("全部优先级", -1)
        for k, v in PRIORITY_MAP.items():
            self.pri_filter.addItem(k, v)
        self.pri_filter.currentIndexChanged.connect(self._on_filter)
        search_row.addWidget(self.pri_filter)
        layout.addLayout(search_row)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "物资名称", "优先级", "重量", "数量",
            "初始服务区", "配送救援点", "备注"
        ])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 6):
            h.setSectionResizeMode(i, QHeaderView.ResizeToContents)
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
        f_title = max(14, int(18 * scale))
        f_stats = max(11, int(14 * scale))
        f_table = max(11, int(14 * scale))
        self.title_label.setFont(QFont("Microsoft YaHei", f_title, QFont.Bold))
        self.stats_label.setStyleSheet(f"color: {TEXT_SUB}; background: transparent; font-size: {f_stats}px;")
        self.table.setStyleSheet(f"font-size: {f_table}px;")

    def _refresh_table(self, items=None):
        if items is None:
            items = self.materials
        self.table.setRowCount(len(items))
        for i, m in enumerate(items):
            name_item = QTableWidgetItem(m.get("name", ""))
            name_item.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
            self.table.setItem(i, 0, name_item)

            pri = m.get("priority", 2)
            pri_item = QTableWidgetItem(m.get("priority_text", f"P{pri}"))
            pri_item.setTextAlignment(Qt.AlignCenter)
            pri_item.setForeground(hc(PRIORITY_COLORS.get(pri, TEXT_SUB)))
            pri_item.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
            self.table.setItem(i, 1, pri_item)

            w_item = QTableWidgetItem(f"{m.get('weight', 0):.1f} kg")
            w_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 2, w_item)

            q_item = QTableWidgetItem(str(m.get("quantity", 1)))
            q_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 3, q_item)

            area_item = QTableWidgetItem(m.get("service_area", ""))
            area_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 4, area_item)

            rescue_item = QTableWidgetItem(m.get("rescue_point", ""))
            rescue_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 5, rescue_item)

            note_item = QTableWidgetItem(m.get("note", ""))
            self.table.setItem(i, 6, note_item)

        total_w = sum(m.get("weight", 0) * m.get("quantity", 1) for m in self.materials)
        self.stats_label.setText(f"共 {len(self.materials)} 种物资 | 总重量 {total_w:.1f} kg")

    def _on_filter(self):
        kw = self.search_edit.text().strip().lower()
        pri = self.pri_filter.currentData()
        result = []
        for m in self.materials:
            if kw and kw not in m.get("name", "").lower():
                continue
            if pri is not None and pri >= 0 and m.get("priority", 2) != pri:
                continue
            result.append(m)
        self._refresh_table(result)

    def _add(self):
        self.reload_data()
        dlg = MaterialDialog(self, service_areas=self.service_areas, rescue_points=self.rescue_points)
        if dlg.exec_() == QDialog.Accepted and dlg.result_data:
            self.materials.append(dlg.result_data)
            save_json(MATERIALS_FILE, self.materials)
            self._refresh_table()

    def _edit(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选中一行物资")
            return
        self.reload_data()
        dlg = MaterialDialog(self, material=self.materials[row],
                             service_areas=self.service_areas, rescue_points=self.rescue_points)
        if dlg.exec_() == QDialog.Accepted and dlg.result_data:
            self.materials[row] = dlg.result_data
            save_json(MATERIALS_FILE, self.materials)
            self._refresh_table()

    def _delete(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选中一行物资")
            return
        name = self.materials[row].get("name", "")
        if QMessageBox.question(self, "确认", f"删除物资 \"{name}\"？",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.materials.pop(row)
            save_json(MATERIALS_FILE, self.materials)
            self._refresh_table()
