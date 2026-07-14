# 独立知识库功能 - 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 PaperMind 引入知识库概念，支持共享库（需审核）和个人库（隔离），保留现有数据。

**Architecture:** 新增 `knowledge_bases` 表，papers/folders/tags/chat_sessions 添加 `kb_id` 外键。ChromaDB 每个 KB 独立目录。前端新增 KB 选择器和审核管理页。

**Tech Stack:** FastAPI + SQLAlchemy + MySQL + ChromaDB + Vue 3 + Element Plus

---

## 文件清单

### 后端 - 修改
- `backend/app/papers/model.py` - 新增 KnowledgeBase，修改 Paper/Folder/Tag/ChatSession
- `backend/app/papers/schemas.py` - 新增 KB schemas，更新现有 schemas
- `backend/app/papers/crud.py` - KB CRUD + 所有函数加 kb_id 过滤
- `backend/app/papers/router.py` - KB router + papers 接口加 kb_id + admin review 接口
- `backend/app/main.py` - 注册 KB router 和 admin router
- `backend/app/qa/indexer.py` - ChromaDB 按 KB 隔离
- `backend/app/qa/router.py` - QA 接口加 kb_id
- `backend/app/qa/chat_router.py` - Chat 接口加 kb_id
- `backend/app/qa/chat_crud.py` - Chat CRUD 加 kb_id
- `backend/app/qa/chat_schemas.py` - Chat schemas 加 kb_id

### 前端 - 新建
- `frontend/src/api/knowledgeBases.js` - KB API 封装
- `frontend/src/stores/knowledgeBase.js` - KB Pinia store
- `frontend/src/api/admin.js` - 审核 API 封装
- `frontend/src/views/admin/ReviewPage.vue` - 审核管理页

### 前端 - 修改
- `frontend/src/api/papers.js` - 接口加 kb_id 参数
- `frontend/src/api/qa.js` - rebuildIndex 加 kb_id
- `frontend/src/api/chat.js` - 会话接口加 kb_id
- `frontend/src/stores/papers.js` - 加 kbId 状态
- `frontend/src/views/papers/PaperLayout.vue` - KB 选择器 + 管理弹窗 + 审核入口
- `frontend/src/views/papers/PaperLibrary.vue` - 接收 kbId，文件夹操作传 kb_id
- `frontend/src/views/GlobalQA.vue` - KB 选择器
- `frontend/src/router/index.js` - 添加 /admin/review 路由

---

### Task 1: 数据库模型变更

**Files:** Modify `backend/app/papers/model.py`

**需要在文件顶部 imports 中加入 `Boolean`：**
```python
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, func, Table, UniqueConstraint
```

- [ ] **Step 1: 新增 KnowledgeBase 模型**

在 `paper_tags = Table(...)` 之后、`class Folder(Base):` 之前插入：

```python
class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(String(32), primary_key=True, default=_new_uuid)
    name = Column(String(200), nullable=False)
    description = Column(String(1000), default="")
    user_id = Column(String(32), nullable=True, default=None, index=True)
    is_shared = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
```

- [ ] **Step 2: 修改 Folder 模型**

唯一约束改为 `UniqueConstraint("name", "parent_id", "knowledge_base_id", name="uq_folder_name_parent_kb")`
新增字段：`knowledge_base_id = Column(String(32), nullable=False, index=True)`

- [ ] **Step 3: 修改 Tag 模型**

唯一约束改为 `UniqueConstraint("name", "knowledge_base_id", name="uq_tag_name_kb")`（去掉 `name` 上的 `unique=True`）
新增字段：`knowledge_base_id = Column(String(32), nullable=False, index=True)`

- [ ] **Step 4: 修改 Paper 模型**

在 `folder_id` 之后新增：
```python
knowledge_base_id = Column(String(32), nullable=False, index=True)
review_status = Column(String(20), default="none")
file_md5 = Column(String(32), default="")
reviewed_at = Column(DateTime, nullable=True, default=None)
review_comment = Column(String(500), default="")
```

- [ ] **Step 5: 修改 ChatSession 模型**

在 `paper_id` 之后新增：
```python
knowledge_base_id = Column(String(32), nullable=True, default=None, index=True)
```

- [ ] **Step 6: 语法检查**

