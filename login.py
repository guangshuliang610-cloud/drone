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

# ── 文件路径 ──────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
USERS_FILE    = os.path.join(BASE_DIR, "users.json")
REMEMBER_FILE = os.path.join(BASE_DIR, "remembered.json")

# ── 颜色常量 ──────────────────────────────────────────────
DARK_BG     = "#12161B"
PANEL_BG    = "#1A2028"
RIGHT_BG    = "#141A22"
ACCENT      = "#2C7A5A"
ACCENT_DARK = "#245F46"
BORDER      = "#2B3441"
TEXT_MAIN   = "#E6E8EC"
TEXT_SUB    = "#A3AFBF"
INPUT_BG    = "#11161D"
SUCCESS     = "#3E8E5B"
ERROR       = "#C85A54"

GLOBAL_STYLE = f"""
QDialog, QWidget {{
    background-color: {DARK_BG};
    color: {TEXT_MAIN};
    font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
}}
QLineEdit {{
    background-color: {INPUT_BG};
    color: {TEXT_MAIN};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}}
QLineEdit:focus {{ border: 1.5px solid {ACCENT}; }}
QPushButton#primary {{
    background-color: {ACCENT};
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 10px 0;
    font-size: 14px;
    font-weight: bold;
}}
QPushButton#primary:hover {{ background-color: {ACCENT_DARK}; }}
QPushButton#primary:pressed {{ background-color: #1E4F3B; }}
QPushButton#tab_btn {{
    background-color: transparent;
    color: {TEXT_SUB};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 8px 20px;
    font-size: 14px;
}}
QPushButton#tab_btn:checked {{
    color: {TEXT_MAIN};
    border-bottom: 2px solid {ACCENT};
    font-weight: bold;
}}
QCheckBox {{
    color: {TEXT_SUB};
    font-size: 12px;
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 14px; height: 14px;
    border-radius: 3px;
    border: 1px solid {BORDER};
    background: {INPUT_BG};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}
"""


# ── 工具函数 ──────────────────────────────────────────────
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


# ── 右侧装饰面板 ─────────────────────────────────────────
class RightPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setStyleSheet(f"background-color: {RIGHT_BG};")
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 36, 24, 28)
        lay.setSpacing(0)

        icon = QLabel("✈")
        icon.setFont(QFont("Segoe UI Emoji", 34))
        icon.setStyleSheet(f"color: {ACCENT}; background: transparent;")
        icon.setAlignment(Qt.AlignCenter)
        lay.addWidget(icon)

        lay.addSpacing(14)

        title = QLabel("应急无人机\n调度平台")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT_MAIN}; background: transparent;")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        lay.addSpacing(6)
        sub = QLabel("Emergency UAV\nDispatch System")
        sub.setFont(QFont("Segoe UI", 9))
        sub.setStyleSheet(f"color: {TEXT_SUB}; background: transparent;")
        sub.setAlignment(Qt.AlignCenter)
        lay.addWidget(sub)

        lay.addSpacing(28)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"color: {BORDER};")
        lay.addWidget(line)
        lay.addSpacing(18)

        features = [
            ("⚡", "智能任务调度"),
            ("🗺", "三维地形视图"),
            ("🤖", "多机协同避障"),
            ("📡", "实时状态监控"),
            ("🛣", "动态路径规划"),
        ]
        for icon_txt, label in features:
            row = QHBoxLayout()
            row.setSpacing(10)
            ic = QLabel(icon_txt)
            ic.setFont(QFont("Segoe UI Emoji", 12))
            ic.setStyleSheet("background: transparent;")
            ic.setFixedWidth(22)
            tx = QLabel(label)
            tx.setFont(QFont("Microsoft YaHei", 11))
            tx.setStyleSheet(f"color: {TEXT_SUB}; background: transparent;")
            row.addWidget(ic)
            row.addWidget(tx)
            lay.addLayout(row)
            lay.addSpacing(12)

        lay.addStretch()

        ver = QLabel("v2.1  ·  应急专版")
        ver.setFont(QFont("Consolas", 9))
        ver.setStyleSheet(f"color: {BORDER}; background: transparent;")
        ver.setAlignment(Qt.AlignCenter)
        lay.addWidget(ver)


