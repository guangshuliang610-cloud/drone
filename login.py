"""
应急无人机调度系统 — 登录/注册界面
文件：login.py
说明：入口文件，登录后跳转主控台
"""

import sys
import json
import hashlib
import os
from PyQt5.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QStackedWidget,
    QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from config import (
    DARK_BG, PANEL_BG, ACCENT, ACCENT_DARK, BORDER,
    TEXT_MAIN, TEXT_SUB, INPUT_BG, SUCCESS, ERROR
)

# ── 文件路径 ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")
REMEMBER_FILE = os.path.join(BASE_DIR, "remembered.json")

# 登录页专用
RIGHT_BG = "#141A22"

LOGIN_STYLE = """
QDialog, QWidget {
    background-color: %(DARK_BG)s;
    color: %(TEXT_MAIN)s;
    font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
}
QLineEdit {
    background-color: %(INPUT_BG)s;
    color: %(TEXT_MAIN)s;
    border: 1px solid %(BORDER)s;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}
QLineEdit:focus { border: 1.5px solid %(ACCENT)s; }
QPushButton#primary {
    background-color: %(ACCENT)s;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 10px 0;
    font-size: 14px;
    font-weight: bold;
}
QPushButton#primary:hover { background-color: %(ACCENT_DARK)s; }
QPushButton#primary:pressed { background-color: #1E4F3B; }
QPushButton#tab_btn {
    background-color: transparent;
    color: %(TEXT_SUB)s;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 8px 20px;
    font-size: 14px;
}
QPushButton#tab_btn:checked {
    color: %(TEXT_MAIN)s;
    border-bottom: 2px solid %(ACCENT)s;
    font-weight: bold;
}
QCheckBox {
    color: %(TEXT_SUB)s;
    font-size: 12px;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 14px; height: 14px;
    border-radius: 3px;
    border: 1px solid %(BORDER)s;
    background: %(INPUT_BG)s;
}
QCheckBox::indicator:checked {
    background-color: %(ACCENT)s;
    border-color: %(ACCENT)s;
}
""" % {
    "DARK_BG": DARK_BG, "PANEL_BG": PANEL_BG, "ACCENT": ACCENT,
    "ACCENT_DARK": ACCENT_DARK, "BORDER": BORDER, "TEXT_MAIN": TEXT_MAIN,
    "TEXT_SUB": TEXT_SUB, "INPUT_BG": INPUT_BG, "SUCCESS": SUCCESS, "ERROR": ERROR,
}


# ── 工具函数 ──
def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users(u):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(u, f, ensure_ascii=False, indent=2)

def load_remembered():
    if os.path.exists(REMEMBER_FILE):
        with open(REMEMBER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_remembered(u, p):
    with open(REMEMBER_FILE, "w", encoding="utf-8") as f:
        json.dump({"username": u, "password": p}, f, ensure_ascii=False)

def clear_remembered():
    if os.path.exists(REMEMBER_FILE):
        os.remove(REMEMBER_FILE)


# ── 右侧装饰面板 ──
class RightPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setStyleSheet("background-color: %s;" % RIGHT_BG)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 36, 24, 28)
        lay.setSpacing(0)

        icon = QLabel("\u2708")
        icon.setFont(QFont("Segoe UI Emoji", 34))
        icon.setStyleSheet("color: %s; background: transparent;" % ACCENT)
        icon.setAlignment(Qt.AlignCenter)
        lay.addWidget(icon)

        lay.addSpacing(14)

        title = QLabel("应急无人机\n调度平台")
        title.setFont(QFont("Microsoft YaHei", 15, QFont.Bold))
        title.setStyleSheet("color: %s; background: transparent;" % TEXT_MAIN)
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        lay.addSpacing(8)

        sub = QLabel("v2.1  \u00b7  应急专版")
        sub.setFont(QFont("Segoe UI", 9))
        sub.setStyleSheet("color: %s; background: transparent;" % TEXT_SUB)
        sub.setAlignment(Qt.AlignCenter)
        lay.addWidget(sub)

        lay.addStretch()

        features = ["\u2714 三维地图可视化", "\u2714 多算法路径规划", "\u2714 无人机编队调度", "\u2714 任务实时监控"]
        for feat in features:
            lbl = QLabel(feat)
            lbl.setFont(QFont("Microsoft YaHei", 10))
            lbl.setStyleSheet("color: %s; background: transparent; padding: 3px 0;" % TEXT_SUB)
            lay.addWidget(lbl)

        lay.addStretch()

        footer = QLabel("\u00a9 2026 Emergency UAV")
        footer.setFont(QFont("Segoe UI", 8))
        footer.setStyleSheet("color: %s; background: transparent;" % BORDER)
        footer.setAlignment(Qt.AlignCenter)
        lay.addWidget(footer)