Run: `cd backend && .venv\Scripts\python.exe -c "import py_compile; py_compile.compile('app/papers/model.py', doraise=True); print('OK')"`
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add backend/app/papers/model.py
git commit -m "feat: 新增 KnowledgeBase 模型，papers/folders/tags/chat_sessions 加 kb_id"
```

---

### Task 2: 数据库迁移脚本

**Files:** Create then delete `backend/migrate_kb.py`

- [ ] **Step 1: 创建并运行迁移脚本**

脚本内容：
1. 给 `papers`, `folders`, `tags`, `chat_sessions` 加 `knowledge_base_id` 列
2. 给 `papers` 加 `review_status`, `file_md5`, `reviewed_at`, `review_comment`
3. 创建 `knowledge_bases` 表
4. 插入共享库记录（is_shared=true, user_id=NULL）
5. 将所有现有 papers/folders/tags 的 kb_id 设为共享库 ID
6. 现有 papers 的 review_status 设为 "approved"
7. 更新 folders 唯一约束（drop 旧的，加新的）
8. 更新 tags 唯一约束（drop name，加 name+kb_id）

Run: `cd backend && .venv\Scripts\python.exe migrate_kb.py`
Expected: 每步输出成功信息，输出共享库 ID

- [ ] **Step 2: 删除迁移脚本**

Run: `Remove-Item backend\migrate_kb.py`

- [ ] **Step 3: Commit**

```bash
git add backend/app/papers/model.py
git commit -m "feat: 数据库迁移，现有数据归入共享库"
```

---

### Task 3: KB Schemas 更新

**Files:** Modify `backend/app/papers/schemas.py`

- [ ] **Step 1: 新增 KB 相关 schemas**

```python
class KnowledgeBaseCreate(BaseModel): name: str; description: str = ""
class KnowledgeBaseUpdate(BaseModel): name: str | None = None; description: str | None = None
class KnowledgeBaseResponse(BaseModel): id, name, description, user_id, is_shared, paper_count, created_at
```

- [ ] **Step 2: FolderCreate 加 `knowledge_base_id: str`**
- [ ] **Step 3: FolderResponse 加 `knowledge_base_id: str | None = None`**
- [ ] **Step 4: PaperResponse 加 `knowledge_base_id`, `review_status`, `file_md5`, `review_comment`**
- [ ] **Step 5: 新增 `ReviewRejectRequest(comment: str)`, `ReviewPaperItem`, `ReviewListResponse`**
- [ ] **Step 6: 语法检查** `py_compile`
- [ ] **Step 7: Commit** `git commit -m "feat: KB 和审核相关 schemas"`

---

### Task 4: KB + 审核 CRUD

**Files:** Modify `backend/app/papers/crud.py`

在顶部导入加 `ChatSession`：`from app.papers.model import Paper, Folder, Tag, KnowledgeBase, paper_tags, Summary, Conversation, Extraction, ChatSession`

- [ ] **Step 1: `get_knowledge_bases(db, user_id)` — 返回共享库 + 该用户的私有库**
- [ ] **Step 2: `create_knowledge_base(db, name, description, user_id)` — 创建私有库**
- [ ] **Step 3: `update_knowledge_base(db, kb_id, name, description)` — 更新名称/描述**
- [ ] **Step 4: `delete_knowledge_base(db, kb_id)` — 删除 KB 及级联内容（共享库不可删）**
- [ ] **Step 5: `get_folders(db, kb_id)` — 按 KB 查文件夹**
- [ ] **Step 6: `create_folder(db, name, parent_id, kb_id)` — 加 kb_id 参数**
- [ ] **Step 7: `get_papers(db, kb_id, ...)` — 加 `Paper.knowledge_base_id == kb_id` 过滤**
- [ ] **Step 8: `create_paper(db, ..., kb_id)` — 加 kb_id 参数**
- [ ] **Step 9: `get_tags(db, kb_id)` / `create_tag(db, name, kb_id)` — 按 kb_id 隔离**
- [ ] **Step 10: `get_pending_papers(db, kb_id)` — 查待审核论文，含标题模糊去重检测**
- [ ] **Step 11: `_title_similar(a, b)` — difflib.SequenceMatcher，阈值 0.85**
- [ ] **Step 12: `approve_paper(db, paper_id)` — 状态改为 approved**
- [ ] **Step 13: `reject_paper(db, paper_id, comment)` — 状态改为 rejected + 保存原因**
- [ ] **Step 14: `paper_to_response` 输出加 `knowledge_base_id`, `review_status`, `file_md5`, `review_comment`**
- [ ] **Step 15: `delete_paper` / `delete_folder` 传 kb_id 给 `indexer.delete_paper_index`**
- [ ] **Step 16: 语法检查**
- [ ] **Step 17: Commit** `git commit -m "feat: KB CRUD + 审核 CRUD + kb_id 隔离"`

---

### Task 5: KB + 审核路由

**Files:** Modify `backend/app/papers/router.py`, `backend/app/main.py`

- [ ] **Step 1: router.py 顶部加 `from sqlalchemy import select, func` 和 `DEFAULT_USER_ID = "default_user"`**
- [ ] **Step 2: 新增 `kb_router`（prefix=/api/knowledge-bases）— GET/POST/PUT/DELETE**
- [ ] **Step 3: 新增 `admin_router`（prefix=/api/admin）— GET review, POST approve, POST reject**
- [ ] **Step 4: `list_folders` 加 `kb_id: str = Query(...)`**
- [ ] **Step 5: `list_tags` 加 `kb_id`，`create_tag` body 加 `knowledge_base_id`**
- [ ] **Step 6: `list_papers` / `upload_paper` 加 `kb_id` 参数，upload 做共享库 MD5 去重**
- [ ] **Step 7: main.py 导出并注册 `kb_router`, `admin_router`**
- [ ] **Step 8: 语法检查**
- [ ] **Step 9: Commit** `git commit -m "feat: KB + 审核路由"`

---

### Task 6: ChromaDB 按 KB 隔离

**Files:** Modify `backend/app/qa/indexer.py`

- [ ] **Step 1: 加 `_get_kb_chroma_dir(kb_id)` — 返回 `chroma_data/kb_{kb_id}/`**
- [ ] **Step 2: `_get_collection(kb_id)` — 在 kb 目录下创建/获取 `paper_chunks` 集合**
- [ ] **Step 3: `index_paper`, `delete_paper_index`, `rebuild_all_papers`, `search_chunks` 全部加 `kb_id` 参数**
- [ ] **Step 4: 语法检查**
- [ ] **Step 5: Commit** `git commit -m "feat: ChromaDB 每个 KB 独立目录"`

---

### Task 7: QA / Chat KB 隔离

**Files:** Modify `backend/app/qa/router.py`, `chat_router.py`, `chat_crud.py`, `chat_schemas.py`

- [ ] **Step 1: qa/router.py `rebuild_index` 加 `kb_id` 参数，查询论文加 `Paper.knowledge_base_id == kb_id`**
- [ ] **Step 2: `_get_paper_topics` 加 `kb_id` 参数，缓存 key 改为 `(kb_id)`**
- [ ] **Step 3: chat_crud.py `create_chat_session` 加 `kb_id` 参数，`get_chat_sessions` 按 `kb_id` 过滤**
- [ ] **Step 4: chat_schemas.py `ChatSessionCreate` 加 `kb_id`，`ChatSessionItem` 加 `kb_id`**
- [ ] **Step 5: chat_router.py `send_message` RAG 搜索时传入 `kb_id`**
- [ ] **Step 6: 语法检查四个文件**
- [ ] **Step 7: Commit** `git commit -m "feat: QA 和 Chat 按 kb_id 隔离"`

---

### Task 8: 前端 KB API + Store + 审核 API

**Files:** Create `frontend/src/api/knowledgeBases.js`, `frontend/src/stores/knowledgeBase.js`, `frontend/src/api/admin.js`

- [ ] **Step 1: `api/knowledgeBases.js` — getKnowledgeBases, create, update, delete**
- [ ] **Step 2: `api/admin.js` — getPendingPapers(kbId), approvePaper(id), rejectPaper(id, comment)**
- [ ] **Step 3: `stores/knowledgeBase.js` — list, currentId, isShared, isAdmin, fetchList, select, create, update, remove**
- [ ] **Step 4: 构建验证** `npm run build`
- [ ] **Step 5: Commit** `git commit -m "feat: 前端 KB + 审核 API + Store"`

---

### Task 9: 前端 API 文件加 kb_id

**Files:** Modify `api/papers.js`, `api/qa.js`, `api/chat.js`, `stores/papers.js`

- [ ] **Step 1: `papers.js` — uploadPaper/getFolders/createFolder 加 kbId 参数**
- [ ] **Step 2: `qa.js` — rebuildIndex 加 kbId**
- [ ] **Step 3: `chat.js` — getChatSessions/createChatSession 加 kbId**
- [ ] **Step 4: `stores/papers.js` — 加 kbId 状态 + setKbId + fetchList 传 kb_id**
- [ ] **Step 5: 构建验证**
- [ ] **Step 6: Commit** `git commit -m "feat: 前端 API 加 kb_id 参数"`

---

### Task 10: 论文库页 KB 选择器

**Files:** Modify `PaperLayout.vue`, `PaperLibrary.vue`

- [ ] **Step 1: PaperLayout 侧栏顶部加 KB 下拉框（import useKnowledgeBaseStore）**
- [ ] **Step 2: onMounted 中 fetchList + restoreSelection + setKbId**
- [ ] **Step 3: onKbChange 切换时刷新论文列表**
- [ ] **Step 4: KB 管理弹窗（创建/重命名/删除，共享库不可删）**
- [ ] **Step 5: 共享库时显示"审核管理"入口按钮**
- [ ] **Step 6: PaperLibrary 接收 kbId prop，传给 folders/tags/upload**
- [ ] **Step 7: 构建验证**
- [ ] **Step 8: Commit** `git commit -m "feat: 论文库页 KB 选择器 + 管理弹窗"`

---

### Task 11: GlobalQA + 审核页

**Files:** Modify `GlobalQA.vue`, Create `views/admin/ReviewPage.vue`, Modify `router/index.js`

- [ ] **Step 1: GlobalQA 顶部加 KB 下拉框，对话/索引重建传 kb_id**
- [ ] **Step 2: 创建 ReviewPage.vue — 表格 + 通过/驳回按钮 + 驳回原因弹窗**
- [ ] **Step 3: router/index.js 加 `/admin/review` 路由**
- [ ] **Step 4: 构建验证**
- [ ] **Step 5: Commit** `git commit -m "feat: 审核管理页 + GlobalQA KB 选择器"`

---

### Task 12: 端到端验证

- [ ] **Step 1: 重启后端，测试 KB 列表 API**
- [ ] **Step 2: 测试共享库论文列表 API**
- [ ] **Step 3: 测试前端页面功能**
- [ ] **Step 4: Commit** `git commit -m "chore: 端到端验证通过"`
