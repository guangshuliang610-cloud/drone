"""
应急无人机调度系统 — 救援点管理页面
文件：rescue_page.py
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QDoubleSpinBox, QComboBox, QDialog, QFormLayout,
    QDialogButtonBox, QMessageBox, QAbstractItemView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from config import (
    PRIORITY_MAP, PRIORITY_COLORS, TEXT_MAIN, TEXT_SUB, ACCENT,
    RESCUE_POINTS_FILE, DEFAULT_RESCUE_POINTS
)
from utils import load_json, save_json, hc


class RescuePointEditDialog(QDialog):
    """救援点编辑对话框"""
    def __init__(self, parent=None, point=None):
        super().__init__(parent)
        self.setWindowTitle("编辑救援点" if point else "添加救援点")
        self.setMinimumWidth(480)
        self.point = point
        self.result_data = None
        self._build_ui()
        if point:
            self._load(point)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(28, 28, 28, 28)

        title = QLabel("🎯 编辑救援点" if self.point else "🎯 添加救援点")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT_MAIN}; background: transparent;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(16)
        form.setLabelAlignment(Qt.AlignRight)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例：灾区A - 居民区、中心医院...")
        self.name_edit.setMinimumHeight(40)
        form.addRow("救援点名称：", self.name_edit)

        coord_widget = QWidget()
        cl = QHBoxLayout(coord_widget)
        cl.setSpacing(12)
        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(-99999, 99999)
        self.x_spin.setDecimals(1)
        self.x_spin.setPrefix("X: ")
        self.x_spin.setMinimumHeight(40)
        cl.addWidget(self.x_spin)
        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(-99999, 99999)
        self.y_spin.setDecimals(1)
        self.y_spin.setPrefix("Y: ")
        self.y_spin.setMinimumHeight(40)
        cl.addWidget(self.y_spin)
        self.z_spin = QDoubleSpinBox()
        self.z_spin.setRange(-99999, 99999)
        self.z_spin.setDecimals(1)
        self.z_spin.setPrefix("Z: ")
        self.z_spin.setMinimumHeight(40)
        cl.addWidget(self.z_spin)
        form.addRow("三维坐标：", coord_widget)

        self.priority_combo = QComboBox()
        self.priority_combo.addItems(PRIORITY_MAP.keys())
        self.priority_combo.setMinimumHeight(40)
        form.addRow("配送优先级：", self.priority_combo)

        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("可选，填写特殊情况...")
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

    def _load(self, p):
        self.name_edit.setText(p.get("name", ""))
        self.x_spin.setValue(p.get("x", 0))
        self.y_spin.setValue(p.get("y", 0))
        self.z_spin.setValue(p.get("z", 0))
        idx = self.priority_combo.findText(p.get("priority_text", "中 (P2)"))
        if idx >= 0:
            self.priority_combo.setCurrentIndex(idx)
        self.note_edit.setText(p.get("note", ""))

    def _on_ok(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请输入救援点名称")
            return
        self.result_data = {
            "name": self.name_edit.text().strip(),
            "x": self.x_spin.value(),
            "y": self.y_spin.value(),
            "z": self.z_spin.value(),
            "priority": PRIORITY_MAP[self.priority_combo.currentText()],
            "priority_text": self.priority_combo.currentText(),
            "note": self.note_edit.text().strip(),
        }
        self.accept()


class RescuePointPage(QWidget):
    """救援点管理页面"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.points = load_json(RESCUE_POINTS_FILE, DEFAULT_RESCUE_POINTS)
        self._build_ui()
        self._refresh_table()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        header = QHBoxLayout()
        self.title_label = QLabel("🎯 救援点管理")
        self.title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        self.title_label.setStyleSheet(f"color: {TEXT_MAIN}; background: transparent;")
        header.addWidget(self.title_label)
        header.addStretch()
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
        del_btn = QPushButton("🗑 删除")
        del_btn.setObjectName("danger")
        del_btn.clicked.connect(self._delete)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "救援点名称", "X 坐标", "Y 坐标", "Z 坐标", "配送优先级", "备注"
        ])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 4):
            h.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.Stretch)
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

            note_item = QTableWidgetItem(p.get("note", ""))
            self.table.setItem(i, 5, note_item)

        self.stats_label.setText(f"共 {len(self.points)} 个救援点")

    def _add(self):
        dlg = RescuePointEditDialog(self)
        if dlg.exec_() == QDialog.Accepted and dlg.result_data:
            self.points.append(dlg.result_data)
            save_json(RESCUE_POINTS_FILE, self.points)
            self._refresh_table()

    def _edit(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选中一个救援点")
            return
        dlg = RescuePointEditDialog(self, point=self.points[row])
        if dlg.exec_() == QDialog.Accepted and dlg.result_data:
            self.points[row] = dlg.result_data
            save_json(RESCUE_POINTS_FILE, self.points)
            self._refresh_table()

    def _delete(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选中一个救援点")
            return
        name = self.points[row].get("name", "")
        if QMessageBox.question(self, "确认", f"删除救援点 \"{name}\"？",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.points.pop(row)
            save_json(RESCUE_POINTS_FILE, self.points)
            self._refresh_table()
