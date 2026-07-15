# 论文知识库分析系统 — 项目状态

## 技术栈
- 前端: Vue 3 + Vite + Element Plus + Pinia (端口 5173)
- 后端: FastAPI + SQLAlchemy async + MySQL (端口 8000)
- 解析: MinerU API (PDF → Markdown)
- 向量检索: ChromaDB + sentence-transformers
- LLM: DeepSeek API (OpenAI 兼容)
- 数学渲染: KaTeX + markdown-it

## 项目结构
```
C:\myweb\
├── frontend/src/
│   ├── api/chat.js          # SSE 流式解析 (JSON.decode)
│   ├── api/papers.js        # 论文 CRUD
│   ├── utils/marked-setup.js # markdown-it + KaTeX 渲染
│   ├── views/papers/
│   │   ├── PaperLayout.vue   # 主布局 (上传/解析/总结流)
│   │   ├── PaperLibrary.vue  # 论文列表
│   │   ├── PaperReader.vue   # PDF 阅读 + 标签
│   │   └── PaperChat.vue     # 论文对话 (流式 + 渲染)
│   └── views/GlobalQA.vue    # 全局问答
├── backend/app/
│   ├── papers/router.py      # 论文/总结/解析 API
│   ├── papers/service.py     # LLM 调用 + 总结流
│   ├── qa/chat_router.py     # 对话 + 全局问答 SSE
│   ├── qa/router.py          # _rewrite_query, _build_qa_prompt
│   └── qa/indexer.py         # ChromaDB 切片索引
```

## 关键修复记录 (2026-07-16)

### SSE 换行丢失
- 问题: LLM token 含 `\n` 时被 SSE 协议吃掉，markdown 无法解析
- 修复: 后端 `json.dumps(token)` → 前端 `JSON.parse(raw)`
- 涉及: chat_router.py (4处), router.py (summarize), chat.js, PaperLayout.vue

### Markdown 渲染时序
- 问题: `streamLoading=false` 先于 `push` 导致 v-html 未重算
- 修复: onDone 回调改为先 push → await nextTick → 再关 streamLoading
- 涉及: PaperChat.vue, GlobalQA.vue

### switchSession 双重渲染
- 问题: 加载历史消息时预渲染 HTML，模板又调用 renderMarkdown(HTML)
- 修复: 去掉预渲染，统一存原始 markdown
- 涉及: PaperChat.vue

### 全局问答虚构论文
- 问题: _rewrite_query 返回 NOT_RELEVANT 跳过检索，LLM 编造 Paper A/B
- 修复: 去掉 NOT_RELEVANT 闸门；无检索结果时返回提示而非编造
- 涉及: chat_router.py

## 当前数据流
1. 上传 PDF → POST /api/papers/upload
2. MinerU 解析 → POST /api/papers/{id}/parse (SSE 进度)
3. 解析完成 → POST /api/papers/{id}/summarize (SSE 流式总结)
4. 论文对话 → POST /api/chat/sessions/{id}/send (SSE 流式)
5. 全局问答 → 同上 (paper_id=null, kb_id=xxx)

## 环境
- 数据库: MySQL root:1234@127.0.0.1:3306/paper_analysis
- 虚拟环境: backend\.venv
- 启动后端: cd backend && .venv\Scripts\activate && uvicorn app.main:app --port 8000
- 启动前端: cd frontend && npm run dev

## 未处理
- 全局问答无独立「参考论文」展示区（仅 LLM 内联引用）
- 无端到端自动化测试
- 上传重复检测逻辑已改：排除 rejected，pending 时自动替换

## LaTeX 渲染注意事项
- KaTeX 不支持 `\text` 等复杂命令，需在 renderMarkdown 中用 throwOnError: false 降级
- CSS: katex/dist/katex.min.css 在 main.js 中导入
