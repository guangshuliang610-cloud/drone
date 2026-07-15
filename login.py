"""
Emergency UAV Dispatch System - Login/Register Interface
File: login.py
Description: Entry point, login then jump to main console
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

# --- File paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")
REMEMBER_FILE = os.path.join(BASE_DIR, "remembered.json")

# --- Stylesheet ---
LOGIN_STYLE = """
QDialog, QWidget {
    background-color: %(DARK_BG)s;
    color: %(TEXT_MAIN)s;
    font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
}
QLineEdit {
    background-color: %(INPUT_BG)s;
    color: %(TEXT_MAIN)s;
    border: 1.5px solid %(BORDER)s;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 14px;
    selection-background-color: rgba(46, 204, 113, 0.35);
}
QLineEdit:focus {
    border: 1.5px solid %(ACCENT)s;
    background-color: #10161E;
}
QPushButton#primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 %(ACCENT)s, stop:1 %(ACCENT_DARK)s);
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 12px 0;
    font-size: 15px;
    font-weight: bold;
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #35DA7E, stop:1 %(ACCENT)s);
}
QPushButton#primary:pressed {
    background: %(ACCENT_DARK)s;
}
QPushButton#tab_btn {
    background-color: transparent;
    color: %(TEXT_SUB)s;
    border: none;
    border-bottom: 2.5px solid transparent;
    padding: 10px 24px;
    font-size: 15px;
}
QPushButton#tab_btn:hover {
    color: %(TEXT_MAIN)s;
}
QPushButton#tab_btn:checked {
    color: %(ACCENT)s;
    border-bottom: 2.5px solid %(ACCENT)s;
    font-weight: bold;
}
QCheckBox {
    color: %(TEXT_SUB)s;
    font-size: 12px;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border-radius: 4px;
    border: 1.5px solid %(BORDER)s;
    background: %(INPUT_BG)s;
}
QCheckBox::indicator:checked {
    background-color: %(ACCENT)s;
    border-color: %(ACCENT)s;
}
QCheckBox::indicator:hover {
    border-color: %(ACCENT)s;
}
""" % {
    "DARK_BG": DARK_BG, "PANEL_BG": PANEL_BG, "ACCENT": ACCENT,
    "ACCENT_DARK": ACCENT_DARK, "BORDER": BORDER, "TEXT_MAIN": TEXT_MAIN,
    "TEXT_SUB": TEXT_SUB, "INPUT_BG": INPUT_BG, "SUCCESS": SUCCESS, "ERROR": ERROR,
}


# --- Utility functions ---
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


# --- Right decorative panel ---
class RightPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(260)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        self.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #0E1620, stop:0.5 #0A1018, stop:1 #060A0F);
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 40, 28, 32)
        lay.setSpacing(0)

        # Large icon
        icon = QLabel("\u2708")
        icon.setFont(QFont("Segoe UI Emoji", 48))
        icon.setStyleSheet("color: %s; background: transparent;" % ACCENT)
        icon.setAlignment(Qt.AlignCenter)
        lay.addWidget(icon)

        lay.addSpacing(18)

        # Title
        title = QLabel("Emergency UAV\nDispatch Platform")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title.setStyleSheet("color: %s; background: transparent;" % TEXT_MAIN)
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        lay.addSpacing(8)

        # Subtitle
        sub = QLabel("v2.1  \u00b7  Professional Edition")
        sub.setFont(QFont("Segoe UI", 9))
        sub.setStyleSheet("color: %s; background: transparent;" % TEXT_SUB)
        sub.setAlignment(Qt.AlignCenter)
        lay.addWidget(sub)

        lay.addStretch()

        # Feature list
        features = [
            "\u2714  3D terrain map visualization",
            "\u2714  Multi-algorithm path planning",
            "\u2714  UAV fleet scheduling",
            "\u2714  Real-time mission monitoring",
        ]
        for feat in features:
            lbl = QLabel(feat)
            lbl.setFont(QFont("Microsoft YaHei", 10))
            lbl.setStyleSheet("color: %s; background: transparent; padding: 3px 0;" % TEXT_SUB)
            lay.addWidget(lbl)

        lay.addStretch()

        # Footer
        footer = QLabel("\u00a9 2026 Emergency UAV")
        footer.setFont(QFont("Segoe UI", 8))
        footer.setStyleSheet("color: %s; background: transparent;" % BORDER)
        footer.setAlignment(Qt.AlignCenter)
        lay.addWidget(footer)


# --- Login/Register Dialog ---
class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Emergency UAV Dispatch System \u2014 Login")
        self.setMinimumSize(700, 480)
        self.resize(700, 480)
        self.setStyleSheet(LOGIN_STYLE)
        self._build_ui()
        self._load_remembered()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_scale()

    def _apply_scale(self):
        w = self.width()
        scale = max(0.8, min(1.5, w / 700))
        self.title_lbl.setFont(QFont("Microsoft YaHei", max(16, int(22 * scale)), QFont.Bold))
        self.sub_lbl.setFont(QFont("Microsoft YaHei", max(10, int(12 * scale))))

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(RightPanel(self))

        center = QWidget()
        center.setStyleSheet("background: %s;" % DARK_BG)
        cl = QVBoxLayout(center)
        cl.setContentsMargins(48, 36, 48, 32)
        cl.setSpacing(0)

        # Title
        self.title_lbl = QLabel("Emergency UAV Dispatch System")
        self.title_lbl.setFont(QFont("Microsoft YaHei", 22, QFont.Bold))
        self.title_lbl.setStyleSheet("color: %s; background: transparent;" % TEXT_MAIN)
        self.title_lbl.setAlignment(Qt.AlignCenter)
        cl.addWidget(self.title_lbl)

        cl.addSpacing(4)

        # Subtitle
        self.sub_lbl = QLabel("Emergency UAV Dispatch System")
        self.sub_lbl.setFont(QFont("Segoe UI", 12))
        self.sub_lbl.setStyleSheet("color: %s; background: transparent;" % TEXT_SUB)
        self.sub_lbl.setAlignment(Qt.AlignCenter)
        cl.addWidget(self.sub_lbl)

        cl.addSpacing(28)

        # Tab bar
        tab_bar = QHBoxLayout()
        tab_bar.setSpacing(0)
        self.login_tab_btn = QPushButton("Login")
        self.login_tab_btn.setObjectName("tab_btn")
        self.login_tab_btn.setCheckable(True)
        self.login_tab_btn.setChecked(True)
        self.login_tab_btn.clicked.connect(lambda: self._switch_tab(0))
        tab_bar.addWidget(self.login_tab_btn)

        self.reg_tab_btn = QPushButton("Register")
        self.reg_tab_btn.setObjectName("tab_btn")
        self.reg_tab_btn.setCheckable(True)
        self.reg_tab_btn.clicked.connect(lambda: self._switch_tab(1))
        tab_bar.addWidget(self.reg_tab_btn)
        tab_bar.addStretch()
        cl.addLayout(tab_bar)

        cl.addSpacing(4)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: %s;" % BORDER)
        cl.addWidget(sep)

        cl.addSpacing(16)

        # Stacked forms
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_login_form())
        self.stack.addWidget(self._build_register_form())
        cl.addWidget(self.stack, stretch=1)

        cl.addStretch()
        root.addWidget(center, stretch=1)

    def _build_login_form(self):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        lbl_u = self._lbl("Username"); self._label_lu = lbl_u; lay.addWidget(lbl_u)
        self.login_user = QLineEdit()
        self.login_user.setPlaceholderText("Enter your username")
        self.login_user.setMinimumHeight(42)
        lay.addWidget(self.login_user)

        lbl_p = self._lbl("Password"); self._label_lp = lbl_p; lay.addWidget(lbl_p)
        self.login_pwd = QLineEdit()
        self.login_pwd.setPlaceholderText("Enter your password")
        self.login_pwd.setEchoMode(QLineEdit.Password)
        self.login_pwd.setMinimumHeight(42)
        self.login_pwd.returnPressed.connect(self._do_login)
        lay.addWidget(self.login_pwd)

        row = QHBoxLayout()
        self.remember_cb = QCheckBox("Remember password")
        row.addWidget(self.remember_cb)
        row.addStretch()
        lay.addLayout(row)

        self.login_msg = QLabel("")
        self.login_msg.setMinimumHeight(20)
        self.login_msg.setStyleSheet("background: transparent;")
        lay.addWidget(self.login_msg)

        btn = QPushButton("Login")
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
        lay.setSpacing(10)

        lbl_ru = self._lbl("Username"); self._label_ru = lbl_ru; lay.addWidget(lbl_ru)
        self.reg_user = QLineEdit()
        self.reg_user.setPlaceholderText("Set username (4-20 chars, letters/digits)")
        self.reg_user.setMinimumHeight(42)
        lay.addWidget(self.reg_user)

        lbl_rp = self._lbl("Password"); self._label_rp = lbl_rp; lay.addWidget(lbl_rp)
        self.reg_pwd = QLineEdit()
        self.reg_pwd.setPlaceholderText("Set password (6+ chars)")
        self.reg_pwd.setEchoMode(QLineEdit.Password)
        self.reg_pwd.setMinimumHeight(42)
        lay.addWidget(self.reg_pwd)

        lbl_rp2 = self._lbl("Confirm Password"); self._label_rp2 = lbl_rp2; lay.addWidget(lbl_rp2)
        self.reg_pwd2 = QLineEdit()
        self.reg_pwd2.setPlaceholderText("Re-enter password")
        self.reg_pwd2.setEchoMode(QLineEdit.Password)
        self.reg_pwd2.setMinimumHeight(42)
        lay.addWidget(self.reg_pwd2)

        self.reg_msg = QLabel("")
        self.reg_msg.setMinimumHeight(20)
        self.reg_msg.setStyleSheet("background: transparent;")
        lay.addWidget(self.reg_msg)

        btn = QPushButton("Register & Login")
        btn.setObjectName("primary")
        btn.setMinimumHeight(44)
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
            self._set_msg(self.login_msg, "Username and password cannot be empty")
            return
        users = load_users()
        if u not in users:
            self._set_msg(self.login_msg, "Account does not exist, please register first")
            return
        if users[u]["password"] != hash_password(p):
            self._set_msg(self.login_msg, "Incorrect password, please try again")
            return
        if self.remember_cb.isChecked():
            save_remembered(u, p)
        else:
            clear_remembered()
        self._set_msg(self.login_msg, "Welcome back, %s! Entering system..." % u, error=False)
        QTimer.singleShot(600, self.accept)

    def _do_register(self):
        u = self.reg_user.text().strip()
        p = self.reg_pwd.text()
        p2 = self.reg_pwd2.text()
        if not u or not p:
            self._set_msg(self.reg_msg, "Username and password cannot be empty")
            return
        if len(u) < 4:
            self._set_msg(self.reg_msg, "Username must be at least 4 characters")
            return
        if len(p) < 6:
            self._set_msg(self.reg_msg, "Password must be at least 6 characters")
            return
        if p != p2:
            self._set_msg(self.reg_msg, "Passwords do not match")
            return
        users = load_users()
        if u in users:
            self._set_msg(self.reg_msg, "Username already exists, please choose another")
            return
        users[u] = {"password": hash_password(p)}
        save_users(users)
        self._set_msg(self.reg_msg, "Registration successful! Redirecting to login...", error=False)
        self.login_user.setText(u)
        self.login_pwd.setText(p)
        QTimer.singleShot(900, lambda: self._switch_tab(0))


# --- Entry point ---
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
