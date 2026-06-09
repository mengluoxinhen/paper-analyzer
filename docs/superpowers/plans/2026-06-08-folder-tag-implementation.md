# 文件夹+标签归类 实施计划

> **Goal:** 论文库支持文件夹组织和标签分类

**Architecture:** 后端新增 Folder/Tag 模型 + API，Paper 增加 folder_id；前端侧边栏改为文件夹树 + 标签 pill

**Tech Stack:** FastAPI + SQLAlchemy + SQLite, Vue 3 + Element Plus

---

### Task 1: 后端模型
- 新增 Folder 模型 (pp/papers/model.py)
- 新增 Tag 模型 + paper_tags 关联表
- Paper 增加 folder_id 列

### Task 2: 后端 CRUD + API
- folders CRUD + router
- tags CRUD + router
- 修改 papers 路由（folder_id 过滤、上传增加 folder_id、标签设置接口）
- 注册路由到 main.py

### Task 3: 前端 API
- 新增 folders/tags API 函数
- 修改 papers API（upload 增加 folder_id）

### Task 4: 前端 UI
- 重写 PaperLibrary：文件夹树 + 标签 pill + 论文列表
- 上传弹窗增加文件夹选择
- PaperReader 显示/编辑标签
