# 变更说明文档 (CHANGELOG)

> 项目：VMR Idea Graph — 基于大模型的科研热点追踪与分析系统  
> 日期：2026-07-07  
> 变更类型：概要设计与代码实现  

---

## 变更总览

| 任务编号 | 任务名称 | 产出 |
|----------|----------|------|
| 任务1 | 核心模块设计（可视化展示模块） | `docs/模块设计_可视化展示.md` + 前端代码 |
| 任务2 | API设计（前端对接） | `docs/API设计_前端对接.md` |
| 任务3 | 数据存储设计（前端部分） | `docs/数据存储设计_前端部分.md` + 前端代码 |
| 任务4 | 接口层设计 | `docs/接口层设计.md` + Flask后端代码 |

---

## 新建文件

### 设计文档（4个）

| 文件 | 说明 |
|------|------|
| `docs/模块设计_可视化展示.md` | T4模块4个可视化组件的详细设计：Idea森林星图、树根探索图谱、分析仪表盘(4个ECharts图表)、论文详情页 |
| `docs/API设计_前端对接.md` | 11个API接口完整定义，含请求参数、返回格式、错误码 |
| `docs/数据存储设计_前端部分.md` | 三级缓存策略、LRU淘汰机制、localStorage持久化、定时刷新策略 |
| `docs/接口层设计.md` | API Gateway层架构：Flask框架、中间件、统一响应格式、错误处理规范 |

### 后端代码（9个文件）

| 文件 | 说明 |
|------|------|
| `source/backend/app.py` | Flask应用入口，路由注册、中间件、静态文件serve |
| `source/backend/config.py` | 配置：数据路径、端口、CORS |
| `source/backend/data_loader.py` | JSON数据加载器，一次性加载到内存并建索引 |
| `source/backend/middleware/response.py` | 统一响应格式：`success()` / `error()` / `make_pagination()` |
| `source/backend/routes/graph.py` | 图谱路由：`/api/graph/forest`、`/api/graph/root` |
| `source/backend/routes/papers.py` | 论文路由：`/api/papers`、`/api/papers/{id}`、`/api/papers/{id}/related` |
| `source/backend/routes/ideas.py` | Idea路由：`/api/ideas`、`/api/ideas/{id}` |
| `source/backend/routes/trends.py` | 趋势路由：`/api/trends/hot-topics`、`/api/trends/temporal` |
| `source/backend/services/graph_service.py` | 图谱构建服务：森林图60节点+180连线计算、树根图构建 |
| `source/backend/services/paper_service.py` | 论文查询服务：分页、全文搜索、Jaccard关联推荐 |
| `source/backend/services/trend_service.py` | 趋势分析服务：热点排名、时间趋势、增长率计算 |

---

## 修改文件

### `source/automation_platform/projects/vmr_idea_dashboard/index.html`

**改动位置**：第1-19行

**改动内容**：
1. 引入 ECharts 5.5.0 CDN（`<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js">`）
2. 新增全局导航栏 `<nav id="globalNav">`：支持 Idea森林 / 分析仪表盘 视图切换
3. 新增仪表盘容器 `<div id="dashboardPanel">`：4个chart-card（chartPie/chartLine/chartBar/chartRadar）
4. 新增论文详情页容器 `<div id="paperPage">`

### `source/automation_platform/projects/vmr_idea_dashboard/styles.css`

**改动位置**：第823行之后新增约190行

**改动内容**：
1. **全局导航栏样式** (`.global-nav`, `.nav-link`)：固定顶部48px，毛玻璃效果，active态
2. **仪表盘样式** (`.dashboard-panel`, `.dashboard-grid`, `.chart-card`)：2×2网格布局，卡片容器
3. **论文详情页样式** (`.paper-page`, `.paper-page-grid`, `.paper-page-section`)：双栏布局，证据链样式
4. **关联推荐样式** (`.related-papers-grid`, `.related-paper-card`)：自适应卡片网格
5. **辅助样式** (`.chart-idea-selector`, `.muted`, `.paper-tag`, `.paper-evidence-item`)：雷达图下拉框、标签、证据句

### `source/automation_platform/projects/vmr_idea_dashboard/app.js`

**改动位置**：多处（由1156行增至1594行）

**改动1 — 状态扩展** (第33行)：
- 新增 `dashboardChartsReady: false` 字段

**改动2 — 视图路由扩展** (`renderApp`函数，第244-247行)：
- 原逻辑：`if (mode === "root") renderRootView(); else renderForestView();`
- 新逻辑：增加 `dashboard` → `renderDashboard()`、`paper` → `renderPaperPage()`
- 增加导航栏和视图容器的显隐切换

