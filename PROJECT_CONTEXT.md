# 项目上下文 — 应急无人机调度系统 v2.1

> 下次会话时上传此文件即可恢复所有项目背景信息。

---

## 一、项目基本信息

- **项目名称**：面向应急响应的无人机物资配送协同调度与路径优化
- **项目级别**：国家级大创项目（天津市大学生创新训练计划）
- **学校**：天津城建大学
- **学院**：理学院
- **负责人**：罗逸玲（学号 2310030126，女，23级数学与应用数学1班）
- **指导教师**：赵洪銮、王晓玲
- **项目周期**：2026年5月 — 2027年5月
- **申请经费**：900元

## 二、团队成员

| 姓名 | 学号 | 专业 | 分工 |
|---|---|---|---|
| 罗逸玲 | 2310030126 | 数学与应用数学23级1班 | 负责人 |
| 李媛媛 | 2305180818 | 数学与应用数学23级2班 | 模型建立与算法研究 |
| 杨莹 | 2410030220 | 数学与应用数学24级2班 | 模型建立与算法研究 |
| 梁广树 | 2429030219 | 人工智能24级2班 | 人工智能算法，系统开发 |
| 黄一诺 | 2510030123 | 数学与应用数学25级1班 | 实验仿真，系统开发 |
| 杨曼铃 | 2510030129 | 数学与应用数学25级1班 | 实验仿真，系统开发 |

## 三、技术栈

- **语言**：Python
- **GUI框架**：PyQt5
- **3D可视化**：matplotlib（Qt5Agg后端）
- **运行环境**：Anaconda 虚拟环境 `drone`（Windows）
- **项目路径**：`D:\Program Tools\python_project\drone\`
- **依赖安装**：`pip install PyQt5 matplotlib numpy`
- **统一版本号**：v2.1

## 四、文件结构（v2.1 整合后）

```
drone/
│
│  ── 核心文件 ──────────────────────────
├── config.py                  # 全局配置（颜色、路径、默认数据、样式）
├── utils.py                   # 工具函数（JSON读写、颜色转换）
│
│  ── 入口与主窗口 ─────────────────────
├── login.py                   # 登录/注册界面（入口）
├── app.py                     # 主控台窗口（导航栏 + 页面切换）
│
│  ── 页面模块 ──────────────────────────
├── material_page.py           # 物资管理
├── area_page.py               # 服务区管理
├── rescue_page.py             # 救援点管理
├── drone_page.py              # 无人机管理
├── dispatch_page.py           # 救援调度（地图+算法+3D画布+日志）
│                             # 含 BaseMap / BaseAlgorithm 基类
│
│  ── 地图模块 ──────────────────────────
├── map_city_quake.py          # 城区地震场景（Map类）
├── map_flood.py               # 山区洪水场景（Map类）
├── map_typhoon.py             # 台风沿海场景（Map类）
│
│  ── 算法模块 ──────────────────────────
├── algo_hho.py                # 改进HHO算法（哈里斯鹰优化）
├── algo_rrt.py                # 改进RRT*算法（三维避障）
├── algo_dqn.py                # DQN强化学习（Q-table实现）
├── algo_hybrid.py             # 混合启发式（GA全局分配 + ACO局部路径）
│
│  ── 数据文件（首次运行自动生成）──────
├── users.json                 # 用户账号
├── materials.json             # 物资数据
├── service_areas.json         # 服务区数据
├── rescue_points.json         # 救援点数据
├── drones.json                # 无人机数据
├── maps.json                  # 可选，默认值在config.py
├── algorithms.json            # 可选，默认值在config.py
└── remembered.json            # 记住密码
```

## 五、运行方式

```bash
conda activate drone
pip install PyQt5 matplotlib numpy

