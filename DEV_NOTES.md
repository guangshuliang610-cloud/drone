# 应急无人机调度系统 — 开发笔记

> 最后更新：2026-07-15  
> 分支：main，最新提交：`b1264a1`

---

## 一、系统概述

**应急无人机调度系统** — 基于 PyQt5 + Plotly + NumPy 的 3D 无人机路径规划与调度平台。

### 技术栈
- Python 3.10+ / PyQt5 / QWebEngineView + Plotly
- NumPy 线性代数运算 + Matplotlib 备用渲染
- JSON 持久化（无人机/物资/救援点/算法配置）

### 目录结构
```
.
├── app.py               # 主窗口、侧边栏导航、页面切换
├── login.py             # 登录页
├── dispatch_page.py     # 调度页（算法选择 + 三维渲染）
├── drone_page.py        # 无人机管理（CRUD）
├── material_page.py     # 物资管理
├── rescue_page.py       # 救援点管理
├── area_page.py         # 服务区管理
├── task_page.py         # 任务历史
├── config.py            # 配色 + 默认数据（地图/算法/物资）
├── utils.py             # JSON 读写工具
│
├── map_city_quake.py    # 城市地震场景地图（天津原型）
├── map_flood.py         # 山区避障场景地图
│
├── algo_rrt_star.py     # 🟢 主用算法：RRT* 路径规划
├── algo_power.py        # 电量约束：RRT* + 换电站插入
├── algo_apf.py          # 人工势场法
├── algo_ialns.py        # 自适应大邻域搜索（VRP）
├── algo_nsga2.py        # NSGA-II 多目标优化
├── algo_risk3d.py       # 三维风险评估
├── write_apf.py         # APF 变体
│
├── drones.json          # 无人机数据
├── materials.json       # 物资数据
├── rescue_points.json   # 救援点数据
├── service_areas.json   # 服务区数据
├── algorithms.json      # 算法注册列表
└── contour_data.json    # 山区等高线地形数据（压缩）
```

---

## 二、Git 提交历史（近期）

| Hash | 类型 | 说明 |
|------|------|------|
| `b1264a1` | fix | 所有救援点 z=2（地面），避难所移至空地 (-100,200) |
| `478f036` | fix | 救援点高度修正为地面或屋顶（后被 b1264a1 覆盖为全地面） |
| `029836c` | refactor | 去除救援点名称中的行政区后缀（河北区/和平区等） |
| `7957d5e` | fix | RRT* 自适应采样 + 安全海拔 fallback + 救援点重定位避建筑 |
| `c3b5c3c` | fix | 侧边栏去菱形图标 + 图例只首项 + 救援点数据恢复 |
| `a99373b` | style | 登录页英译中 |
| `4b7d7ed` | style | 山区 3D 配色对齐备份版本 |
| `3cb6569` | fix | 导航菜单对齐 + 3D 山区主题适配 |
| `631b9bf` | style | UI 改版：Emerald Dark Theme |
| `00d9f11` | refactor | 算法模块大替换：新增 6 个算法（RRT*/IALNS/NSGA-II/APF/Risk3D/Power） |

### 备份分支
- `backup/before-cleanup` — 清理前快照
- `backup/post-redesign-fixes` — UI 改版修复后快照
- `backup/pre-ui-redesign` — UI 改版前快照

---

## 三、架构关键约束

### 3.1 地图模块接口
每个地图类必须实现 `BaseMap` 接口：
```python
class BaseMap:
    name: str           # 场景名称
    desc: str           # 场景描述
    def get_obstacles(self) -> list    # 障碍物列表 {center, size, type}
    def get_service_areas(self) -> list  # 服务区 {name, x, y, z, scene}
    def get_rescue_points(self) -> list  # 救援点 {name, x, y, z, priority, ...}
    def get_bounds(self) -> tuple       # ((x_min,x_max), (y_min,y_max), (z_min,z_max))
    def render_plotly(self, result) -> list  # Plotly traces 列表
```

山区地图额外提供 `get_terrain_height(gx, gy)` 供地形避障。

### 3.2 算法模块接口
每个算法类必须实现 `BaseAlgorithm` 接口：
```python
class BaseAlgorithm:
    name: str
    desc: str
    def solve(self, drones, materials, service_areas, rescue_points, map_obj) -> dict
    def render_plotly(self, result) -> list
```

### 3.3 数据流
```
用户操作 → JSON文件 → 调度页 _on_start():
    1. 读取 drones.json → 无人机列表
    2. 从地图模块获取 service_areas + rescue_points（不硬编码！）
    3. map_obj.get_obstacles() → 建筑/地形障碍
    4. algo.solve(drones, materials, service_areas, rescue_points, map_obj)
    5. 返回 result: {trajectories, message, total_time}
    6. algo.render_plotly(result) → Plotly traces → QWebEngineView
```

### 3.4 导航菜单要点
- `dispatch_page.py` 必须在 `QApplication` 之前导入
- objectName 选择器不能随意更改（UI 逻辑依赖）
- 菱形符号已从侧边栏移除（c3b5c3c）

---

## 四、城区救援点坐标（最终版）

文件：`map_city_quake.py` → `get_rescue_points()`