# ── 登录/注册对话框 ──
class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("应急无人机调度系统 \u2014 登录")
        self.setMinimumSize(700, 460)
        self.setStyleSheet(LOGIN_STYLE)
        self._build_ui()
        self._load_remembered()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_scale()

    def _apply_scale(self):
        w = self.width()
        scale = max(0.8, min(1.5, w / 700))
        self.title_lbl.setFont(QFont("Microsoft YaHei", max(16, int(20 * scale)), QFont.Bold))
        self.sub_lbl.setFont(QFont("Microsoft YaHei", max(10, int(12 * scale))))

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(RightPanel(self))

        center = QWidget()
        center.setStyleSheet("background: %s;" % DARK_BG)
        cl = QVBoxLayout(center)
        cl.setContentsMargins(48, 32, 48, 28)
        cl.setSpacing(0)

        self.title_lbl = QLabel("应急无人机调度系统")
        self.title_lbl.setFont(QFont("Microsoft YaHei", 20, QFont.Bold))
        self.title_lbl.setStyleSheet("color: %s; background: transparent;" % TEXT_MAIN)
        self.title_lbl.setAlignment(Qt.AlignCenter)
        cl.addWidget(self.title_lbl)

        cl.addSpacing(4)

        self.sub_lbl = QLabel("Emergency UAV Dispatch System")
        self.sub_lbl.setFont(QFont("Segoe UI", 12))
        self.sub_lbl.setStyleSheet("color: %s; background: transparent;" % TEXT_SUB)
        self.sub_lbl.setAlignment(Qt.AlignCenter)
        cl.addWidget(self.sub_lbl)

        cl.addSpacing(24)

        tab_bar = QHBoxLayout()
        tab_bar.setSpacing(0)
        self.login_tab_btn = QPushButton("登 录")
        self.login_tab_btn.setObjectName("tab_btn")
        self.login_tab_btn.setCheckable(True)
        self.login_tab_btn.setChecked(True)
        self.login_tab_btn.clicked.connect(lambda: self._switch_tab(0))
        tab_bar.addWidget(self.login_tab_btn)

        self.reg_tab_btn = QPushButton("注 册")
        self.reg_tab_btn.setObjectName("tab_btn")
        self.reg_tab_btn.setCheckable(True)
        self.reg_tab_btn.clicked.connect(lambda: self._switch_tab(1))
        tab_bar.addWidget(self.reg_tab_btn)
        tab_bar.addStretch()
        cl.addLayout(tab_bar)

        cl.addSpacing(4)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: %s;" % BORDER)
        cl.addWidget(sep)

        cl.addSpacing(12)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_login_form())
        self.stack.addWidget(self._build_register_form())
        cl.addWidget(self.stack, stretch=1)

        cl.addStretch()
        root.addWidget(center, stretch=1)

    def _fill_form(self, parent_lay):
        parent_lay.addStretch()

    def _build_login_form(self):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        lbl_u = self._lbl("用户名"); self._label_lu = lbl_u; lay.addWidget(lbl_u)
        self.login_user = QLineEdit()
        self.login_user.setPlaceholderText("请输入用户名")
        self.login_user.setMinimumHeight(38)
        lay.addWidget(self.login_user)

        lbl_p = self._lbl("密    码"); self._label_lp = lbl_p; lay.addWidget(lbl_p)
        self.login_pwd = QLineEdit()
        self.login_pwd.setPlaceholderText("请输入密码")
        self.login_pwd.setEchoMode(QLineEdit.Password)
        self.login_pwd.setMinimumHeight(38)
        self.login_pwd.returnPressed.connect(self._do_login)
        lay.addWidget(self.login_pwd)

        row = QHBoxLayout()
        self.remember_cb = QCheckBox("记住密码")
        row.addWidget(self.remember_cb)
        row.addStretch()
        lay.addLayout(row)

        self.login_msg = QLabel("")
        self.login_msg.setMinimumHeight(20)
        self.login_msg.setStyleSheet("background: transparent;")
        lay.addWidget(self.login_msg)

        btn = QPushButton("登 录")
        btn.setObjectName("primary")
        btn.setMinimumHeight(42)
        btn.clicked.connect(self._do_login)
        self._login_btn = btn
        lay.addWidget(btn)
        lay.addSpacing(8)
        return w

    def _build_register_form(self):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        lbl_ru = self._lbl("用户名"); self._label_ru = lbl_ru; lay.addWidget(lbl_ru)
        self.reg_user = QLineEdit()
        self.reg_user.setPlaceholderText("设置用户名（4-20位字母数字）")
        self.reg_user.setMinimumHeight(38)
        lay.addWidget(self.reg_user)

        lbl_rp = self._lbl("密    码"); self._label_rp = lbl_rp; lay.addWidget(lbl_rp)
        self.reg_pwd = QLineEdit()
        self.reg_pwd.setPlaceholderText("设置密码（6位以上）")
        self.reg_pwd.setEchoMode(QLineEdit.Password)
        self.reg_pwd.setMinimumHeight(38)
        lay.addWidget(self.reg_pwd)

        lbl_rp2 = self._lbl("确认密码"); self._label_rp2 = lbl_rp2; lay.addWidget(lbl_rp2)
        self.reg_pwd2 = QLineEdit()
        self.reg_pwd2.setPlaceholderText("再次输入密码")
        self.reg_pwd2.setEchoMode(QLineEdit.Password)
        self.reg_pwd2.setMinimumHeight(38)
        lay.addWidget(self.reg_pwd2)

        self.reg_msg = QLabel("")
        self.reg_msg.setMinimumHeight(20)
        self.reg_msg.setStyleSheet("background: transparent;")
        lay.addWidget(self.reg_msg)

        btn = QPushButton("注 册 账 号")
        btn.setObjectName("primary")
        btn.setMinimumHeight(42)
        btn.clicked.connect(self._do_register)
        self._reg_btn = btn
        lay.addWidget(btn)
        lay.addSpacing(8)
        return w

    def _lbl(self, text):
        l = QLabel(text)
        l.setFont(QFont("Microsoft YaHei", 11))
        l.setStyleSheet("color: %s; background: transparent;" % TEXT_SUB)
        return l

    def _set_msg(self, label, text, error=True):
        color = ERROR if error else SUCCESS
        label.setStyleSheet("color: %s; font-size: 12px; background: transparent;" % color)
        label.setText(text)

    def _switch_tab(self, index):
        self.stack.setCurrentIndex(index)
        self.login_tab_btn.setChecked(index == 0)
        self.reg_tab_btn.setChecked(index == 1)

    def _load_remembered(self):
        data = load_remembered()
        if data:
            self.login_user.setText(data.get("username", ""))
            self.login_pwd.setText(data.get("password", ""))
            self.remember_cb.setChecked(True)

    def _do_login(self):
        u = self.login_user.text().strip()
        p = self.login_pwd.text()
        if not u or not p:
            self._set_msg(self.login_msg, "用户名和密码不能为空")
            return
        users = load_users()
        if u not in users:
            self._set_msg(self.login_msg, "账号不存在，请先注册")
            return
        if users[u]["password"] != hash_password(p):
            self._set_msg(self.login_msg, "密码错误，请重试")
            return
        if self.remember_cb.isChecked():
            save_remembered(u, p)
        else:
            clear_remembered()
        self._set_msg(self.login_msg, "欢迎回来，%s！正在进入系统..." % u, error=False)
        QTimer.singleShot(600, self.accept)

    def _do_register(self):
        u = self.reg_user.text().strip()
        p = self.reg_pwd.text()
        p2 = self.reg_pwd2.text()
        if not u or not p:
            self._set_msg(self.reg_msg, "用户名和密码不能为空")
            return
        if len(u) < 4:
            self._set_msg(self.reg_msg, "用户名至少4位")
            return
        if len(p) < 6:
            self._set_msg(self.reg_msg, "密码至少6位")
            return
        if p != p2:
            self._set_msg(self.reg_msg, "两次密码不一致")
            return
        users = load_users()
        if u in users:
            self._set_msg(self.reg_msg, "用户名已存在，请换一个")
            return
        users[u] = {"password": hash_password(p)}
        save_users(users)
        self._set_msg(self.reg_msg, "注册成功！自动跳转登录...", error=False)
        self.login_user.setText(u)
        self.login_pwd.setText(p)
        QTimer.singleShot(900, lambda: self._switch_tab(0))


# ── 入口 ──
if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    dlg = LoginDialog()
    dlg.show()
    if dlg.exec_() == QDialog.Accepted:
        from app import MainWindow
        username = dlg.login_user.text().strip()
        win = MainWindow(username=username)
        win.show()
        sys.exit(app.exec_())
    sys.exit(0)