python login.py      # 登录 → 主控台
python app.py        # 直接测试主控台（跳过登录）
```

## 六、功能模块

### 📦 物资管理 (material_page.py)
- 添加/编辑/删除物资
- 字段：名称、优先级(P0~P3)、重量(kg)、数量、初始服务区（下拉选）、配送救援点（下拉选）、备注
- 搜索、优先级筛选
- 数据：materials.json

### 🏗 服务区管理 (area_page.py)
- 添加/编辑/删除服务区
- 字段：名称 + 三维坐标 (X, Y, Z)
- 数据：service_areas.json

### 🎯 救援点管理 (rescue_page.py)
- 添加/编辑/删除救援点
- 字段：名称 + 三维坐标 + 配送优先级 + 备注
- 数据：rescue_points.json

### 🤖 无人机管理 (drone_page.py)
- 设置数量（1~100），自动增减
- 每架：编号、名称、型号、载荷、航程、速度、电量、状态
- 批量状态切换，表格内可编辑
- 数据：drones.json

### 🚀 救援调度 (dispatch_page.py)
- 下拉选择救援图（3D 场景）
- 下拉选择算法
- 「开始调度」按钮 → matplotlib 3D 画布显示无人机轨迹
- 运行日志面板（QSplitter 可调比例）
- 动态加载地图/算法模块

## 七、地图模块接口

```python
from dispatch_page import BaseMap

class Map(BaseMap):
    name = "场景名称"
    desc = "场景描述"

    def get_obstacles(self):
        """返回障碍物列表：
           [{"center": [x,y,z], "size": [w,h,d], "type": "building"/...}, ...]
        """
        return []

    def get_service_areas(self):
        """返回服务区列表（可选，覆盖 config 默认值）"""
        return []

    def get_rescue_points(self):
        """返回救援点列表（可选，覆盖 config 默认值）"""
        return []

    def get_bounds(self):
        """返回地图边界 ((x_min,x_max), (y_min,y_max), (z_min,z_max))"""
        return ((-500, 500), (-500, 500), (0, 200))

    def render_3d(self, ax):
        """在 matplotlib Axes3D 上绘制地图"""
        pass
```

## 八、算法模块接口

```python
from dispatch_page import BaseAlgorithm

class Algorithm(BaseAlgorithm):
    name = "算法名称"
    desc = "算法描述"

    def solve(self, drones, materials, service_areas, rescue_points, map_obj):
        """
        参数：
          drones         - list[dict]  无人机列表
          materials      - list[dict]  物资列表
          service_areas  - list[dict]  服务区（含 name, x, y, z）
          rescue_points  - list[dict]  救援点（含 name, x, y, z, priority）
          map_obj        - BaseMap     地图对象

        返回 dict：
        {
            "trajectories": [
                {
                    "drone_id": 1,
                    "drone_name": "无人机-01",
                    "color": "#1E6FD9",
                    "waypoints": [
                        {"pos": [x, y, z], "label": "起点"},
                        {"pos": [x, y, z], "label": "投送点"},
                    ],
                    "total_distance": 1234.5,
                    "total_time": 320.0,
                    "delivered_materials": ["医疗急救包"],
                },
            ],
            "total_time": 1200.0,
            "total_distance": 5678.0,
            "success_rate": 0.95,
            "message": "调度完成...",
        }
        """
        ...

    def render_result(self, ax, result):
        """在 matplotlib Axes3D 上绘制调度轨迹"""
        pass
```

### 注册方式

在 config.py 的 DEFAULT_MAPS / DEFAULT_ALGORITHMS 中添加条目即可自动识别。

## 九、UI 设计规范

- **配色**：深色科技风
  - 背景 #0D1B2A，面板 #132337，边框 #1E3A5F
  - 强调色 #1E6FD9，成功 #2EAA6C，错误 #E24B4A，警告 #E6A817
- **字体**：Microsoft YaHei，全局 15px 起步
- **窗口**：主控台默认 1280×780，最小 960×600
- **自适应**：所有页面通过 resizeEvent 动态缩放字体
- **风格**：Fusion，圆角 8-10px

## 十、项目研究方向

### 核心算法
- 哈里斯鹰优化算法（HHO）— 全局路径寻优
- 改进 RRT* 算法 — 三维动态避障
- 深度强化学习（DQN）— 智能决策
- 双阶段混合启发式算法 — 协同调度

### 目标函数
最小化应急物资配送总时间 + 设备能耗优化

### 预期成果
1. 1份研究报告
2. 1篇学术论文
3. 1项软件著作权

## 十一、已知问题

- PyQt5 的 sipPyTypeDict() 警告不影响运行，升级 PyQt5 可消除
- 必须在 Anaconda 的 drone 环境下运行
- matplotlib 3D 画布在大量障碍物时可能卡顿

---

*最后更新：2026-05-27 23:12 | 版本：v2.1*
