"""
????????? ? ??????
???task_page.py
???????????????? ? ????? ? ???? ? ?? ? ??/???
"""

import os
import importlib.util
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QLineEdit, QComboBox, QDoubleSpinBox, QDialogButtonBox, QMessageBox,
    QAbstractItemView, QTextEdit, QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from config import (
    SCENES, DARK_BG, PANEL_BG, ACCENT, ACCENT_DARK, BORDER,
    TEXT_MAIN, TEXT_SUB, SUCCESS, ERROR, WARNING,
    PRIORITY_MAP, TASKS_FILE, MAPS_FILE, ALGORITHMS_FILE,
    DEFAULT_MAPS, DEFAULT_ALGORITHMS, BASE_DIR
)
from utils import load_json, save_json


TASK_STATUS_LIST = ["待执行", "执行中", "暂停中", "已完成", "已取消"]
TASK_STATUS_COLORS = {
    "待执行": WARNING,
    "执行中": ACCENT,
    "暂停中": TEXT_SUB,
    "已完成": SUCCESS,
    "已取消": ERROR,
}


def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _next_task_id(tasks):
    max_id = 0
    for t in tasks:
        try:
            max_id = max(max_id, int(t.get("id", 0)))
        except Exception:
            pass
    return max_id + 1


class TaskEditDialog(QDialog):
    def __init__(self, parent=None, task=None, drones=None, service_areas=None, rescue_points=None):
        super().__init__(parent)
        self.setWindowTitle("新建任务" if not task else "编辑任务")
        self.setMinimumWidth(680)
        self.task = task
        self.drones = drones or []
        self.service_areas = service_areas or []
        self.rescue_points = rescue_points or []
        self.result_data = None
        self._build_ui()
        if task:
            self._load(task)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(22, 22, 22, 22)

        title = QLabel("🧰 新建任务" if not self.task else "🧰 编辑任务")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT_MAIN}; background: transparent;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：P0紧急投送-医院通道")
        self.name_edit.setMinimumHeight(38)
        form.addRow("任务名称：", self.name_edit)

        self.priority_combo = QComboBox()
        self.priority_combo.addItems(PRIORITY_MAP.keys())
        self.priority_combo.setMinimumHeight(38)
        form.addRow("任务优先级：", self.priority_combo)

        self.drone_combo = QComboBox()
        for d in self.drones:
            self.drone_combo.addItem(d.get("name", ""), d)
        self.drone_combo.setMinimumHeight(38)
        form.addRow("执行无人机：", self.drone_combo)

        self.start_combo = QComboBox()
        for a in self.service_areas:
            self.start_combo.addItem(a.get("name", ""), a)
        self.start_combo.setMinimumHeight(38)
        form.addRow("起点（服务区）：", self.start_combo)

        self.end_combo = QComboBox()
        for r in self.rescue_points:
            self.end_combo.addItem(r.get("name", ""), r)
        self.end_combo.setMinimumHeight(38)
        form.addRow("终点（救援点）：", self.end_combo)

        self.weight_spin = QDoubleSpinBox()
        self.weight_spin.setRange(0.1, 500.0)
        self.weight_spin.setDecimals(1)
        self.weight_spin.setValue(1.0)
        self.weight_spin.setMinimumHeight(38)
        self.weight_spin.setSuffix(" kg")
        form.addRow("物资重量：", self.weight_spin)

        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("可选，填写特殊要求")
        self.note_edit.setMinimumHeight(38)
        form.addRow("备注：", self.note_edit)

        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("確 認")
        btns.button(QDialogButtonBox.Cancel).setText("取 消")
        btns.button(QDialogButtonBox.Ok).setObjectName("primary")
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _load(self, t):
        self.name_edit.setText(t.get("name", ""))
        idx = self.priority_combo.findText(t.get("priority_text", "高(P1)"))
        if idx >= 0:
            self.priority_combo.setCurrentIndex(idx)
        for i, d in enumerate(self.drones):
            if d.get("name") == t.get("drone_name"):
                self.drone_combo.setCurrentIndex(i)
                break
        for i, a in enumerate(self.service_areas):
            if a.get("name") == t.get("start_name"):
                self.start_combo.setCurrentIndex(i)
                break
        for i, r in enumerate(self.rescue_points):
            if r.get("name") == t.get("end_name"):
                self.end_combo.setCurrentIndex(i)
                break
        self.weight_spin.setValue(float(t.get("weight", 1.0)))
        self.note_edit.setText(t.get("note", ""))

    def _on_accept(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入任务名称")
            return
        if self.start_combo.currentData() is None or self.end_combo.currentData() is None:
            QMessageBox.warning(self, "提示", "请先配置起点/终点数据")
            return
        priority_text = self.priority_combo.currentText()
        self.result_data = {
            "name": name,
            "priority": PRIORITY_MAP.get(priority_text, 2),
            "priority_text": priority_text,
            "drone_id": self.drone_combo.currentData().get("id") if self.drone_combo.currentData() else None,
            "drone_name": self.drone_combo.currentText(),
            "start_name": self.start_combo.currentText(),
            "end_name": self.end_combo.currentText(),
            "weight": float(self.weight_spin.value()),
            "note": self.note_edit.text().strip(),
        }
        self.accept()


class TaskPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_tasks = load_json(TASKS_FILE, [])
        self.maps = load_json(MAPS_FILE, DEFAULT_MAPS)
        self.algorithms = load_json(ALGORITHMS_FILE, DEFAULT_ALGORITHMS)
        self._build_ui()
        self._on_scene_changed(self.scene_combo.currentText())

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        header = QHBoxLayout()
        self.title_label = QLabel("📋 任务管理")
        self.title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        self.title_label.setStyleSheet(f"color: {TEXT_MAIN}; background: transparent;")
        header.addWidget(self.title_label)

        self.scene_combo = QComboBox()
        self.scene_combo.addItems(SCENES)
        self.scene_combo.setMinimumHeight(34)
        self.scene_combo.setMaximumWidth(180)
        self.scene_combo.currentTextChanged.connect(self._on_scene_changed)
        header.addWidget(QLabel("场景:"))
        header.addWidget(self.scene_combo)

        header.addStretch()
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet(f"color: {TEXT_SUB}; font-size: 14px; background: transparent;")
        header.addWidget(self.stats_label)
        layout.addLayout(header)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        add_btn = QPushButton("➕ 新建任务")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._add_task)
        btn_row.addWidget(add_btn)
        edit_btn = QPushButton("✏️ 编辑任务")
        edit_btn.clicked.connect(self._edit_task)
        btn_row.addWidget(edit_btn)
        del_btn = QPushButton("🗑️ 删除任务")
        del_btn.setObjectName("danger")
        del_btn.clicked.connect(self._delete_task)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()

        route_btn = QPushButton("🗺️ 生成路径")
        route_btn.clicked.connect(self._generate_route)
        btn_row.addWidget(route_btn)
        compare_btn = QPushButton("📊 算法对比")
        compare_btn.clicked.connect(self._compare_route)
        btn_row.addWidget(compare_btn)
        start_btn = QPushButton("🚀 开始执行")
        start_btn.clicked.connect(self._start_task)
        btn_row.addWidget(start_btn)
        pause_btn = QPushButton("⏸ 暂停任务")
        pause_btn.clicked.connect(self._pause_task)
        btn_row.addWidget(pause_btn)
        complete_btn = QPushButton("✅ 完成任务")
        complete_btn.setObjectName("primary")
        complete_btn.clicked.connect(self._complete_task)
        btn_row.addWidget(complete_btn)
        cancel_btn = QPushButton("⛔ 取消任务")
        cancel_btn.setObjectName("danger")
        cancel_btn.clicked.connect(self._cancel_task)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "任务ID", "任务名称", "优先级", "状态", "执行无人机",
            "起点", "终点", "预计时间(min)", "创建时间"
        ])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        for i in range(2, 9):
            h.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.currentItemChanged.connect(self._refresh_log_panel)
        layout.addWidget(self.table, stretch=3)

        log_group = QGroupBox("任务日志")
        lg = QVBoxLayout(log_group)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet(
            f"background-color: {PANEL_BG}; color: {TEXT_MAIN}; border: 1.5px solid {BORDER}; border-radius: 10px; padding: 8px;"
        )
        lg.addWidget(self.log_view)
        layout.addWidget(log_group, stretch=2)

    def reload_config(self):
        self.maps = load_json(MAPS_FILE, DEFAULT_MAPS)
        self.algorithms = load_json(ALGORITHMS_FILE, DEFAULT_ALGORITHMS)
        self.all_tasks = load_json(TASKS_FILE, [])
        self._on_scene_changed(self.scene_combo.currentText())

    def _selected_task(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        id_item = self.table.item(row, 0)
        if not id_item:
            return None
        task_id = int(id_item.text())
        for t in self.tasks:
            if int(t.get("id", -1)) == task_id:
                return t
        return None

    def _save(self):
        save_json(TASKS_FILE, self.all_tasks)


    def _on_scene_changed(self, scene):
        if scene == "全部场景":
            self.tasks = self.all_tasks[:]
        else:
            self.tasks = [t for t in self.all_tasks if t.get("scene", "") == scene]
        self._refresh_table()

    def _current_scene(self):
        scene = self.scene_combo.currentText()
        return scene if scene != "全部场景" else "城市地震场景"

    def _refresh_table(self):
        self.table.setRowCount(len(self.tasks))
        for i, t in enumerate(self.tasks):
            self.table.setItem(i, 0, self._center_item(str(t.get("id", ""))))
            name_item = QTableWidgetItem(t.get("name", ""))
            name_item.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
            self.table.setItem(i, 1, name_item)
            self.table.setItem(i, 2, self._center_item(t.get("priority_text", "")))

            status = t.get("status", "待执行")
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
            status_item.setForeground(self._status_color(status))
            self.table.setItem(i, 3, status_item)

            self.table.setItem(i, 4, self._center_item(t.get("drone_name", "")))
            self.table.setItem(i, 5, self._center_item(t.get("start_name", "")))
            self.table.setItem(i, 6, self._center_item(t.get("end_name", "")))

            eta = t.get("route", {}).get("total_time") if t.get("route") else None
            eta_text = f"{float(eta)/60:.1f}" if eta is not None else "-"
            self.table.setItem(i, 7, self._center_item(eta_text))
            self.table.setItem(i, 8, self._center_item(t.get("created_at", "")))

        stats = {"待执行": 0, "执行中": 0, "暂停中": 0, "已完成": 0, "已取消": 0}
        for t in self.tasks:
            s = t.get("status", "待执行")
            if s in stats:
                stats[s] += 1
        self.stats_label.setText(
            f"任务总数：{len(self.all_tasks)}（当前场景：{len(self.tasks)}） ｜ "
            f"待执行：{stats['待执行']} ｜ "
            f"执行中：{stats['执行中']} ｜ "
            f"已完成：{stats['已完成']}"
        )
        self._refresh_log_panel()

    def _refresh_log_panel(self):
        t = self._selected_task()
        if not t:
            self.log_view.setPlainText("")
            return
        logs = t.get("logs", [])
        lines = []
        for lg in logs[-200:]:
            lines.append(f"[{lg.get('time', '')}] {lg.get('user', '系统')}：{lg.get('action', '')}（{lg.get('detail', '')}）")
        self.log_view.setPlainText("\n".join(lines))

    def _append_log(self, task, action, detail=""):
        logs = task.setdefault("logs", [])
        logs.append({
            "time": _now_str(),
            "user": "当前用户",
            "action": action,
            "detail": detail,
        })

    def _status_color(self, status):
        from utils import hc
        return hc(TASK_STATUS_COLORS.get(status, TEXT_SUB))

    def _center_item(self, text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        return item

    def _get_drones(self):
        from config import DRONES_FILE
        data = load_json(DRONES_FILE, {"count": 3, "drones": []})
        return data.get("drones", [])

    def _get_service_areas(self):
        from config import SERVICE_AREAS_FILE, DEFAULT_SERVICE_AREAS
        return load_json(SERVICE_AREAS_FILE, DEFAULT_SERVICE_AREAS)

    def _get_rescue_points(self):
        from config import RESCUE_POINTS_FILE, DEFAULT_RESCUE_POINTS
        return load_json(RESCUE_POINTS_FILE, DEFAULT_RESCUE_POINTS)

    def _load_module(self, file_name, class_name):
        path = os.path.join(BASE_DIR, file_name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"找不到模块文件：{path}")
        spec = importlib.util.spec_from_file_location(file_name.replace(".py", ""), path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls = getattr(module, class_name, None)
        if cls is None:
            raise AttributeError(f"模块中未找到 {class_name}：{file_name}")
        return cls()

    def _add_task(self):
        drones = self._get_drones()
        service_areas = self._get_service_areas()
        rescue_points = self._get_rescue_points()
        dlg = TaskEditDialog(self, drones=drones, service_areas=service_areas, rescue_points=rescue_points)
        if dlg.exec_() == QDialog.Accepted and dlg.result_data:
            data = dlg.result_data
            task = {
                "id": _next_task_id(self.tasks),
                "name": data["name"],
                "priority": data["priority"],
                "priority_text": data["priority_text"],
                "status": "待执行",
                "drone_id": data.get("drone_id"),
                "drone_name": data.get("drone_name", ""),
                "start_name": data.get("start_name", ""),
                "end_name": data.get("end_name", ""),
                "weight": float(data.get("weight", 1.0)),
                "note": data.get("note", ""),
                "scene": self._current_scene(),
                "created_at": _now_str(),
                "completed_at": None,
                "route": None,
                "logs": [],
            }
            self._append_log(task, "创建任务", f"创建任务《{task['name']}》")
            self.all_tasks.append(task)
            self._save()
            self._on_scene_changed(self.scene_combo.currentText())

    def _edit_task(self):
        task = self._selected_task()
        if not task:
            QMessageBox.information(self, "提示", "请先选择一条任务")
            return
        drones = self._get_drones()
        service_areas = self._get_service_areas()
        rescue_points = self._get_rescue_points()
        dlg = TaskEditDialog(self, task=task, drones=drones, service_areas=service_areas, rescue_points=rescue_points)
        if dlg.exec_() == QDialog.Accepted and dlg.result_data:
            data = dlg.result_data
            task.update({
                "name": data["name"],
                "priority": data["priority"],
                "priority_text": data["priority_text"],
                "drone_id": data.get("drone_id"),
                "drone_name": data.get("drone_name", ""),
                "start_name": data.get("start_name", ""),
                "end_name": data.get("end_name", ""),
                "weight": float(data.get("weight", 1.0)),
                "note": data.get("note", ""),
            })
            self._append_log(task, "修改任务", "修改任务配置")
            self._save()
            self._on_scene_changed(self.scene_combo.currentText())

    def _delete_task(self):
        task = self._selected_task()
        if not task:
            QMessageBox.information(self, "提示", "请先选择一条任务")
            return
        if QMessageBox.question(self, "确认", f"删除任务《{task.get('name', '')}》？", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.all_tasks = [t for t in self.all_tasks if int(t.get("id", -1)) != int(task.get("id", -2))]
            self._save()
            self._on_scene_changed(self.scene_combo.currentText())

    def _start_task(self):
        task = self._selected_task()
        if not task:
            QMessageBox.information(self, "提示", "请先选择一条任务")
            return
        if not task.get("route"):
            QMessageBox.warning(self, "提示", "请先生成路径后再开始执行")
            return
        task["status"] = "执行中"
        self._append_log(task, "开始执行", "任务进入执行状态")
        self._save()
        self._on_scene_changed(self.scene_combo.currentText())

    def _pause_task(self):
        task = self._selected_task()
        if not task:
            return
        if task.get("status") != "执行中":
            QMessageBox.information(self, "提示", "当前状态不支持暂停")
            return
        task["status"] = "暂停中"
        self._append_log(task, "暂停任务", "任务已暂停")
        self._save()
        self._on_scene_changed(self.scene_combo.currentText())

    def _complete_task(self):
        task = self._selected_task()
        if not task:
            return
        if task.get("status") in ["已完成", "已取消"]:
            QMessageBox.information(self, "提示", "任务已结束")
            return
        task["status"] = "已完成"
        task["completed_at"] = _now_str()
        self._append_log(task, "完成任务", "任务执行完成并归档")
        self._save()
        self._on_scene_changed(self.scene_combo.currentText())

    def _cancel_task(self):
        task = self._selected_task()
        if not task:
            return
        if task.get("status") in ["已完成", "已取消"]:
            QMessageBox.information(self, "提示", "任务已结束")
            return
        if QMessageBox.question(self, "确认", "确认取消该任务？", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        task["status"] = "已取消"
        self._append_log(task, "取消任务", "任务被取消")
        self._save()
        self._on_scene_changed(self.scene_combo.currentText())

    def _generate_route(self):
        task = self._selected_task()
        if not task:
            QMessageBox.information(self, "提示", "请先选择一条任务")
            return
        if task.get("status") in ["已完成", "已取消"]:
            QMessageBox.information(self, "提示", "已结束任务无需生成路径")
            return
        if not task.get("drone_name"):
            QMessageBox.warning(self, "提示", "请先配置执行无人机")
            return

        drones = self._get_drones()
        materials = [{"name": "任务物资", "weight": float(task.get("weight", 1.0)), "rescue_point": task.get("end_name", "")}]
        service_areas = self._get_service_areas()
        rescue_points = self._get_rescue_points()

        drone_obj = None
        for d in drones:
            if d.get("name") == task.get("drone_name"):
                drone_obj = d
                break
        if not drone_obj:
            QMessageBox.warning(self, "提示", "未找到匹配的执行无人机")
            return

        maps = self.maps
        algorithms = self.algorithms
        if not maps or not algorithms:
            QMessageBox.warning(self, "提示", "缺少场景或算法配置")
            return

        try:
            map_obj = self._load_module(maps[0].get("file"), "Map")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"路径模块加载失败：{e}")
            return

        all_results = []
        default_result = None
        for algo_cfg in algorithms:
            try:
                algo_obj = self._load_module(algo_cfg.get("file"), "Algorithm")
                result = algo_obj.solve([drone_obj], materials, service_areas, rescue_points, map_obj)
                entry = {
                    "algo_name": getattr(algo_obj, "name", algo_cfg.get("name", "")),
                    "total_time": result.get("total_time", 0),
                    "total_distance": result.get("total_distance", 0),
                    "success_rate": result.get("success_rate", 0),
                    "message": result.get("message", ""),
                    "trajectories": result.get("trajectories", []),
                }
                all_results.append(entry)
                if default_result is None:
                    default_result = entry
            except Exception as e:
                all_results.append({
                    "algo_name": algo_cfg.get("name", ""),
                    "error": str(e),
                    "total_time": 0,
                    "total_distance": 0,
                    "success_rate": 0,
                    "message": f"算法执行失败：{e}",
                    "trajectories": [],
                })

        if not default_result:
            QMessageBox.critical(self, "错误", "没有算法可生成路径")
            return

        task["route"] = {
            "map_name": getattr(map_obj, "name", maps[0].get("name", "")),
            "algo_name": default_result["algo_name"],
            "trajectories": default_result.get("trajectories", []),
            "total_time": default_result.get("total_time", 0),
            "total_distance": default_result.get("total_distance", 0),
            "success_rate": default_result.get("success_rate", 0),
            "message": default_result.get("message", ""),
            "generated_at": _now_str(),
            "all_results": all_results,
        }
        self._append_log(task, "生成路径", f"使用算法《{default_result['algo_name']}》生成路径")
        self._save()
        self._on_scene_changed(self.scene_combo.currentText())
        QMessageBox.information(self, "完成", f"路径已生成\n预计时间：{float(task['route']['total_time'])/60:.1f} 分钟")

    def _compare_route(self):
        task = self._selected_task()
        if not task:
            QMessageBox.information(self, "提示", "请先选择一条任务")
            return
        route = task.get("route") or {}
        all_results = route.get("all_results") or []
        if not all_results:
            QMessageBox.information(self, "提示", "请先生成路径后再进行算法对比")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("算法对比")
        dlg.setMinimumSize(760, 420)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(16, 16, 16, 16)

        title = QLabel("📊 路径算法对比")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT_MAIN}; background: transparent;")
        lay.addWidget(title)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["算法", "预计时间(min)", "路径长度(m)", "成功率", "备注"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, 5):
            table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setAlternatingRowColors(True)
        table.setRowCount(len(all_results))
        for i, r in enumerate(all_results):
            table.setItem(i, 0, QTableWidgetItem(str(r.get("algo_name", ""))))
            time_item = QTableWidgetItem(f"{float(r.get('total_time', 0))/60:.1f}")
            time_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 1, time_item)
            dist_item = QTableWidgetItem(f"{float(r.get('total_distance', 0)):.1f}")
            dist_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 2, dist_item)
            rate_item = QTableWidgetItem(f"{float(r.get('success_rate', 0))*100:.1f}%")
            rate_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 3, rate_item)
            note = r.get("message") or r.get("error") or ""
            table.setItem(i, 4, QTableWidgetItem(note))
        lay.addWidget(table)

        btns = QDialogButtonBox(QDialogButtonBox.Ok)
        btns.button(QDialogButtonBox.Ok).setText("关闭")
        btns.accepted.connect(dlg.accept)
        lay.addWidget(btns)

        dlg.exec_()







