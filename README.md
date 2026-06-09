# 📄 Paper Analyzer — 论文分析系统

基于 AI 的论文学术助手，支持 PDF/Markdown 上传、AI 自动总结、论文对话问答，以及文件夹管理与标签分类。

## ✨ 功能

- **📤 论文上传** — 支持 PDF 原文 + Markdown 文件上传，按文件夹归类
- **🤖 AI 自动总结** — 上传后自动生成结构化总结（解决的问题、结论、工况表格）
- **💬 论文对话** — 基于论文全文的 AI 问答，支持流式输出
- **📁 文件夹管理** — 三级目录结构，拖拽移动论文到不同文件夹
- **🏷️ 标签系统** — 自定义标签，支持按标签搜索筛选
- **📋 复制/下载** — 总结内容一键复制 Markdown 或下载为 .md 文件
- **🎨 浅色极简风** — 现代化的 ChatGPT 风格 UI

## 🏗️ 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Vue 3 + Vite + Element Plus + Pinia |
| 后端 | FastAPI + SQLAlchemy (async) + MySQL |
| AI | OpenAI 兼容 API（流式 SSE） |
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
echo LLM_API_KEY=your-api-key > .env
echo LLM_API_BASE=https://api.openai.com/v1 >> .env
echo LLM_MODEL=gpt-4o >> .env
echo DATABASE_URL=mysql+asyncmy://root:password@localhost:3306/paper_analyzer >> .env

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
│   │   ├── papers/       # 论文 CRUD、总结、对话
│   │   ├── settings/     # 系统设置
│   │   ├── config.py     # 配置管理
│   │   ├── database.py   # 数据库连接
│   │   └── main.py       # FastAPI 入口
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── views/papers/  # PaperLibrary / PaperReader / PaperChat
│       ├── stores/        # Pinia 状态管理
│       ├── api/           # Axios API 封装
│       └── router/        # Vue Router
└── docs/                  # 设计文档与计划
```

## 🔧 配置项

在 `.env` 或系统设置页面中配置：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_API_KEY` | LLM API 密钥 | - |
| `LLM_API_BASE` | LLM API 地址 | `https://api.openai.com/v1` |
| `LLM_MODEL` | 模型名称 | `gpt-4o` |
| `LLM_MAX_TOKENS` | 最大 Token | `4096` |
| `LLM_TEMPERATURE` | 温度参数 | `0.7` |
| `DATABASE_URL` | MySQL 连接串 | - |

## 📄 License

MIT
