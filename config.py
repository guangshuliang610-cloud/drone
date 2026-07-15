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
CONTOUR_DATA_FILE = os.path.join(BASE_DIR, "contour_data.json")

# === 新配色方案 (Emerald Dark Theme) ===
DARK_BG = "#080B10"           # 最深色背景
PANEL_BG = "#0C1117"          # 卡片/面板背景
SIDEBAR_BG = "#0A0E13"        # 侧边栏背景
INPUT_BG = "#0F1419"          # 输入框背景
ACCENT = "#2ECC71"            # 主强调色 (翠绿)
ACCENT_DARK = "#27AE60"       # 深一点的强调色
BORDER = "#151C26"            # 边框色
TEXT_MAIN = "#C8D0DC"         # 主文字
TEXT_SUB = "#5A6A7E"          # 次要文字
WHITE = "#FFFFFF"              # 纯白（标题）
SUCCESS = "#27AE60"           # 成功/在线
WARNING = "#F39C12"           # 警告/待命
ERROR = "#E74C3C"             # 错误/危险
TABLE_ROW_ALT = "#0C1117"     # 表格交替行
SIDEBAR_HOVER = "#111820"     # 导航悬停
SIDEBAR_ACTIVE = "#0F1A14"    # 导航选中

PRIORITY_MAP = {
    "紧急(P0)": 0,
    "高(P1)": 1,
    "中(P2)": 2,
    "低(P3)": 3,
}

PRIORITY_COLORS = {
    0: "#E74C3C",
    1: "#F39C12",
    2: "#27AE60",
    3: "#5A6A7E",
}

DEFAULT_SERVICE_AREAS = [
    {"name": "城北服务区", "x": 0.0, "y": 340.0, "z": 0.0, "scene": "城市地震场景"},
    {"name": "城南服务区", "x": 0.0, "y": -340.0, "z": 0.0, "scene": "城市地震场景"},
    {"name": "城东服务区", "x": 340.0, "y": 0.0, "z": 0.0, "scene": "城市地震场景"},
    {"name": "城西服务区", "x": -340.0, "y": 0.0, "z": 0.0, "scene": "城市地震场景"},
    {"name": "中心服务区", "x": 200.0, "y": 320.0, "z": 0.0, "scene": "城市地震场景"},
    {"name": "北山服务区", "x": 0.0, "y": 260.0, "z": 30.0, "scene": "山区避障场景"},
    {"name": "南谷服务区", "x": 0.0, "y": -260.0, "z": 31.0, "scene": "山区避障场景"},
    {"name": "东岭服务区", "x": 260.0, "y": 0.0, "z": 17.0, "scene": "山区避障场景"},
    {"name": "西峰服务区", "x": -280.0, "y": -280.0, "z": 33.0, "scene": "山区避障场景"},
    {"name": "中心营地", "x": 150.0, "y": -60.0, "z": 40.0, "scene": "山区避障场景"},
]

