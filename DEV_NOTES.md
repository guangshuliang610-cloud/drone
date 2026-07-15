# 应急无人机调度系统 — 开发笔记

> 最后更新：2026-07-15  
> 分支：main，最新提交：`TBD-battery`  
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
├── algo_battery.py      # 🆕 统一电量管理：换电站插入+物理模型+渲染
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

### 🟢 问题 2（已解决）：无人机电量统一管理

> 2026-07-15 电量管理已重构为 `algo_battery.py`，所有 6 个算法统一接入。

**设计**：
- **物理模型**：电量容量由 `max_range` × 38 Wh/km 推导；或由 `battery_capacity_kWh` 字段显式指定。
- **换电时间**：根据无人机型号查表（DJI M30T = 2 分钟；DJI Mini = 1 分钟；Heavy/VTOL = 5 分钟），型号匹配忽略大小写与连字符差异。
- **阈值**：当下一段航程会导致剩余电量 < 25%，在最近服务区插入换电站航点，然后满电出发。
- **渲染**：换电站在 3D 视图中显示为绿色方块 ⚡，所有算法自动调用同一渲染逻辑。

**算法接入方式**（每个 `solve()` 末尾一行调用）：

```python
from algo_battery import BatteryManager
return BatteryManager().apply(drones, service_areas, result)
```

**已接入的算法**：
| 算法 | 接入前是否处理电量 |
|------|--------------------|
| `algo_rrt_star.py` | ❌ 新增 |
| `algo_apf.py` | ❌ 新增 |
| `algo_power.py` | ✅ 硬编码（已切换至统一管理） |
| `algo_ialns.py` | ❌ 新增 |
| `algo_nsga2.py` | ❌ 新增 |
| `algo_risk3d.py` | ❌ 新增 |

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

| 问题 | 选项 A | 选项 B | 选项 C | 状态 |
|------|--------|--------|--------|------|
| RRT* 未收敛 | 提高迭代数到 2000 | 保留飞越模式 | 增加提示 | ⏳ 讨论中 |
| ~~电量约束~~ | ~~嵌入 RRT*~~ | ~~修正 algo_power~~ | ~~独立算法~~ | ✅ 已选"统一模块"方案（algo_battery.py） |
| 距离单位 | 地图加比例尺 | 文档定义换算 | 维持现状 | ⏳ 讨论中 |
---

## 十、电量管理模块（algo_battery.py）

> 2026-07-15 新增

### 模块职责
所有 6 个算法在 `solve()` 末尾调用，自动完成：电量累计 → 安全阈值检查 → 最近服务区换电站插入 → 时间惩罚。

### 物理参数推导链

```
capacity_kWh  = drone["battery_capacity_kWh"] 或 (max_range_km × 38 Wh/km)
max_range_m    = max_range_km × 1000
e_consume_per_m = capacity_kWh / max_range_m   (kWh/m)
initial_energy  = capacity_kWh × (battery_pct / 100.0)
```

**阈值规则**：
- 剩余电量飞完下一段后 < 25% → 触发换电
- 剩余电量甚至不够飞到最近服务区 → 90% 当前电量硬飞到服务区（兜底）

**换电时间（秒）**：

| 型号 | 时间 |
|------|------|
| DJI M30T | 120 (2 min) |
| DJI M350/M300 | 150 (2.5 min) |
| DJI Mini | 60 (1 min) |
| EVO Heavy | 300 (5 min) |
| EVTOL | 420 (7 min) |
| 其他机型 | 按 capacity_kWh 分段推断（默认 120s） |

**输出数据**：

```python
traj["swap_stations"]      # [{"pos":[x,y,z], "name":"服务区名"}, ...]
traj["swap_count"]         # int，该机的换电次数
traj["battery_remaining_pct"]  # 飞到终点的剩余电量百分比
traj["power_low"]          # bool，是否触发过换电
traj["total_swap_time"]    # 本机换电总耗时（秒）
traj["total_time"]         # 重新计算 = 飞行时间 + 换电时间
traj["total_distance"]     # 包含服务区绕行的实际距离

result["total_swaps"]      # 所有无人机合计换电次数
result["total_swap_time"]  # 所有无人机合计换电时间（秒）
```

### 渲染集成
- 所有算法的 `render_plotly()` 和 `render_result()` 已统一注入换电站 ⚡ 标记绘制。
- 换电站使用 Plotly 的 Scatter3d mode=markers+text，symbol="square"，00E676 绿色方块 + ⚡ 符号。

---