# ── 主登录对话框 ───────────────────────────────────────────
class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("应急无人机调度系统 — 登录")
        self.resize(760, 480)
        self.setMinimumSize(600, 420)
        self.setWindowFlags(Qt.Window)
        self.setStyleSheet(GLOBAL_STYLE)
        self._base_w = 760
        self._build_ui()
        self._load_remembered()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_scale()

    def _apply_scale(self):
        left_w = max(self.width() - 220, 400)
        scale = left_w / self._base_w

        f_title = max(12, int(15 * scale))
        f_tab   = max(11, int(14 * scale))
        f_label = max(10, int(11 * scale))
        f_input = max(11, int(13 * scale))
        f_btn   = max(12, int(14 * scale))
        f_check = max(10, int(12 * scale))
        h_input = max(34, int(40 * scale))
        h_btn   = max(38, int(44 * scale))
        pad     = max(6, int(8 * scale))

        extra = (
            f"QLineEdit {{ font-size: {f_input}px; padding: {pad}px 12px;"
            f" min-height: {h_input}px; max-height: {h_input + 10}px; }}"
            f"QPushButton#tab_btn {{ font-size: {f_tab}px; }}"
            f"QPushButton#primary {{ font-size: {f_btn}px; min-height: {h_btn}px; }}"
            f"QCheckBox {{ font-size: {f_check}px; }}"
        )
        self.setStyleSheet(GLOBAL_STYLE + extra)

        bold = QFont("Microsoft YaHei", f_title, QFont.Bold)
        norm = QFont("Microsoft YaHei", f_label)
        for attr, font in [
            ('_title_label', bold),
            ('_label_user', norm), ('_label_pwd', norm),
            ('_label_ru', norm), ('_label_rp', norm), ('_label_rp2', norm),
        ]:
            w = getattr(self, attr, None)
            if w:
                w.setFont(font)

        inp_font = QFont("Microsoft YaHei", f_input)
        for attr in ['login_user', 'login_pwd', 'reg_user', 'reg_pwd', 'reg_pwd2']:
            w = getattr(self, attr, None)
            if w:
                w.setFont(inp_font)

        tab_font = QFont("Microsoft YaHei", f_tab)
        for attr in ['login_tab_btn', 'reg_tab_btn']:
            w = getattr(self, attr, None)
            if w:
                w.setFont(tab_font)

        btn_font = QFont("Microsoft YaHei", f_btn, QFont.Bold)
        for attr in ['_login_btn', '_reg_btn']:
            w = getattr(self, attr, None)
            if w:
                w.setFont(btn_font)

        if hasattr(self, 'remember_cb'):
            self.remember_cb.setFont(QFont("Microsoft YaHei", f_check))

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        left_bg = QWidget()
        left_bg.setStyleSheet(f"background-color: {PANEL_BG};")
        left_bg.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        left_h = QHBoxLayout(left_bg)
        left_h.setContentsMargins(0, 0, 0, 0)
        left_h.setSpacing(0)

        card = QWidget()
        card.setStyleSheet("background: transparent;")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        card_v = QVBoxLayout(card)
        card_v.setContentsMargins(60, 0, 60, 0)
        card_v.setSpacing(0)
        card_v.addStretch(1)
        self._fill_form(card_v)
        card_v.addStretch(1)

        left_h.addWidget(card)
        root.addWidget(left_bg, stretch=1)
        root.addWidget(RightPanel())

    def _fill_form(self, parent_lay):
        title_row = QHBoxLayout()
        shield = QLabel("🛡")
        shield.setFont(QFont("Segoe UI Emoji", 16))
        shield.setStyleSheet("background: transparent;")
        sys_title = QLabel("应急无人机调度系统")
        sys_title.setFont(QFont("Microsoft YaHei", 15, QFont.Bold))
        sys_title.setStyleSheet(f"color: {TEXT_MAIN}; background: transparent;")
        self._title_label = sys_title
        title_row.addWidget(shield)
        title_row.addSpacing(8)
        title_row.addWidget(sys_title)
        title_row.addStretch()
        parent_lay.addLayout(title_row)
        parent_lay.addSpacing(24)

        tab_row = QHBoxLayout()
        tab_row.setSpacing(0)
        self.login_tab_btn = QPushButton("登  录")
        self.login_tab_btn.setObjectName("tab_btn")
        self.login_tab_btn.setCheckable(True)
        self.login_tab_btn.setChecked(True)
        self.login_tab_btn.clicked.connect(lambda: self._switch_tab(0))
        self.reg_tab_btn = QPushButton("注  册")
        self.reg_tab_btn.setObjectName("tab_btn")
        self.reg_tab_btn.setCheckable(True)
        self.reg_tab_btn.clicked.connect(lambda: self._switch_tab(1))
        tab_row.addWidget(self.login_tab_btn)
        tab_row.addWidget(self.reg_tab_btn)
        tab_row.addStretch()
        parent_lay.addLayout(tab_row)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setMinimumHeight(1)
        line.setStyleSheet(f"background: {BORDER}; border: none;")
        parent_lay.addWidget(line)
        parent_lay.addSpacing(22)

        self.stack = QStackedWidget()
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.stack.addWidget(self._build_login_form())
        self.stack.addWidget(self._build_register_form())
        parent_lay.addWidget(self.stack)

    def _build_login_form(self):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        lbl_u = self._lbl("用户名 / 工号"); self._label_user = lbl_u; lay.addWidget(lbl_u)
        self.login_user = QLineEdit()
        self.login_user.setPlaceholderText("请输入用户名")
        self.login_user.setMinimumHeight(40)
        lay.addWidget(self.login_user)

        lay.addSpacing(4)
        lbl_p = self._lbl("密  码"); self._label_pwd = lbl_p; lay.addWidget(lbl_p)
        self.login_pwd = QLineEdit()
        self.login_pwd.setPlaceholderText("请输入密码")
        self.login_pwd.setEchoMode(QLineEdit.Password)
        self.login_pwd.setMinimumHeight(40)
        self.login_pwd.returnPressed.connect(self._do_login)
        lay.addWidget(self.login_pwd)

        lay.addSpacing(6)
        self.remember_cb = QCheckBox("记住密码")
        lay.addWidget(self.remember_cb)

        self.login_msg = QLabel("")
        self.login_msg.setMinimumHeight(20)
        self.login_msg.setStyleSheet("background: transparent;")
        lay.addWidget(self.login_msg)

        btn = QPushButton("进 入 系 统")
        btn.setObjectName("primary")
        btn.setMinimumHeight(44)
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

        lbl_rp = self._lbl("密  码"); self._label_rp = lbl_rp; lay.addWidget(lbl_rp)
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
        l.setStyleSheet(f"color: {TEXT_SUB}; background: transparent;")
        return l

    def _set_msg(self, label, text, error=True):
        color = ERROR if error else SUCCESS
        label.setStyleSheet(f"color: {color}; font-size: 12px; background: transparent;")
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
        self._set_msg(self.login_msg, f"欢迎回来，{u}！正在进入系统...", error=False)
        QTimer.singleShot(600, self.accept)

    def _do_register(self):
        u = self.reg_user.text().strip()
        p = self.reg_pwd.text()
        p2 = self.reg_pwd2.text()
        if not u or not p:
            self._set_msg(self.reg_msg, "用户名和密码不能为空")
            return
        if len(u) < 4:
            self._set_msg(self.reg_msg, "用户名至少 4 位")
            return
        if len(p) < 6:
            self._set_msg(self.reg_msg, "密码至少 6 位")
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


# ── 入口 ──────────────────────────────────────────────────
if __name__ == "__main__":
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
