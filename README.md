# 📄 PaperMind — AI 论文分析系统

基于 AI 的论文学术助手，上传 PDF 后自动调用 MinerU 解析为 Markdown 并入库，支持 AI 总结、多轮对话问答（RAG 检索增强）、全局知识库问答（含学术引用来标注）、文件夹管理与标签分类。

## ✨ 功能

- **📤 PDF 上传与解析** — 拖拽上传 PDF，自动调用 MinerU v4 API 解析为结构化 Markdown，流式进度展示，解析完成后直接入库
- **🤖 AI 自动总结** — 解析完成后自动生成结构化总结（解决的问题、结论、工况表格），支持重新生成
- **💬 论文对话** — 基于论文全文的多轮 AI 问答，流式输出，支持多会话管理（新建/切换/删除对话历史）
- **🌐 全局问答** — 基于所有论文知识库的 RAG 检索增强问答，向量语义搜索 + LLM 综合回答，回答中使用学术引用 [1][2] 标注来源编号
- **📚 参考来源展示** — 每条 AI 回答底部自动展示引用论文列表，编号与文中标注一一对应
- **📝 会话管理** — 论文对话和全局问答均支持多会话，对话历史持久化到数据库，可随时继续
- **📁 文件夹管理** — 三级目录结构，拖拽移动论文到不同文件夹
- **🏷️ 标签系统** — 自定义标签，支持搜索筛选
- **📋 复制/下载** — 总结内容一键复制或下载为 Markdown 文件
- **⚙️ 可视化配置** — 界面内直接配置 LLM API 参数，无需手动编辑配置文件

## 🏗️ 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Vue 3 + Vite + Element Plus + Pinia + Axios |
| 后端 | FastAPI + SQLAlchemy (async) + MySQL |
| AI | OpenAI 兼容 API（流式 SSE），支持多轮对话上下文 |
| PDF 解析 | MinerU v4 Batch Upload API |
| 向量检索 | Kraken (ChromaDB) + BGE 中文 Embedding |
| 样式 | Scoped CSS + CSS Variables 浅色主题 |

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0+

### 1. 后端

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（创建 .env 文件）
echo LLM_API_KEY=sk-your-key > .env
echo LLM_API_BASE=https://api.deepseek.com >> .env
echo LLM_MODEL=deepseek-chat >> .env
echo DATABASE_URL=mysql+asyncmy://root:password@127.0.0.1:3306/paper_analysis >> .env
echo MINERU_API_TOKEN=your-mineru-token >> .env

# 启动
python run.py
```

### 2. 前端

```bash
cd frontend

npm install
npm run dev
```

访问 http://localhost:5173

## 📁 项目结构

```
├── backend/
│   ├── app/
│   │   ├── papers/          # 论文 CRUD、MinerU 解析、总结
│   │   │   ├── crud.py      # 数据库操作（文件夹/标签/论文/摘要）
│   │   │   ├── mineru.py    # MinerU v4 流式解析服务
│   │   │   ├── model.py     # SQLAlchemy 数据模型
│   │   │   ├── router.py    # API 路由（上传/解析/总结/对比/提取）
│   │   │   ├── schemas.py   # Pydantic 请求/响应模型
│   │   │   ├── service.py   # LLM 调用服务
│   │   │   └── utils.py     # 提示词模板与工具函数
│   │   ├── qa/              # 问答与聊天系统
│   │   │   ├── chat_crud.py # 会话与消息 CRUD
│   │   │   ├── chat_router.py # 会话 API（列表/创建/删除/流式消息）
│   │   │   ├── chat_schemas.py # 会话 Pydantic 模型
│   │   │   ├── embedder.py  # BGE 中文 Embedding 服务
│   │   │   ├── indexer.py   # ChromaDB 向量索引管理
│   │   │   ├── router.py    # QA 路由（索引重建）
│   │   │   └── schemas.py   # QA 请求/响应模型
│   │   ├── settings/        # 系统设置 CRUD
│   │   ├── config.py        # 环境变量与配置管理
│   │   ├── database.py      # 异步数据库连接
│   │   ├── deps.py          # FastAPI 依赖注入
│   │   └── main.py          # 应用入口与路由注册
│   └── run.py               # uvicorn 启动脚本
├── frontend/
│   └── src/
│       ├── views/papers/     # PaperLayout / PaperLibrary / PaperReader / PaperChat
│       ├── views/settings/   # SettingsDialog
│       ├── views/GlobalQA.vue # 全局问答页面
│       ├── stores/           # Pinia 状态管理
│       ├── api/              # Axios API 封装（papers / qa / chat / settings）
│       ├── utils/            # Markdown 渲染 (markdown-it + KaTeX)
│       └── router/           # Vue Router
└── docs/                     # 设计文档
```

## 🔌 API 概览

| 模块 | 端点 | 说明 |
|------|------|------|
| 论文 | `POST /api/papers/upload` | 上传 PDF |
| 论文 | `POST /api/papers/{id}/parse` | 触发 MinerU 解析（SSE 流） |
| 论文 | `POST /api/papers/{id}/summarize` | AI 总结（SSE 流） |
| 论文 | `GET /api/papers/{id}/summary` | 获取已缓存的总结 |
| 聊天 | `GET /api/chat/sessions` | 列出会话（支持 paper_id 筛选） |
| 聊天 | `POST /api/chat/sessions` | 创建新会话 |
| 聊天 | `DELETE /api/chat/sessions/{id}` | 删除会话 |
| 聊天 | `GET /api/chat/sessions/{id}/messages` | 获取历史消息 |
| 聊天 | `POST /api/chat/sessions/{id}/send` | 发送消息（SSE 流式回复） |
| QA | `POST /api/qa/rebuild` | 重建向量索引 |
| 设置 | `GET/POST /api/settings` | 系统配置管理 |

## 🔧 配置项

在 `.env` 或系统设置页面中配置：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_API_KEY` | LLM API 密钥 | - |
| `LLM_API_BASE` | LLM API 地址 | `https://api.deepseek.com` |
| `LLM_MODEL` | 模型名称 | `deepseek-chat` |
| `LLM_MAX_TOKENS` | 最大 Token | `4096` |
| `LLM_TEMPERATURE` | 温度参数 | `0.7` |
| `DATABASE_URL` | MySQL 连接串 | - |
| `MINERU_API_TOKEN` | MinerU API Token | - |
| `CHROMA_PERSIST_DIR` | 向量索引存储目录 | `chroma_data` |
| `UPLOAD_DIR` | 上传文件存储目录 | `uploads` |

## 📄 License

MIT
