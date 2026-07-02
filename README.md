# 📄 Paper Analyzer — 论文分析系统

基于 AI 的论文学术助手，上传 PDF 后自动调用 MinerU 解析为 Markdown，支持 AI 总结、对话问答、文件夹管理与标签分类。

## ✨ 功能

- **📤 PDF 上传** — 拖拽或点击上传 PDF，自动按文件夹归类
- **🔬 MinerU 解析** — 自动调用 MinerU v4 API 解析 PDF 为结构化 Markdown，支持流式进度展示
- **🤖 AI 自动总结** — 解析完成后自动生成结构化总结（解决的问题、结论、工况表格）
- **💬 论文对话** — 基于论文全文的 AI 问答，流式输出，上下文感知
- **📁 文件夹管理** — 三级目录结构，拖拽移动论文到不同文件夹
- **🏷️ 标签系统** — 自定义标签，支持搜索筛选，论文快速打标
- **📋 复制/下载** — 总结内容一键复制 Markdown 或下载为 .md 文件
- **⚙️ 可视化配置** — 界面内直接配置 LLM API 参数，无需手动编辑 .env
- **🎨 浅色极简风** — CSS Variables 设计系统，Element Plus 全局定制

## 🏗️ 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Vue 3 + Vite + Element Plus + Pinia + Axios |
| 后端 | FastAPI + SQLAlchemy (async) + MySQL |
| AI | OpenAI 兼容 API（流式 SSE） |
| PDF 解析 | MinerU v4 Batch Upload API |
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

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

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
│   │   ├── papers/       # 论文 CRUD、MinerU 解析、总结、对话
│   │   │   ├── crud.py   # 数据库操作（文件夹/标签/论文/摘要/对话）
│   │   │   ├── mineru.py # MinerU v4 流式解析服务
│   │   │   ├── model.py  # SQLAlchemy 数据模型
│   │   │   ├── router.py # API 路由（上传/解析/总结/对话/对比/提取）
│   │   │   ├── schemas.py# Pydantic 请求/响应模型
│   │   │   ├── service.py# LLM 调用服务
│   │   │   └── utils.py  # 提示词模板与工具函数
│   │   ├── settings/     # 系统设置 CRUD
│   │   ├── config.py     # 环境变量与配置管理
│   │   ├── database.py   # 异步数据库连接
│   │   ├── deps.py       # FastAPI 依赖注入
│   │   └── main.py       # 应用入口与路由注册
│   └── run.py            # uvicorn 启动脚本
├── frontend/
│   └── src/
│       ├── views/papers/  # PaperLayout / PaperLibrary / PaperReader / PaperChat / FolderTreeItem
│       ├── views/settings/# SettingsDialog
│       ├── stores/        # Pinia 状态管理
│       ├── api/           # Axios API 封装
│       ├── utils/         # Markdown 渲染
│       └── router/        # Vue Router
└── docs/                  # 设计文档与计划
```

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
| `MINERU_BATCH_URL` | MinerU 批量上传地址 | `https://mineru.net/api/v4/file-urls/batch` |
| `MINERU_RESULT_URL` | MinerU 结果查询地址 | `https://mineru.net/api/v4/extract-results/batch` |
| `MINERU_MODEL_VERSION` | MinerU 模型版本 | `vlm` |
| `MINERU_POLL_INTERVAL` | 轮询间隔（秒） | `5.0` |
| `MINERU_POLL_MAX_RETRIES` | 最大轮询次数 | `60` |
| `UPLOAD_DIR` | 上传文件存储目录 | `uploads` |

## 📄 License

MIT