DEFAULT_RESCUE_POINTS = [
    {"name": "居民区A-河北区", "x": -280.0, "y": 250.0, "z": 9.0, "priority": 0, "priority_text": "紧急(P0)", "note": "老城居民楼3层", "scene": "城市地震场景"},
    {"name": "医院-和平区", "x": 170.0, "y": -100.0, "z": 12.0, "priority": 0, "priority_text": "紧急(P0)", "note": "医院4层", "scene": "城市地震场景"},
    {"name": "学校-南开区", "x": -200.0, "y": 130.0, "z": 15.0, "priority": 1, "priority_text": "高(P1)", "note": "南开大学5层", "scene": "城市地震场景"},
    {"name": "商业街-滨江道", "x": 80.0, "y": -50.0, "z": 30.0, "priority": 2, "priority_text": "中(P2)", "note": "滨江道商业10层", "scene": "城市地震场景"},
    {"name": "避难所-河西区", "x": -80.0, "y": -180.0, "z": 24.0, "priority": 1, "priority_text": "高(P1)", "note": "文化中心8层", "scene": "城市地震场景"},
    {"name": "灾区A-北坡居民点", "x": -170.0, "y": 200.0, "z": 73.0, "priority": 0, "priority_text": "紧急(P0)", "note": "", "scene": "山区避障场景"},
    {"name": "灾区B-河谷村庄", "x": 100.0, "y": -80.0, "z": 63.0, "priority": 0, "priority_text": "紧急(P0)", "note": "", "scene": "山区避障场景"},
    {"name": "灾区C-西岭小学", "x": -140.0, "y": -170.0, "z": 51.0, "priority": 1, "priority_text": "高(P1)", "note": "", "scene": "山区避障场景"},
    {"name": "灾区D-东坡林场", "x": 160.0, "y": 200.0, "z": 58.0, "priority": 1, "priority_text": "高(P1)", "note": "", "scene": "山区避障场景"},
    {"name": "灾区E-南谷农田", "x": -50.0, "y": -200.0, "z": 39.0, "priority": 2, "priority_text": "中(P2)", "note": "", "scene": "山区避障场景"},
]

DEFAULT_MAPS = [
    {"name": "城市地震场景", "file": "map_city_quake.py", "desc": "以天津为原型的北方城市震后场景，中心天塔、环形路网、分层建筑群"},
    {"name": "山区避障场景", "file": "map_flood.py", "desc": "山区山峰障碍避障场景"},
]

DEFAULT_ALGORITHMS = [
    {"name": "改进HHO算法", "file": "algo_hho.py", "desc": "哈里斯鹰优化算法，全局路径寻优"},
    {"name": "改进RRT*算法", "file": "algo_rrt.py", "desc": "快速探索随机树，三维动态避障"},
    {"name": "DQN强化学习", "file": "algo_dqn.py", "desc": "强化学习决策与路径规划"},
    {"name": "混合启发式算法", "file": "algo_hybrid.py", "desc": "双阶段混合启发式协同调度"},
]

DEFAULT_MATERIALS = [
    # 城市地震场景
    {"name": "医疗急救包", "priority": 0, "priority_text": "紧急(P0)", "weight": 2.5, "quantity": 10, "service_area": "城北服务区", "rescue_point": "居民区A-河北区", "note": "", "scene": "城市地震场景"},
    {"name": "饮用水", "priority": 0, "priority_text": "紧急(P0)", "weight": 12.0, "quantity": 20, "service_area": "城南服务区", "rescue_point": "医院-和平区", "note": "", "scene": "城市地震场景"},
    {"name": "方便食品", "priority": 1, "priority_text": "高(P1)", "weight": 8.0, "quantity": 15, "service_area": "城东服务区", "rescue_point": "学校-南开区", "note": "", "scene": "城市地震场景"},
    {"name": "折叠帐篷", "priority": 1, "priority_text": "高(P1)", "weight": 15.0, "quantity": 5, "service_area": "城西服务区", "rescue_point": "避难所-河西区", "note": "", "scene": "城市地震场景"},
    {"name": "通讯设备", "priority": 2, "priority_text": "中(P2)", "weight": 3.0, "quantity": 8, "service_area": "中心服务区", "rescue_point": "商业街-滨江道", "note": "", "scene": "城市地震场景"},
    # 山区避障场景
    {"name": "救援绳索", "priority": 0, "priority_text": "紧急(P0)", "weight": 5.0, "quantity": 6, "service_area": "北山服务区", "rescue_point": "灾区A-北坡居民点", "note": "", "scene": "山区避障场景"},
    {"name": "医疗急救包", "priority": 0, "priority_text": "紧急(P0)", "weight": 2.5, "quantity": 8, "service_area": "南谷服务区", "rescue_point": "灾区B-河谷村庄", "note": "", "scene": "山区避障场景"},
    {"name": "压缩食品", "priority": 1, "priority_text": "高(P1)", "weight": 6.0, "quantity": 12, "service_area": "东岭服务区", "rescue_point": "灾区C-西岭小学", "note": "", "scene": "山区避障场景"},
    {"name": "保暖毯", "priority": 1, "priority_text": "高(P1)", "weight": 1.5, "quantity": 20, "service_area": "西峰服务区", "rescue_point": "灾区D-东坡林场", "note": "", "scene": "山区避障场景"},
    {"name": "照明设备", "priority": 2, "priority_text": "中(P2)", "weight": 3.0, "quantity": 10, "service_area": "中心营地", "rescue_point": "灾区E-南谷农田", "note": "", "scene": "山区避障场景"},
]