| 名称 | x | y | z | 优先级 | 说明 |
|------|---|---|---|--------|------|
| 居民区A | -280 | 310 | 2 | P0 | 地面空地 |
| 医院 | 210 | -100 | 2 | P0 | 地面（医院旁空地） |
| 学校 | -200 | 180 | 2 | P1 | 地面 |
| 商业街 | 80 | -120 | 2 | P2 | 地面 |
| 避难所 | -100 | 200 | 2 | P1 | 远离建筑的空地 |

> 约束：z 必须 = 地面（2m）或 ≤ 建筑屋顶高度；避难所必须在空地。

---

## 五、建筑群数据（城区）

文件：`map_city_quake.py` → `get_obstacles()`

| 类型 | 数量 | 高度 |
|------|------|------|
| 电视塔 | 1 | 130m |
| CBD 超高层 | 4 | 60~82m |
| 中层公共建筑 | 10 | 35~48m |
| 传统低层民居 | 15 | 13~20m |
| **合计** | **30** | — |

---

## 六、当前遗留问题

### 🔴 问题 1：RRT* 未收敛触发飞越模式

**现象**：调度时显示 `2 架无人机使用飞越模式(RRT*未收敛)`

**根因**：`algo_rrt_star.py`:
```python
MAX_ITER = 800   # 最多 800 次采样
STEP_SIZE = 35
GOAL_BIAS = 0.15
```
800 次随机采样在 30 个障碍物的密集城区中，无法保证覆盖所有起点-终点组合。

**当前行为**：未收敛 → `_fallback_path()` → 计算安全高度 → `[起点 → 高点 → 终点]` 折线

**可行方案**：
1. 提高 `MAX_ITER = 2000`，`GOAL_BIAS = 0.22`
2. 保留飞越模式作为正常 fallback
3. 区分显示（当前已实现：路径用红色虚线）

---

### 🔴 问题 2：无人机电量管理未接入主算法

**现象**：无人机管理页修改 `battery` 参数，调度不触发换电。

**根因**：
- `algo_rrt_star.py`（主用算法）**不评估电量**
- `algo_power.py`（电量算法）需要手动从下拉框选择
- 两算法共用默认参数，`algo_power.py` **硬编码常量**：

```python
E_CONSUME = 0.08   # 每米耗电 — 应从 drone 对象读取
MAX_E = 100.0      # 满电量 — 应从 drone["battery"] 读取
SWAP_TIME = 1.8    # 换电时间 — 应从 drone["model"] 推断
```

**数据结构**（`drones.json`）：
```json
{
  "id": 1, "name": "无人机-01", "model": "DJI M30T",
  "max_payload": 5.0, "max_range": 15.0,
  "max_speed": 60.0, "battery": 100, "status": "待命"
}
```

**城区现状**：地图最大跨度 ~400 单位，满电航程 = 100/0.08 = 1250 单位，一次飞行不触发换电。

**可行方案**：
1. 将电量检查嵌入 `algo_rrt_star.py`（不增加算法入口）
2. 让 `algo_power.py` 读取 drone 对象参数（替代硬编码常量）
3. 定义：RRT* 收敛 + 电量充足 = 成功；电量不足 = 插入换电站

---

### 🟡 问题 3：地图距离单位缺失

地图没有标注实际距离比例尺，地图单位与实际米的换算关系未定义。无人机 max_speed=60 的单位不明（km/h? m/s?），导致电量消耗公式 `E_CONSUME × 距离` 的物理意义不清。

**建议**：在地图渲染或侧边栏增加比例尺，并在文档中定义 `1 地图单位 = N 米`。

---

### 🟡 问题 4：算法-页面渲染链路

`algo_power.py` 内部调用了 `algo_rrt_star.py` 并扩展 waypoints，但渲染时需要同时绘制：
- 正常轨迹（实线）
- 换电站标记（绿色方块+⚡）
- 虚线标识的飞越 fallback 路径

三套状态共享 `trajectories` 中的 `waypoints` / `swap_stations` / `is_fallback` 字段，渲染逻辑在 `render_plotly()` 中。如果扩展新状态，需同步更新渲染。

---

## 七、恢复与回档

```bash
# 回退最近 N 次提交
git revert HEAD~N     # 生成反提交
# 或
git reset --hard HASH  # 硬回退

# 恢复到算法大替换前
git checkout backup/before-cleanup

# 恢复到 UI 改版前
git checkout backup/pre-ui-redesign
```

---

## 八、UI 改版产物备忘

- **主题**：Emerald Dark — 深色背景 `#080B10`，面板 `#0C1117`
- **配色**：主文本 `#E0E6ED`，次文本 `#8899AA`，成功 `#00E676`，警告 `#FFD700`，错误 `#FF4444`
- **字体**：Aller（已删除字体文件依赖，回退至系统字体）
- **图标**：侧边栏无菱形前缀符号
- **布局**：4 页管理（无人机/物资/救援点/服务区）+ 调度 + 任务 + 登录

---

## 九、未决定项

| 问题 | 选项 A | 选项 B | 选项 C |
|------|--------|--------|--------|
| RRT* 未收敛 | 提高迭代数到 2000 | 保留飞越模式 | 增加提示 |
| 电量约束 | 嵌入 RRT* | 修正 algo_power 读取 drone 参数 | 独立算法 |
| 距离单位 | 地图加比例尺 | 文档定义换算 | 维持现状 |

