"""
Global config for emergency UAV dispatch system.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MATERIALS_FILE = os.path.join(BASE_DIR, "materials.json")
DRONES_FILE = os.path.join(BASE_DIR, "drones.json")
SERVICE_AREAS_FILE = os.path.join(BASE_DIR, "service_areas.json")
RESCUE_POINTS_FILE = os.path.join(BASE_DIR, "rescue_points.json")
MAPS_FILE = os.path.join(BASE_DIR, "maps.json")
ALGORITHMS_FILE = os.path.join(BASE_DIR, "algorithms.json")
TASKS_FILE = os.path.join(BASE_DIR, "tasks.json")

# Theme colors
DARK_BG = "#12161B"
PANEL_BG = "#1A2028"
ACCENT = "#2C7A5A"
ACCENT_DARK = "#245F46"
BORDER = "#2B3441"
TEXT_MAIN = "#E6E8EC"
TEXT_SUB = "#A3AFBF"
INPUT_BG = "#11161D"
SUCCESS = "#3E8E5B"
ERROR = "#C85A54"
WARNING = "#C39A3A"
SIDEBAR_BG = "#151B23"
SIDEBAR_HOVER = "#242D38"
SIDEBAR_ACTIVE = "#2A3644"
TABLE_ROW_ALT = "#171D25"

PRIORITY_MAP = {
    "紧急(P0)": 0,
    "高(P1)": 1,
    "中(P2)": 2,
    "低(P3)": 3,
}

PRIORITY_COLORS = {
    0: "#C85A54",
    1: "#C39A3A",
    2: "#2C7A5A",
    3: "#7C8796",
}

DEFAULT_SERVICE_AREAS = [
    {"name": "北区服务区", "x": 100.0, "y": 200.0, "z": 0.0},
    {"name": "南区服务区", "x": 100.0, "y": -200.0, "z": 0.0},
    {"name": "东区服务区", "x": 300.0, "y": 0.0, "z": 0.0},
    {"name": "西区服务区", "x": -300.0, "y": 0.0, "z": 0.0},
    {"name": "中心服务区", "x": 0.0, "y": 0.0, "z": 0.0},
]

DEFAULT_RESCUE_POINTS = [
    {"name": "灾区A-居民区", "x": 150.0, "y": 300.0, "z": 50.0, "priority": 0, "priority_text": "紧急(P0)", "note": ""},
    {"name": "灾区B-学校", "x": -200.0, "y": 150.0, "z": 30.0, "priority": 1, "priority_text": "高(P1)", "note": ""},
    {"name": "灾区C-医院", "x": 250.0, "y": -100.0, "z": 20.0, "priority": 0, "priority_text": "紧急(P0)", "note": ""},
]

DEFAULT_MAPS = [
    {"name": "城市地震场景", "file": "map_city_quake.py", "desc": "城市震后废墟与受损建筑环境"},
    {"name": "山区避障场景", "file": "map_flood.py", "desc": "山区山峰障碍避障场景"},
]

DEFAULT_ALGORITHMS = [
    {"name": "改进HHO算法", "file": "algo_hho.py", "desc": "哈里斯鹰优化算法，全局路径寻优"},
    {"name": "改进RRT*算法", "file": "algo_rrt.py", "desc": "快速探索随机树，三维动态避障"},
    {"name": "DQN强化学习", "file": "algo_dqn.py", "desc": "强化学习决策与路径规划"},
    {"name": "混合启发式算法", "file": "algo_hybrid.py", "desc": "双阶段混合启发式协同调度"},
]

GLOBAL_STYLE = f"""
QMainWindow, QWidget {{
    background-color: {DARK_BG};
    color: {TEXT_MAIN};
    font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
    font-size: 15px;
}}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {INPUT_BG};
    color: {TEXT_MAIN};
    border: 1.5px solid {BORDER};
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 15px;
    min-height: 38px;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 2px solid {ACCENT};
}}
QComboBox::drop-down {{ border: none; width: 30px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 7px solid {TEXT_SUB};
    margin-right: 10px;
}}
QComboBox QAbstractItemView {{
    background-color: {PANEL_BG};
    color: {TEXT_MAIN};
    border: 1px solid {BORDER};
    font-size: 15px;
    padding: 4px;
}}
QComboBox QAbstractItemView::item {{
    min-height: 36px;
    padding: 6px 12px;
}}
QComboBox QAbstractItemView::item:selected {{
    background-color: {ACCENT};
}}
QPushButton {{
    background-color: transparent;
    color: {TEXT_SUB};
    border: 1.5px solid {BORDER};
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 15px;
}}
QPushButton:hover {{
    background-color: {SIDEBAR_HOVER};
    color: {TEXT_MAIN};
    border-color: {ACCENT};
}}
QPushButton#primary {{
    background-color: {ACCENT};
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 15px;
    font-weight: bold;
}}
QPushButton#primary:hover {{ background-color: {ACCENT_DARK}; }}
QPushButton#primary:pressed {{ background-color: #1E4F3B; }}
QPushButton#start_btn {{
    background-color: {SUCCESS};
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    padding: 14px 40px;
    font-size: 18px;
    font-weight: bold;
}}
QPushButton#start_btn:hover {{ background-color: #32774C; }}
QPushButton#start_btn:pressed {{ background-color: #2A6240; }}
QPushButton#danger {{
    background-color: transparent;
    color: {ERROR};
    border: 1.5px solid {ERROR};
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 15px;
}}
QPushButton#danger:hover {{ background-color: {ERROR}; color: #FFFFFF; }}
QPushButton#sidebar {{
    background-color: transparent;
    color: {TEXT_SUB};
    border: none;
    border-radius: 0;
    padding: 16px 22px;
    font-size: 16px;
    text-align: left;
}}
QPushButton#sidebar:hover {{
    background-color: {SIDEBAR_HOVER};
    color: {TEXT_MAIN};
}}
QPushButton#sidebar:checked {{
    background-color: {SIDEBAR_ACTIVE};
    color: {TEXT_MAIN};
    border-left: 4px solid {ACCENT};
    font-weight: bold;
}}
QTableWidget {{
    background-color: {PANEL_BG};
    alternate-background-color: {TABLE_ROW_ALT};
    color: {TEXT_MAIN};
    border: 1.5px solid {BORDER};
    border-radius: 10px;
    gridline-color: {BORDER};
    font-size: 14px;
    selection-background-color: {ACCENT};
}}
QTableWidget::item {{ padding: 8px 10px; border: none; }}
QTableWidget::item:selected {{ background-color: {ACCENT}; color: #FFFFFF; }}
QHeaderView::section {{
    background-color: {SIDEBAR_BG};
    color: {TEXT_SUB};
    border: none;
    border-bottom: 2px solid {BORDER};
    padding: 10px 12px;
    font-size: 14px;
    font-weight: bold;
}}
QGroupBox {{
    background-color: {PANEL_BG};
    border: 1.5px solid {BORDER};
    border-radius: 10px;
    margin-top: 12px;
    padding: 20px 16px 16px 16px;
    font-size: 15px;
    font-weight: bold;
    color: {TEXT_MAIN};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 14px;
    color: {ACCENT};
    font-size: 15px;
}}
QLabel {{ font-size: 15px; }}
QScrollBar:vertical {{ background: {DARK_BG}; width: 10px; border-radius: 5px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 40px; }}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QSplitter::handle {{ background-color: {BORDER}; }}
QSplitter::handle:horizontal {{ width: 3px; }}
QSplitter::handle:vertical {{ height: 3px; }}
QSplitter::handle:hover {{ background-color: {ACCENT}; }}
"""

