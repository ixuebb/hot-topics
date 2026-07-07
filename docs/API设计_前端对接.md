# API设计：前端对接

> 系统：基于大模型的科研热点追踪与分析系统（VMR领域）
> 目标：定义前后端对接的全部API接口规范

---

## 目录

1. [规范约定](#规范约定)
2. [图谱数据API](#图谱数据api)
3. [论文API](#论文api)
4. [Idea API（组员A汇总）](#idea-api组员a汇总)
5. [趋势API（组员B汇总）](#趋势api组员b汇总)
6. [系统API](#系统api)
7. [错误码汇总](#错误码汇总)

---

## 规范约定

### 基础URL

```
开发环境: http://127.0.0.1:5000/api
生产环境: https://<domain>/api
```

### 统一响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": { ... },
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 300,
    "total_pages": 15
  }
}
```

### 请求头

```
Content-Type: application/json
Accept: application/json
```

### 分页参数

所有列表类接口统一使用：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码（从1开始） |
| `page_size` | int | 20 | 每页条数（最大100） |

---

## 图谱数据API

### 2.1 获取Idea森林数据

```
GET /api/graph/forest
```

**用途**：获取Idea森林星图的全部节点和连线数据。

**请求参数**：无

**返回示例**：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "nodes": [
      {
        "id": "FI001",
        "title": "面向长视频稀疏证据发现的结构化证据链世界模型",
        "summary": "通过结构化证据链与显式记忆机制...",
        "score": 10.49,
        "evidence": 86,
        "novelty": 78,
        "verifiability": 71,
        "risk": "medium-high",
        "featured": true,
        "target_problem_id": "MP0139",
        "target_problem_name": "Sparse Evidence Discovery in Long Videos",
        "source_method_id": "MM0006",
        "source_method_name": "Structured and Agentic Reasoning",
        "problem_category": "Sparse Evidence / Long Video",
        "method_category": "Structured Reasoning",
        "color_group": "cyan-green",
        "radius": 54.5,
        "x": 760.0,
        "y": 410.0
      }
    ],
    "links": [
      {
        "id": "shared-problem-FI001-FI002",
        "source": "FI001",
        "target": "FI002",
        "type": "shared-problem",
        "strength": 0.82,
        "label": "共享问题: Sparse Evidence"
      }
    ],
    "stats": {
      "total_ideas": 60,
      "total_problems": 145,
      "total_methods": 229,
      "total_papers": 300,
      "core_papers": 255
    }
  }
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `nodes[].id` | string | Idea唯一标识，如 FI001 |
| `nodes[].score` | float | 潜力评分(7.7-10.5) |
| `nodes[].evidence` | int | 证据强度(38-100) |
| `nodes[].novelty` | int | 新颖度评分(58-100) |
| `nodes[].verifiability` | int | 可验证性(55-100) |
| `nodes[].radius` | float | 节点渲染半径 |
| `nodes[].x` / `nodes[].y` | float | 布局坐标(SVG 1600×900坐标系) |
| `links[].type` | string | `shared-problem` 或 `shared-method` |

---

### 2.2 获取树根探索图谱

```
GET /api/graph/root?idea=FI001
```

**用途**：获取指定Idea的层级推理图谱。

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `idea` | string | 是 | Idea ID，如 FI001 |

**返回示例**：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "idea": {
      "id": "FI001",
      "title": "面向长视频稀疏证据发现的结构化证据链世界模型",
      "score": 10.49,
      "trunk": "结构化证据链 + 显式记忆机制...",
      "datasets": "QVHighlights / Charades-STA / ActivityNet Captions / Ego4D-NLQ",
      "risk": "medium-high",
      "evidence_strength": 86,
      "novelty": 78,
      "verifiability": 71
    },
    "nodes": [
      {
        "id": "idea",
        "type": "idea",
        "label": "面向长视频稀疏证据发现的结构化证据链世界模型",
        "detail": "一个从长视频稀疏证据问题中长出的候选研究主张。",
        "x": 800.0,
        "y": 172.0,
        "confidence": 96,
        "size": 1.28
      },
      {
        "id": "p_sparse",
        "type": "problem",
        "label": "长视频中的稀疏证据发现困难",
        "detail": "关键证据在长视频中低频、短暂且容易被平均池化或稀疏采样漏掉。",
        "x": 430.0,
        "y": 425.0,
        "confidence": 92,
        "size": 1.0
      },
      {
        "id": "paper_0",
        "type": "paper",
        "label": "Unleashing the Potential of Multimodal LLMs...",
        "detail": "2025 · arXiv",
        "x": 170.0,
        "y": 840.0,
        "confidence": 75,
        "size": 1.0,
        "paper_id": "2025_yang_unleashing_...",
        "evidence": [
          {
            "quote": "they typically require explicit fine-tuning of MLLMs...",
            "section": "Introduction",
            "role": "limitation"
          }
        ]
      }
    ],
    "edges": [
      {
        "id": "idea->trunk",
        "source": "idea",
        "target": "trunk",
        "type": "claim",
        "strength": 1.0,
        "label": "核心主张"
      }
    ]
  }
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `nodes[].type` | string | `idea` / `trunk` / `problem` / `failure` / `method` / `paper` |
| `nodes[].confidence` | int | 置信度(0-100)，控制节点是否出现在"高置信度"过滤中 |
| `nodes[].size` | float | 节点尺寸系数 |
| `nodes[].paper_id` | string | 仅paper节点有，关联到论文详情 |
| `edges[].type` | string | `claim` / `root` / `cause` / `cross-cause` / `transfer` / `evidence` / `shared-mechanism` |

---

## 论文API

### 3.1 获取论文列表

```
GET /api/papers
```

**请求参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码 |
| `page_size` | int | 20 | 每页条数 |
| `year` | int | — | 按年份筛选，如 `2024` |
| `sort` | string | `year_desc` | 排序：`year_desc` / `year_asc` / `title` |
| `keyword` | string | — | 标题/摘要搜索关键词 |
| `task_scope` | string | — | 按任务范围筛选：`core` / `adjacent` / `all` |
| `problem_category` | string | — | 按问题族筛选 |

**返回示例**：

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "paper_id": "2026_yu_mamba-based-modulated-fusion-model-for-video-moment-retrieval_d99dbf0e60",
      "title": "Mamba-based modulated fusion model for video moment retrieval",
      "year": 2026,
      "venue_or_source": "arXiv",
      "authors": ["Yu X", "Wang Y", "Zhang Z"],
      "task_scope": {
        "primary_task": "Video Moment Retrieval",
        "is_core_video_moment_retrieval": true
      },
      "datasets": ["QVHighlights", "Charades-STA"],
      "metrics": ["R@1", "mIoU"],
      "problem_units_count": 3,
      "method_units_count": 2,
      "abstract_snippet": "Video moment retrieval aims to..."
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 300,
    "total_pages": 15
  }
}
```

---

### 3.2 获取论文详情

```
GET /api/papers/{paper_id}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `paper_id` | string | 是 | 论文ID，如 `2026_yu_mamba-based-...` |

**返回示例**：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "paper_id": "2026_yu_mamba-based-modulated-fusion-model-for-video-moment-retrieval_d99dbf0e60",
    "title": "Mamba-based modulated fusion model for video moment retrieval",
    "year": 2026,
    "venue_or_source": "arXiv",
    "authors": ["Yu X", "Wang Y", "Zhang Z"],
    "abstract": "Video moment retrieval aims to... (完整摘要)",
    "introduction": "(完整引言)",
    "task_scope": {
      "primary_task": "Video Moment Retrieval",
      "task_family": "video moment retrieval / video temporal grounding",
      "is_core_video_moment_retrieval": true,
      "is_adjacent_only": false
    },
    "datasets": ["QVHighlights", "Charades-STA"],
    "metrics": ["R@1", "mIoU", "Recall"],
    "problem_units": [
      {
        "problem_unit_id": "PU1",
        "macro_problem_id": "EP008",
        "macro_problem_name": "Boundary Structure and Temporal Precision",
        "name": "Boundary precision degradation in long videos",
        "evidence": [
          { "quote": "...", "section": "Introduction", "page": 1 }
        ]
      }
    ],
    "method_units": [
      {
        "method_unit_id": "MU1",
        "macro_method_id": "EM003",
        "macro_method_name": "Structured and Agentic Reasoning",
        "name": "Mamba-based temporal state space modeling",
        "evidence": [
          { "quote": "We propose MambaFusion...", "section": "Method", "page": 3 }
        ]
      }
    ],
    "problem_method_links": [
      {
        "problem_unit_id": "PU1",
        "method_unit_id": "MU1",
        "solves_how": "Mamba state space model captures long-range temporal dependencies..."
      }
    ],
    "intro_motivation_chain": {
      "background_setup": [{"summary": "...", "evidence": [...]}],
      "prior_work_limitation": [{"summary": "...", "evidence": [...]}],
      "core_problem_transition": [{"summary": "...", "evidence": [...]}],
      "method_transition": [{"summary": "...", "evidence": [...]}]
    },
    "figures": [
      {"src": "./paper_assets/.../figure_001.png", "caption": "Architecture overview"}
    ],
    "tables": [
      {"src": "./paper_assets/.../table_001.csv", "caption": "Main results on QVHighlights"}
    ],
    "related_papers": [
      {
        "paper_id": "2024_zhang_xxx",
        "title": "...",
        "year": 2024,
        "relation_type": "共享方法",
        "shared_units": ["Mamba-based sequential modeling"]
      }
    ]
  }
}
```

---

### 3.3 获取论文关联推荐

```
GET /api/papers/{paper_id}/related
```

**请求参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `limit` | int | 4 | 返回推荐数量 |

**返回示例**：

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "paper_id": "2024_zhang_xxx",
      "title": "Relation-aware Video Grounding...",
      "year": 2024,
      "venue_or_source": "CVPR 2024",
      "relation_type": "共享方法",
      "similarity": 0.78,
      "shared_units": ["Mamba-based modeling", "Cross-modal fusion"]
    }
  ]
}
```

**推荐算法**：
1. 取当前论文的 `problem_units[].macro_problem_id` 和 `method_units[].macro_method_id`
2. 在全部论文中按 Jaccard 相似度计算：`|A ∩ B| / |A ∪ B|`
3. 排除当前论文自身，按相似度降序，取 `limit` 条

---

## Idea API（组员A汇总）

### 4.1 获取Idea列表

```
GET /api/ideas
```

**请求参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码 |
| `page_size` | int | 20 | 每页条数 |
| `sort` | string | `score_desc` | `score_desc` / `score_asc` / `novelty_desc` |
| `risk_level` | string | — | 按风险等级筛选：`medium` / `medium-high` |
| `problem_category` | string | — | 按目标问题族筛选 |

**返回示例**：

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "idea_id": "FI001",
      "title": "面向长视频稀疏证据发现的结构化证据链世界模型",
      "score": 10.49,
      "evidence": 86,
      "novelty": 78,
      "verifiability": 71,
      "risk_level": "medium-high",
      "target_problem": "Sparse Evidence Discovery in Long Videos",
      "source_method": "Structured and Agentic Reasoning",
      "is_cross_task_transfer": true,
      "summary": "通过结构化证据链与显式记忆机制..."
    }
  ],
  "pagination": { "page": 1, "page_size": 20, "total": 60, "total_pages": 3 }
}
```

### 4.2 获取单个Idea详情

```
GET /api/ideas/{idea_id}
```

**返回示例**：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "idea_id": "FI001",
    "score": 10.49,
    "target_micro_problem_id": "MP0139",
    "target_micro_problem": "Sparse Evidence Discovery in Long Videos",
    "source_micro_method_id": "MM0006",
    "source_micro_method": "Structured and Agentic Reasoning",
    "shared_failure_mode": "reasoning can organize evidence selection over long videos",
    "transferable_mechanism": "SMORE framework...",
    "why_currently_underused": "0 direct problem-method links",
    "candidate_idea": "Structured and Agentic Reasoning for Sparse Evidence",
    "technical_sketch": "Instrument the target baseline...",
    "minimum_verification_experiment": "Use Unleashing the Potential of MLLMs on QVHighlights...",
    "expected_gain": "Better localization on sparse evidence cases",
    "reviewer_attack_points": [
      {
        "risk": "Novelty may look like direct module transplantation.",
        "mitigation": "Define the shared failure variable and compare against a naive plug-in baseline."
      }
    ],
    "risk_level": "medium-high",
    "is_cross_task_transfer": true,
    "source_papers": [{ "paper_id": "...", "title": "...", "year": 2026 }],
    "target_papers": [{ "paper_id": "...", "title": "...", "year": 2025 }],
    "full_data": { "...": "完整的raw对象，包含所有原始字段" }
  }
}
```

---

## 趋势API（组员B汇总）

### 5.1 获取热点问题排名

```
GET /api/trends/hot-topics
```

**请求参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `limit` | int | 10 | 返回排名数量 |
| `category` | string | — | 按问题族筛选 |
| `year` | int | — | 按年份过滤论文 |

**返回示例**：

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "rank": 1,
      "problem_id": "MP0003",
      "problem_name": "Weak Supervision: Retrieval / Moment",
      "paper_count": 16,
      "paper_count_by_year": { "2021": 4, "2022": 4, "2024": 11 },
      "trend": "rising",
      "macro_category": "Weak Supervision and Annotation Reliability"
    }
  ]
}
```