SCENES = ["城市地震场景", "山区避障场景"]

DEFAULT_TASKS = [
    {"task_id": 0, "material": "应急食品包(5kg)", "priority": 0, "priority_text": "紧急(P0)", "weight": 5.0, "quantity": 20, "service_area": "城北服务区", "rescue_point": "居民区A-河北区", "note": "紧急救援物资", "scene": "城市地震场景"},
    {"task_id": 1, "material": "医疗急救箱", "priority": 0, "priority_text": "紧急(P0)", "weight": 2.0, "quantity": 15, "service_area": "城北服务区", "rescue_point": "医院-和平区", "note": "送往医院", "scene": "城市地震场景"},
    {"task_id": 2, "material": "饮用水(24瓶/箱)", "priority": 1, "priority_text": "高(P1)", "weight": 12.0, "quantity": 8, "service_area": "城南服务区", "rescue_point": "避难所-河西区", "note": "", "scene": "城市地震场景"},
    {"task_id": 3, "material": "儿童防寒毯", "priority": 2, "priority_text": "中(P2)", "weight": 1.5, "quantity": 30, "service_area": "城东服务区", "rescue_point": "商业街-滨江道", "note": "", "scene": "城市地震场景"},
    {"task_id": 4, "material": "发电机(小型)", "priority": 1, "priority_text": "高(P1)", "weight": 25.0, "quantity": 3, "service_area": "城西服务区", "rescue_point": "学校-南开区", "note": "", "scene": "城市地震场景"},
    {"task_id": 5, "material": "卫星电话", "priority": 0, "priority_text": "紧急(P0)", "weight": 0.5, "quantity": 10, "service_area": "北山服务区", "rescue_point": "灾区A-北坡居民点", "note": "通讯设备", "scene": "山区避障场景"},
    {"task_id": 6, "material": "担架(折叠式)", "priority": 0, "priority_text": "紧急(P0)", "weight": 3.5, "quantity": 8, "service_area": "南谷服务区", "rescue_point": "灾区B-河谷村庄", "note": "", "scene": "山区避障场景"},
    {"task_id": 7, "material": "应急帐篷(4人)", "priority": 1, "priority_text": "高(P1)", "weight": 8.0, "quantity": 5, "service_area": "东岭服务区", "rescue_point": "灾区C-西岭小学", "note": "", "scene": "山区避障场景"},
    {"task_id": 8, "material": "救生衣", "priority": 1, "priority_text": "高(P1)", "weight": 1.0, "quantity": 25, "service_area": "西峰服务区", "rescue_point": "灾区D-东坡林场", "note": "", "scene": "山区避障场景"},
    {"task_id": 9, "material": "工具箱(综合)", "priority": 2, "priority_text": "中(P2)", "weight": 3.0, "quantity": 10, "service_area": "中心营地", "rescue_point": "灾区E-南谷农田", "note": "", "scene": "山区避障场景"},
]

