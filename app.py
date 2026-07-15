"""
应急无人机调度系统 — 主控台
文件：app.py
说明：主窗口，现代化侧边栏 + 顶栏布局，右侧内容区 QStackedWidget
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QLineEdit
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from config import (
    DARK_BG, PANEL_BG, ACCENT, ACCENT_DARK, BORDER,
    TEXT_MAIN, TEXT_SUB, INPUT_BG, SIDEBAR_BG,
    SIDEBAR_HOVER, SIDEBAR_ACTIVE, SUCCESS, GLOBAL_STYLE
)
from material_page import MaterialPage
from area_page import ServiceAreaPage
from rescue_page import RescuePointPage
from drone_page import DronePage
from dispatch_page import DispatchPage
from task_page import TaskPage


class NavCaption(QLabel):
    """每组上方的大写灰色小标题"""
    def __init__(self, text: str):
        super().__init__(text)
        self.setFont(QFont("Segoe UI", 8))
        self.setStyleSheet(f"""
            color: {TEXT_SUB};
            background: transparent;
            padding: 12px 22px 4px 22px;
            letter-spacing: 2px;
        """)


class CircleAvatar(QFrame):
    """圆形渐变头像，显示用户名第一个字"""
    def __init__(self, text: str, size: int = 38):
        super().__init__()
        self.setFixedSize(size, size)
        self.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {ACCENT}, stop:1 {ACCENT_DARK});
            border-radius: {size // 2}px;
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(text[0] if text else "U")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont("Microsoft YaHei", size // 3, QFont.Bold))
        lbl.setStyleSheet("color: #FFFFFF; background: transparent;")
        lay.addWidget(lbl)


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

        sidebar = self._build_sidebar()
        root.addWidget(sidebar)

        right_wrap = QFrame()
        right_wrap.setStyleSheet(f"background: {DARK_BG};")
        right_lay = QVBoxLayout(right_wrap)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)

        topbar = self._build_topbar()
        right_lay.addWidget(topbar)

        content_area = self._build_content_area()
        right_lay.addWidget(content_area, stretch=1)

        root.addWidget(right_wrap, stretch=1)

        if self.nav_buttons:
            self.nav_buttons[0].setChecked(True)
            self.stack.setCurrentIndex(0)

    def _build_sidebar(self) -> QWidget:
        sb = QWidget()
        sb.setFixedWidth(230)
        sb.setStyleSheet(f"background-color: {SIDEBAR_BG};")

        lay = QVBoxLayout(sb)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Logo 区 ──
        logo_widget = QWidget()
        logo_widget.setFixedHeight(130)
        logo_widget.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(46,204,113,0.18),
                stop:1 {SIDEBAR_BG});
            border-bottom: 1px solid {BORDER};
        """)
        logo_lay = QVBoxLayout(logo_widget)
        logo_lay.setContentsMargins(16, 18, 16, 14)

        icon_container = QFrame()
        icon_container.setFixedSize(52, 52)
        icon_container.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {ACCENT}, stop:1 {ACCENT_DARK});
            border-radius: 14px;
        """)
        ic_lay = QHBoxLayout(icon_container)
        ic_lay.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel("\u2708")
        icon_lbl.setFont(QFont("Segoe UI Emoji", 22))
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("color: #FFFFFF; background: transparent;")
        ic_lay.addWidget(icon_lbl)

        logo_row = QHBoxLayout()
        logo_row.addStretch()
        logo_row.addWidget(icon_container)
        logo_row.addStretch()
        logo_lay.addLayout(logo_row)

        title = QLabel("应急无人机调度")
        title.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {TEXT_MAIN}; background: transparent;")
        logo_lay.addWidget(title)

        subtitle = QLabel("Drone Dispatch Console")
        subtitle.setFont(QFont("Segoe UI", 8))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(f"color: {TEXT_SUB}; background: transparent;")
        logo_lay.addWidget(subtitle)

        lay.addWidget(logo_widget)

        # ── 导航按钮 ──
        self.nav_buttons = []

        lay.addWidget(NavCaption("MONITOR"))
        self._add_nav(lay, "[\u25c6]",  "调度总览", "overview")
        lay.addWidget(NavCaption("RESOURCE"))
        self._add_nav(lay, "[\u25c6]",  "物资管理", "material")
        self._add_nav(lay, "[\u25c6]",  "服务区管理", "area")
        self._add_nav(lay, "[\u25c6]",  "救援点管理", "rescue")
        self._add_nav(lay, "[\u25c6]",  "无人机管理", "drone")
        lay.addWidget(NavCaption("MISSION"))
        self._add_nav(lay, "[\u25c6]",  "救援调度", "dispatch")
        self._add_nav(lay, "[\u25c6]",  "任务管理", "task")

        lay.addStretch()

        # ── 底部用户区 ──
        user_widget = QWidget()
        user_widget.setFixedHeight(68)
        user_widget.setStyleSheet(f"background: {SIDEBAR_BG}; border-top: 1px solid {BORDER};")
        ul = QHBoxLayout(user_widget)
        ul.setContentsMargins(14, 8, 14, 8)

        avatar = CircleAvatar(self.username, size=38)
        ul.addWidget(avatar)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        lbl_name = QLabel(self.username if self.username else "User")
        lbl_name.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        lbl_name.setStyleSheet(f"color: {TEXT_MAIN}; background: transparent;")
        ul.addLayout(text_col)

        dot = QLabel('\u25cf \u5728\u7ebf')
        dot.setFont(QFont("Microsoft YaHei", 9))
        dot.setStyleSheet(
            f"background: transparent; color: {TEXT_SUB};"
        )
        text_col.addWidget(lbl_name)
        text_col.addWidget(dot)
        ul.addStretch()

        lay.addWidget(user_widget)
        return sb

    def _add_nav(self, parent_lay, icon_text: str, label: str, obj_name: str):
        btn = QPushButton(f"  {icon_text}   {label}")
        btn.setObjectName(obj_name)
        btn.setProperty("navGroup", "sidebar")
        btn.setCheckable(True)
        btn.setMinimumHeight(44)
        btn.setFont(QFont("Microsoft YaHei", 12))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_SUB};
                border: none;
                border-left: 3px solid transparent;
                border-radius: 0;
                padding: 10px 18px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {SIDEBAR_HOVER};
                color: {TEXT_MAIN};
                border-left: 3px solid {BORDER};
            }}
            QPushButton:checked {{
                background-color: {SIDEBAR_ACTIVE};
                color: {ACCENT};
                border-left: 3px solid {ACCENT};
                font-weight: bold;
            }}
        """)
        btn.clicked.connect(lambda _=False, b=btn: self._on_nav(b))
        parent_lay.addWidget(btn)
        self.nav_buttons.append(btn)

    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(62)
        bar.setStyleSheet(f"background: {PANEL_BG}; border-bottom: 1px solid {BORDER};")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(14)

        # 左侧搜索框
        search = QLineEdit()
        search.setPlaceholderText("  \u641c\u7d22\u7269\u8d44 / \u65e0\u4eba\u673a / \u4efb\u52a1 ...")
        search.setFixedWidth(320)
        search.setFixedHeight(36)
        search.setFont(QFont("Microsoft YaHei", 11))
        search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {INPUT_BG};
                color: {TEXT_MAIN};
                border: 1.5px solid {BORDER};
                border-radius: 18px;
                padding: 0 16px;
            }}
            QLineEdit:focus {{
                border: 1.5px solid {ACCENT};
            }}
        """)
        lay.addWidget(search)

        lay.addStretch()

        # 右侧状态标签
        status_lbl = QLabel(
            f'<span style="color:{SUCCESS};">\u25cf</span> \u7cfb\u7edf\u6b63\u5e38'
        )
        status_lbl.setFont(QFont("Microsoft YaHei", 11))
        status_lbl.setStyleSheet(
            f"color: {TEXT_MAIN}; background: transparent;"
        )
        lay.addWidget(status_lbl)

        # 刷新按钮
        btn_refresh = QPushButton("\U0001f504 \u5237\u65b0")
        btn_refresh.setFont(QFont("Segoe UI Emoji", 11))
        btn_refresh.setFixedSize(80, 34)
        btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: {INPUT_BG};
                color: {TEXT_MAIN};
                border: 1px solid {BORDER};
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: {SIDEBAR_HOVER};
                border-color: {ACCENT};
                color: {ACCENT};
            }}
        """)
        btn_refresh.clicked.connect(self._on_refresh)
        lay.addWidget(btn_refresh)

        # 新建调度按钮
        btn_new = QPushButton("\u2795 \u65b0\u5efa\u8c03\u5ea6")
        btn_new.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        btn_new.setFixedSize(130, 34)
        btn_new.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {ACCENT}, stop:1 {ACCENT_DARK});
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #35DA7E, stop:1 {ACCENT});
            }}
            QPushButton:pressed {{
                background: {ACCENT_DARK};
            }}
        """)
        btn_new.clicked.connect(self._on_new_dispatch)
        lay.addWidget(btn_new)

        return bar

    def _build_content_area(self) -> QStackedWidget:
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

        return self.stack

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

    def _on_refresh(self):
        idx = self.stack.currentIndex()
        if idx == 0:
            self.material_page.reload_data()
        elif idx == 4:
            self.dispatch_page.reload_config()
        elif idx == 5:
            self.task_page.reload_config()

    def _on_new_dispatch(self):
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == 4)
        self.stack.setCurrentIndex(4)
        self.dispatch_page.reload_config()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