### 5.2 获取时间趋势数据

```
GET /api/trends/temporal
```

**请求参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `granularity` | string | `year` | 时间粒度：`year` |
| `start_year` | int | 2021 | 起始年份 |
| `end_year` | int | 2026 | 结束年份 |
| `problem_category` | string | — | 按问题族筛选 |

**返回示例**：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "labels": ["2021", "2022", "2023", "2024", "2025", "2026"],
    "total": [35, 43, 49, 92, 12, 69],
    "by_category": {
      "Weak Supervision": [8, 10, 12, 22, 3, 16],
      "Sparse Evidence": [5, 7, 8, 18, 2, 14]
    },
    "growth_rate": {
      "2021-2022": 0.23,
      "2022-2023": 0.14,
      "2023-2024": 0.88,
      "2024-2025": -0.87,
      "2025-2026": 4.75
    }
  }
}
```

---

## 系统API

### 6.1 获取系统状态

```
GET /api/status
```

**返回示例**：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "paper_count": 300,
    "core_papers": 255,
    "adjacent_papers": 45,
    "idea_count": 60,
    "problem_count": 145,
    "method_count": 229,
    "last_updated": "2026-06-27T18:28:00Z",
    "data_version": "finegrained-20260619"
  }
}
```

### 6.2 健康检查