**改动3 — 新增 LRU缓存类** (第1175-1191行)：
- `LRUCache(maxSize)`：基于Map的LRU淘汰

**改动4 — 新增 localStorage持久化** (第1193-1230行)：
- `loadViewState()` / `saveViewState()`：浏览状态（视图模式、选中Idea、变换参数）
- `loadPrefs()` / `savePrefs()`：用户偏好（预留）

**改动5 — 新增 分析仪表盘** (第1232-1345行)：
- `renderDashboard()`：切换到仪表盘视图，延迟100ms初始化图表
- `initDashboardCharts()`：初始化4个ECharts图表
  - 饼图 (`#chartPie`)：问题族论文分布，环形饼图
  - 折线图 (`#chartLine`)：年份趋势，带半透明面积填充
  - 柱状图 (`#chartBar`)：热点问题Top 10，横向渐变色柱
  - 雷达图 (`#chartRadar`)：五维评分（潜力/证据/新颖度/可验证/论文支撑），Idea下拉选择器

**改动6 — 新增 论文详情页** (第1347-1500行)：
- `renderPaperPage(paperId)`：独立论文详情页，含：
  - 基本信息区（标题/作者/年份/期刊/数据集标签）
  - 问题-方法-效果区（problem_units + method_units + links）
  - 证据链区（evidence quotes with section/role标注）
  - 关联论文推荐（基于Jaccard相似度的4篇推荐卡片）
- `findRelatedPapers(paperId, limit)`：关联推荐算法

**改动7 — 新增 导航事件处理** (第1524-1562行)：
- 全局body click handler：处理返回论文页、导航切换、关联论文点击、paper节点点击打开详情页

**改动8 — 新增 状态恢复与路由** (第1564-1594行)：
- 24小时内浏览状态自动恢复（localStorage读取）
- URL hash路由支持：`#paper=xxx` 和 `?paper=xxx`

---

## 后端API测试结果

所有7个API端点测试通过：

| 端点 | 返回数据 | 状态 |
|------|----------|------|
| `GET /api/health` | `{"status":"healthy","data_loaded":true}` | ✅ |
| `GET /api/status` | 300 papers, 235 core, 60 ideas, 145 problems, 229 methods | ✅ |
| `GET /api/graph/forest` | 60 nodes + 80 links | ✅ |
| `GET /api/graph/root?idea=FI001` | 15 nodes + 16 edges | ✅ |
| `GET /api/trends/hot-topics?limit=3` | Top 3 issues returned | ✅ |
| `GET /api/papers?page=1&page_size=2` | 2 items, total=300 | ✅ |
| `GET /api/ideas/FI001` | score=10.49 | ✅ |

---

## 启动方式

### 后端API

```bash
cd source/backend
pip install flask flask-cors
python app.py --port 5000 --data-root "../../data/idea_graph"
# 访问 http://127.0.0.1:5000/api/health
```

### 前端（两种方式）

```bash
# 方式1：开发模式（前端8765 + 后端5000）
cd source/automation_platform/projects/vmr_idea_dashboard
python -m http.server 8765 --bind 127.0.0.1

# 方式2：生产模式（后端5000统一serve）
python source/backend/app.py --port 5000
# 访问 http://127.0.0.1:5000/
```

---

## 文件结构总览

```
vmr_idea_repro_20260704/
├── docs/                               # [新建] 设计文档
│   ├── 模块设计_可视化展示.md
│   ├── API设计_前端对接.md
│   ├── 数据存储设计_前端部分.md
│   └── 接口层设计.md
├── source/
│   ├── automation_platform/
│   │   └── projects/vmr_idea_dashboard/
│   │       ├── index.html              # [修改] 新增ECharts+导航+容器
│   │       ├── app.js                  # [修改] +438行 仪表盘+论文页+LRU+缓存
│   │       └── styles.css              # [修改] +190行 仪表盘+论文页样式
│   └── backend/                        # [新建] Flask后端
│       ├── app.py                      # Flask入口
│       ├── config.py                   # 配置
│       ├── data_loader.py             # 数据加载
│       ├── middleware/
│       │   └── response.py             # 统一响应格式
│       ├── routes/
│       │   ├── graph.py                # 图谱API
│       │   ├── papers.py               # 论文API
│       │   ├── ideas.py                # Idea API
│       │   ├── trends.py               # 趋势API
│       │   └── system.py               # 系统API
│       └── services/
│           ├── graph_service.py        # 图谱构建
│           ├── paper_service.py        # 论文查询+推荐
│           └── trend_service.py        # 趋势分析
├── CHANGELOG.md                        # [新建] 本文件
└── data/ (unchanged)
    └── idea_graph/                     # 静态JSON数据（无变化）
```
