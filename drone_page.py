"""
应急无人机调度系统 — 无人机管理页面
文件：drone_page.py
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QSpinBox, QDialog, QFormLayout, QDialogButtonBox,
    QMessageBox, QGroupBox, QAbstractItemView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from config import (
    TEXT_MAIN, TEXT_SUB, ACCENT, SUCCESS, ERROR, WARNING, WHITE,
    BORDER, PANEL_BG, INPUT_BG,
    DRONES_FILE, DEFAULT_SERVICE_AREAS
)
from utils import load_json, save_json, hc


class DronePage(QWidget):
    """无人机管理页面"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.drones_data = load_json(DRONES_FILE, {"count": 3, "drones": []})
        self._ensure_drones()
        self._sa_combos = []
        self._build_ui()
        self._refresh_table()

    def _ensure_drones(self):
        count = self.drones_data.get("count", 3)
        drones = self.drones_data.get("drones", [])
        while len(drones) < count:
            idx = len(drones)
            drones.append({
                "id": idx + 1,
                "name": "无人机%02d" % (idx + 1),
                "model": "DJI M30T",
                "max_payload": 5.0,
                "max_range": 15.0,
                "max_speed": 60.0,
                "battery": 100,
                "status": "待命",
                "m_body": 10.0,
                "U_bat": 64.8,
                "C_bat_Ah": 30.0,
                "service_area": "",
            })
        self.drones_data["drones"] = drones[:count]
        self.drones_data["count"] = count

    def get_drones(self):
        """供外部（调度页面）读取当前无人机列表"""
        return self.drones_data.get("drones", [])

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        header = QHBoxLayout()
        header.setSpacing(8)
        title_wrap = QVBoxLayout()
        title_wrap.setSpacing(4)
        self.title_label = QLabel("🤖 无人机管理")
        self.title_label.setFont(QFont("Microsoft YaHei", 20, QFont.Bold))
        self.title_label.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {WHITE}; background: transparent;")
        title_wrap.addWidget(self.title_label)
        self.subtitle_label = QLabel("管理无人机编队数量、型号与状态")
        self.subtitle_label.setFont(QFont("Microsoft YaHei", 12))
        self.subtitle_label.setStyleSheet(f"color: {TEXT_SUB}; background: transparent;")
        title_wrap.addWidget(self.subtitle_label)
        header.addLayout(title_wrap)
        header.addStretch()
        self.count_label = QLabel("")
        self.count_label.setStyleSheet(f"font-size: 12px; color: {TEXT_SUB}; background: transparent;")
        header.addWidget(self.count_label)
        layout.addLayout(header)

        count_group = QGroupBox("无人机编队设置")
        cg = QHBoxLayout(count_group)
        cg.setSpacing(16)
        cg.addWidget(QLabel("无人机数量："))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 100)
        self.count_spin.setValue(self.drones_data.get("count", 3))
        self.count_spin.setMinimumHeight(36)
        self.count_spin.setMinimumWidth(120)
        cg.addWidget(self.count_spin)
        apply_btn = QPushButton("✔ 应用数量")
        apply_btn.setObjectName("primary")
        apply_btn.clicked.connect(self._apply_count)
        cg.addWidget(apply_btn)
        cg.addStretch()
        cg.addWidget(QLabel("批量状态："))
        self.batch_combo = QComboBox()
        self.batch_combo.addItems(["待命", "执行中", "充电中", "维修中", "离线"])
        self.batch_combo.setMinimumHeight(36)
        cg.addWidget(self.batch_combo)
        batch_btn = QPushButton("全部应用")
        batch_btn.clicked.connect(self._batch_status)
        cg.addWidget(batch_btn)
        layout.addWidget(count_group)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        save_btn = QPushButton("💾 保存配置")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        reset_btn = QPushButton("🔄 重置默认")
        reset_btn.clicked.connect(self._reset)
        btn_row.addWidget(reset_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "编号", "名称", "服务区", "型号", "最大载重(kg)",
            "航程(km)", "最大速度(km/h)", "机身重(kg)",
            "电池(V)", "容量(Ah)", "状态"
        ])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        for i in range(2, 10):
            h.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setShowGrid(False)
        layout.addWidget(self.table, stretch=1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        scale = max(0.7, min(2.0, w / 900))
        self.title_label.setFont(QFont("Microsoft YaHei", max(14, int(18 * scale)), QFont.Bold))

    def _refresh_table(self):
        drones = self.drones_data.get("drones", [])
        self.table.setRowCount(len(drones))
        for i, d in enumerate(drones):
            id_item = QTableWidgetItem(str(d.get("id", i + 1)))
            id_item.setTextAlignment(Qt.AlignCenter)
            id_item.setFont(QFont("Consolas", 14, QFont.Bold))
            self.table.setItem(i, 0, id_item)

            name_item = QTableWidgetItem(d.get("name", "无人机%02d" % (i + 1)))
            name_item.setFont(QFont("Microsoft YaHei", 13))
            self.table.setItem(i, 1, name_item)

            self._sa_combos.append([])
            sa_combo = QComboBox()
            sa_names = [a["name"] for a in DEFAULT_SERVICE_AREAS]
            sa_combo.addItems(["(未分配)"] + sa_names)
            cur_sa = d.get("service_area", "")
            if cur_sa in sa_names:
                sa_combo.setCurrentIndex(sa_names.index(cur_sa) + 1)
            self._sa_combos[-1] = sa_combo
            self.table.setCellWidget(i, 2, sa_combo)

            model_item = QTableWidgetItem(d.get("model", "DJI M30T"))
            model_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 3, model_item)

            for j, key in enumerate(["max_payload", "max_range", "max_speed", "m_body", "U_bat", "C_bat_Ah"]):
                val_item = QTableWidgetItem("%.1f" % d.get(key, 0))
                val_item.setTextAlignment(Qt.AlignCenter)
                val_item.setFont(QFont("Consolas", 14))
                self.table.setItem(i, j + 4, val_item)

            status = d.get("status", "待命")
            st_item = QTableWidgetItem(status)
            st_item.setTextAlignment(Qt.AlignCenter)
            st_item.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
            sc = {"待命": SUCCESS, "执行中": ACCENT, "充电中": WARNING, "维修中": ERROR, "离线": TEXT_SUB}
            st_item.setForeground(hc(sc.get(status, TEXT_SUB)))
            self.table.setItem(i, 10, st_item)

        self.count_label.setText("共 %d 架无人机" % len(drones))

    def _apply_count(self):
        self.drones_data["count"] = self.count_spin.value()
        self._ensure_drones()
        self._refresh_table()
        save_json(DRONES_FILE, self.drones_data)

    def _batch_status(self):
        s = self.batch_combo.currentText()
        for d in self.drones_data.get("drones", []):
            d["status"] = s
        self._refresh_table()
        save_json(DRONES_FILE, self.drones_data)

    def _save(self):
        drones = self.drones_data.get("drones", [])
        for i in range(min(self.table.rowCount(), len(drones))):
            for col, key in [(1, "name"), (3, "model")]:
                item = self.table.item(i, col)
                if item:
                    drones[i][key] = item.text()
            for col, key in [(4, "max_payload"), (5, "max_range"), (6, "max_speed"), (7, "m_body"), (8, "U_bat"), (9, "C_bat_Ah")]:
                item = self.table.item(i, col)
                if item:
                    try:
                        drones[i][key] = float(item.text())
                    except ValueError:
                        pass
        # Save service_area from combo
        for i in range(min(self.table.rowCount(), len(drones))):
            if i < len(self._sa_combos) and self._sa_combos[i]:
                sa_text = self._sa_combos[i].currentText()
                drones[i]["service_area"] = "" if sa_text.startswith("(未分配") else sa_text

        save_json(DRONES_FILE, self.drones_data)
        QMessageBox.information(self, "保存成功", "无人机配置已保存 ✔")

    def _reset(self):
        if QMessageBox.question(self, "确认", "恢复默认配置？",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.drones_data = {"count": 3, "drones": []}
            self._ensure_drones()
            self.count_spin.setValue(3)
            self._refresh_table()
            save_json(DRONES_FILE, self.drones_data)

