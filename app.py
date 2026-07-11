"""
应急无人机调度系统 — 主控台
文件：app.py
说明：主窗口，整合所有页面，左侧可折叠导航栏，右侧内容区
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from config import (
    DARK_BG, ACCENT, BORDER, TEXT_MAIN, TEXT_SUB,
    SIDEBAR_BG, SIDEBAR_HOVER, SIDEBAR_ACTIVE, GLOBAL_STYLE
)
from material_page import MaterialPage
from area_page import ServiceAreaPage
from rescue_page import RescuePointPage
from drone_page import DronePage
from dispatch_page import DispatchPage
from task_page import TaskPage


class MainWindow(QMainWindow):
    def __init__(self, username="管理员"):
        super().__init__()
        self.setWindowTitle("应急无人机调度系统 — 主控台")
        self.resize(1280, 780)
        self.setMinimumSize(960, 600)
        self.setStyleSheet(GLOBAL_STYLE)
        self.username = username
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 左侧导航栏 ──
        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(220)
        sidebar_container.setStyleSheet(f"background-color: {SIDEBAR_BG};")

        sb_lay = QVBoxLayout(sidebar_container)
        sb_lay.setContentsMargins(0, 0, 0, 0)
        sb_lay.setSpacing(0)

        logo = QWidget()
        logo.setStyleSheet(f"background: {SIDEBAR_BG}; border-bottom: 1px solid {BORDER};")
        logo_lay = QVBoxLayout(logo)
        logo_lay.setContentsMargins(16, 22, 16, 18)
        icon = QLabel("✈")
        icon.setFont(QFont("Segoe UI Emoji", 36))
        icon.setStyleSheet(f"color: {ACCENT}; background: transparent;")
        icon.setAlignment(Qt.AlignCenter)
        logo_lay.addWidget(icon)
        logo_title = QLabel("应急无人机调度")
        logo_title.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        logo_title.setStyleSheet(f"color: {TEXT_MAIN}; background: transparent;")
        logo_title.setAlignment(Qt.AlignCenter)
        logo_lay.addWidget(logo_title)
        logo_sub = QLabel("v2.1")
        logo_sub.setFont(QFont("Segoe UI", 10))
        logo_sub.setStyleSheet(f"color: {TEXT_SUB}; background: transparent;")
        logo_sub.setAlignment(Qt.AlignCenter)
        logo_lay.addWidget(logo_sub)
        sb_lay.addWidget(logo)

        self.nav_buttons = []
        nav_items = [
            ("📦", "物资管理"),
            ("🏗", "服务区管理"),
            ("🎯", "救援点管理"),
            ("🤖", "无人机管理"),
            ("🚀", "救援调度"),
            ("🧍", "任务管理"),
]
        for icon_txt, text in nav_items:
            btn = QPushButton(f"  {icon_txt}  {text}")
            btn.setObjectName("sidebar")
            btn.setCheckable(True)
            btn.setMinimumHeight(50)
            btn.clicked.connect(lambda _, b=btn: self._on_nav(b))
            sb_lay.addWidget(btn)
            self.nav_buttons.append(btn)

        sb_lay.addStretch()

        user_area = QWidget()
        user_area.setStyleSheet(f"background: {SIDEBAR_BG}; border-top: 1px solid {BORDER};")
        user_lay = QVBoxLayout(user_area)
        user_lay.setContentsMargins(16, 14, 16, 14)
        user_label = QLabel(f"👤 {self.username}")
        user_label.setFont(QFont("Microsoft YaHei", 13))
        user_label.setStyleSheet(f"color: {TEXT_SUB}; background: transparent;")
        user_label.setAlignment(Qt.AlignCenter)
        user_lay.addWidget(user_label)
        sb_lay.addWidget(user_area)

        root.addWidget(sidebar_container)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(f"color: {BORDER};")
        root.addWidget(sep)

        # ── 右侧内容区 ──
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background: {DARK_BG};")

        self.material_page = MaterialPage()
        self.area_page = ServiceAreaPage()
        self.rescue_page = RescuePointPage()
        self.drone_page = DronePage()
        self.task_page = TaskPage()
        self.dispatch_page = DispatchPage(
            get_drones_func=lambda: self.drone_page.get_drones()
        )

        self.stack.addWidget(self.material_page)
        self.stack.addWidget(self.area_page)
        self.stack.addWidget(self.rescue_page)
        self.stack.addWidget(self.drone_page)
        self.stack.addWidget(self.dispatch_page)
        self.stack.addWidget(self.task_page)

        root.addWidget(self.stack, stretch=1)

        self.nav_buttons[0].setChecked(True)
        self.stack.setCurrentIndex(0)

    def _on_nav(self, clicked):
        for i, btn in enumerate(self.nav_buttons):
            if btn is clicked:
                btn.setChecked(True)
                self.stack.setCurrentIndex(i)
                if i == 0:
                    self.material_page.reload_data()
                if i == 4:
                    self.dispatch_page.reload_config()
                if i == 5:
                    self.task_page.reload_config()
            else:
                btn.setChecked(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