GLOBAL_STYLE = f"""
QMainWindow, QWidget {{
    background-color: {DARK_BG};
    color: {TEXT_MAIN};
    font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
    font-size: 15px;
}}

/* ==================== 输入控件 ==================== */
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
QComboBox::drop-down {{
    border: none;
    width: 30px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {TEXT_SUB};
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
    min-height: 34px;
    padding: 6px 12px;
}}
QComboBox QAbstractItemView::item:selected {{
    background-color: {ACCENT};
    color: #FFFFFF;
}}

/* ==================== 通用按钮 ==================== */
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
QPushButton:pressed {{
    background-color: rgba(46, 204, 113, 0.12);
}}

/* ==================== 主操作按钮 (primary) ==================== */
QPushButton#primary {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {ACCENT}, stop:1 {ACCENT_DARK});
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 10px 28px;
    font-size: 15px;
    font-weight: bold;
}}
QPushButton#primary:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #35DA7E, stop:1 {ACCENT});
}}
QPushButton#primary:pressed {{
    background: {ACCENT_DARK};
}}
QPushButton#primary:disabled {{
    background: #1A2330;
    color: {TEXT_SUB};
}}

/* ==================== 危险按钮 (danger) ==================== */
QPushButton#danger {{
    background-color: transparent;
    color: {ERROR};
    border: 1.5px solid {ERROR};
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 15px;
}}
QPushButton#danger:hover {{
    background-color: rgba(231, 76, 60, 0.15);
    color: {ERROR};
    border-color: {ERROR};
}}
QPushButton#danger:pressed {{
    background-color: rgba(231, 76, 60, 0.25);
}}

/* ==================== 侧边栏按钮 (sidebar) ==================== */
QPushButton#sidebar {{
    background-color: transparent;
    color: {TEXT_SUB};
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0;
    padding: 14px 20px;
    font-size: 15px;
    text-align: left;
}}
QPushButton#sidebar:hover {{
    background-color: {SIDEBAR_HOVER};
    color: {TEXT_MAIN};
    border-left: 3px solid {BORDER};
}}
QPushButton#sidebar:checked {{
    background-color: {SIDEBAR_ACTIVE};
    color: {ACCENT};
    border-left: 3px solid {ACCENT};
    font-weight: bold;
}}

/* ==================== 表格 ==================== */
QTableWidget {{
    background-color: {PANEL_BG};
    alternate-background-color: {TABLE_ROW_ALT};
    color: {TEXT_MAIN};
    border: 1.5px solid {BORDER};
    border-radius: 10px;
    gridline-color: {BORDER};
    font-size: 14px;
    selection-background-color: rgba(46, 204, 113, 0.25);
    selection-color: {TEXT_MAIN};
}}
QTableWidget::item {{
    padding: 8px 10px;
    border: none;
}}
QTableWidget::item:selected {{
    background-color: rgba(46, 204, 113, 0.25);
    color: {TEXT_MAIN};
}}
QHeaderView::section {{
    background-color: {SIDEBAR_BG};
    color: {TEXT_SUB};
    border: none;
    border-bottom: 2px solid {BORDER};
    padding: 10px 12px;
    font-size: 14px;
    font-weight: bold;
}}
QHeaderView::section:hover {{
    color: {TEXT_MAIN};
}}
QTableCornerButton::section {{
    background-color: {SIDEBAR_BG};
    border: none;
}}

/* ==================== 分组框 ==================== */
QGroupBox {{
    background-color: {PANEL_BG};
    border: 1.5px solid {BORDER};
    border-radius: 10px;
    margin-top: 12px;
    padding: 22px 16px 16px 16px;
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

/* ==================== 标签 ==================== */
QLabel {{
    font-size: 15px;
    color: {TEXT_MAIN};
    background: transparent;
}}
QLabel[secondary="true"] {{
    color: {TEXT_SUB};
    font-size: 13px;
}}

/* ==================== 滚动条（精致细条） ==================== */
QScrollBar:vertical {{
    background: {DARK_BG};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    subcontrol-position: none;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QScrollBar:horizontal {{
    background: {DARK_BG};
    height: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {ACCENT};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    subcontrol-position: none;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}

/* ==================== 分割器 ==================== */
QSplitter::handle {{
    background-color: {BORDER};
}}
QSplitter::handle:horizontal {{
    width: 3px;
}}
QSplitter::handle:vertical {{
    height: 3px;
}}
QSplitter::handle:hover {{
    background-color: {ACCENT};
}}
"""