```
GET /api/health
```

**返回示例**：

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "status": "healthy",
    "uptime_seconds": 3600,
    "data_loaded": true
  }
}
```

---

## 错误码汇总

| 错误码 | HTTP状态码 | 说明 |
|--------|-----------|------|
| 200 | 200 | 成功 |
| 400 | 400 | 请求参数错误（如 `page=-1`） |
| 401 | 401 | 未认证（预留，当前不需要） |
| 403 | 403 | 无权限（预留） |
| 404 | 404 | 资源不存在（如 `idea=FI999`） |
| 422 | 422 | 请求格式正确但语义错误 |
| 429 | 429 | 请求频率超限 |
| 500 | 500 | 服务器内部错误 |
| 503 | 503 | 服务不可用（如数据未加载完成） |

**错误返回格式**：

```json
{
  "code": 404,
  "message": "Idea not found: FI999",
  "data": null,
  "error": {
    "type": "NOT_FOUND",
    "detail": "No idea with id 'FI999' in the database. Valid range: FI001-FI060."
  }
}
```

---

## API路由汇总表

| 方法 | 路径 | 用途 | 设计方 |
|------|------|------|--------|
| GET | `/api/graph/forest` | Idea森林图数据 | T4(前端) |
| GET | `/api/graph/root` | 树根探索图谱 | T4(前端) |
| GET | `/api/papers` | 论文列表 | T4(前端) |
| GET | `/api/papers/{id}` | 论文详情 | T4(前端) |
| GET | `/api/papers/{id}/related` | 论文关联推荐 | T4(前端) |
| GET | `/api/ideas` | Idea列表 | 组员A |
| GET | `/api/ideas/{id}` | Idea详情 | 组员A |
| GET | `/api/trends/hot-topics` | 热点排名 | 组员B |
| GET | `/api/trends/temporal` | 时间趋势 | 组员B |
| GET | `/api/status` | 系统状态 | T4(前端) |
| GET | `/api/health` | 健康检查 | T4(前端) |
