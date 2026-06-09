# 论文分析平台 - 设计文档

> 创建日期: 2026-05-28  
> 状态: 已确认

## 1. 项目概述

一个基于 MinerU 解析结果的论文分析 Web 应用。上传 MinerU 解析后的 MD + JSON 文件，即可对论文进行总结、深度对话、多论文对比和信息提取。

## 2. 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 后端框架 | FastAPI (async) | Python 异步 Web 框架 |
| 前端框架 | Vue 3 + Vite | 现代前端开发工具链 |
| UI 库 | Element Plus | Vue 3 组件库 |
| 数据库 | MySQL 8.0 | 关系型数据库 |
| ORM | SQLAlchemy 2.0 (async) + asyncmy | 异步数据库操作 |
| 迁移 | Alembic | 数据库版本管理 |
| LLM | openai SDK | 兼容 OpenAI 协议的第三方 API |
| 流式 | sse-starlette | 服务端推送事件 |
| 状态管理 | Pinia | Vue 3 状态管理 |
| Markdown 渲染 | marked + highlight.js | 论文内容展示 |

## 3. 业务域架构

项目采用**业务域分包**结构，每个业务域独立：

```
backend/app/
├── main.py, config.py, database.py, deps.py   # 全局基础设施
├── settings/                                   # 系统设置域
│   └── model.py, schemas.py, crud.py, router.py
├── papers/                                     # 论文业务域（一期）
│   ├── model.py       # SQLAlchemy 模型（4 表）
│   ├── schemas.py     # Pydantic 校验
│   ├── crud.py        # 数据库操作
│   ├── router.py      # API 路由
│   ├── service.py     # LLM 调用逻辑
│   └── utils.py       # 文件解析、prompt 模板、token 处理
└── novels/                                     # 小说域（未来扩展）
    └── ...
```

前端同理：

```
frontend/src/
├── views/papers/          # 论文页面
│   ├── PaperLibrary.vue   # 左侧论文库
│   ├── PaperReader.vue    # 中间阅读区
│   ├── PaperChat.vue      # 右侧对话面板
│   └── api/               # 论文 API 封装
├── router/
├── stores/
└── App.vue
```

## 4. 页面布局

单页三栏布局（论文域）：

```
┌───────────────┬──────────────────────┬──────────────┐
│  论文库       │                      │  总结面板     │
│  (左侧 280px) │    MD 阅读区         │  (右上)      │
│              │    (中间 flex)       │              │
│  · 上传按钮  │                      │  [查看总结]  │
│  · 论文列表  │   渲染 Markdown      │  [生成总结]  │
│  · 搜索/删除 │   论文正文           │              │
│              │                      │  对话面板     │
│              │                      │  (右下)      │
│              │                      │  聊天消息     │
│              │                      │  输入框      │
└───────────────┴──────────────────────┴──────────────┘
```

## 5. 数据库设计

所有表关联到 paper_id，属于 papers 业务域：

```sql
-- 论文主表
papers (
    id          INT AUTO_INCREMENT PK,
    title       VARCHAR(500),
    filename    VARCHAR(500),      -- 原始文件名
    md_path     VARCHAR(1000),     -- MD 文件本地路径
    json_path   VARCHAR(1000),     -- JSON 文件本地路径
    md_content  LONGTEXT,         -- MD 原文内容（方便检索）
    status      VARCHAR(50) DEFAULT 'uploaded',
    created_at  DATETIME DEFAULT NOW()
)

-- 总结记录
summaries (
    id          INT AUTO_INCREMENT PK,
    paper_id    INT FK → papers.id,
    background  TEXT,              -- 背景
    methods     TEXT,              -- 方法
    results     TEXT,              -- 结果
    conclusion  TEXT,              -- 结论
    full_text   LONGTEXT,         -- 完整总结
    model       VARCHAR(100),      -- 使用的模型
    tokens      INT,               -- token 消耗
    created_at  DATETIME DEFAULT NOW()
)

-- 对话记录
conversations (
    id          INT AUTO_INCREMENT PK,
    paper_id    INT FK → papers.id,
    role        VARCHAR(20),       -- user / assistant
    content     TEXT,
    tokens      INT,
    created_at  DATETIME DEFAULT NOW()
)

-- 提取记录
extractions (
    id          INT AUTO_INCREMENT PK,
    paper_id    INT FK → papers.id,
    type        VARCHAR(50),       -- figures / tables / references / formulas
    content     JSON,              -- 结构化提取结果
    created_at  DATETIME DEFAULT NOW()
)

-- 系统设置（全局，非业务域独有）
settings (
    id          INT AUTO_INCREMENT PK,
    key         VARCHAR(100) UNIQUE,
    value       TEXT
)
```

## 6. API 设计

所有论文 API 挂载在 `/api/papers` 下：

| 方法 | 路径 | 说明 | 流式 |
|------|------|------|------|
| `POST` | `/api/papers/upload` | 上传 MD + JSON 文件 | - |
| `GET` | `/api/papers` | 论文列表（分页+搜索） | - |
| `GET` | `/api/papers/{id}` | 论文详情（含 MD 全文） | - |
| `DELETE` | `/api/papers/{id}` | 删除论文及关联数据 | - |
| `POST` | `/api/papers/{id}/summarize` | 生成/重新生成总结 | ✅ SSE |
| `GET` | `/api/papers/{id}/summary` | 获取已有总结 | - |
| `POST` | `/api/papers/{id}/chat` | 发送对话消息 | ✅ SSE |
| `GET` | `/api/papers/{id}/conversations` | 对话历史 | - |
| `POST` | `/api/papers/compare` | 多论文对比 | ✅ SSE |
| `POST` | `/api/papers/{id}/extract` | 提取关键信息 | - |
| `GET` | `/api/papers/{id}/extractions` | 已有提取结果 | - |

系统设置：

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/settings` | 获取所有设置 |
| `PUT` | `/api/settings` | 批量更新设置 |

## 7. LLM 调用策略

### 总结
- 拼接 MD 全文作为 context
- 使用结构化 prompt：背景 → 方法 → 结果 → 结论
- SSE 流式返回，前端逐段渲染

### 对话
- 带历史对话的上下文窗口
- 论文 MD 全文作为 system prompt 注入
- 历史截断策略：保留最近 N 轮 + 论文全文

### 对比（后期）
- 选中多篇论文，拼接各自的总结
- 对比 prompt：方法差异、结果对比、贡献评价

## 8. 功能优先级（一期实现范围）

1. **论文总结** —— 上传后一键生成结构化摘要，SSE 流式展示
2. **深度对话** —— 基于论文全文的多轮问答
3. **多论文对比** —— 选中多篇论文进行横向对比
4. **关键信息提取** —— 提取图表、公式、参考文献

一期完成 1-2，3-4 在界面预留入口。

## 9. 配置项

通过 settings 表 + API 管理，前端提供配置页面：

- `api_base`: LLM API 地址
- `api_key`: API 密钥
- `model`: 模型名称（如 deepseek-chat）
- `max_tokens`: 最大 token 数
- `temperature`: 温度参数

## 10. 非功能需求

- 上传文件限制：单文件 ≤ 50MB，类型 `.md` / `.json`
- 对话历史持久化，切换论文可恢复
- 前端路由：`/papers`（论文库首页）
- CORS 配置允许前端开发服务器跨域

