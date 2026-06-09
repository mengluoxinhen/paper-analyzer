# 文件夹 + 标签归类设计

## 目标
为论文库增加文件夹组织 + 标签分类功能，用户可创建文件夹归类论文，并通过标签筛选。

## 数据模型

### Folder（新增表）
| 列 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增 |
| name | VARCHAR(200) | 文件夹名，唯一 |
| created_at | DATETIME | 创建时间 |

### Tag（新增表）
| 列 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增 |
| name | VARCHAR(100) | 标签名，唯一 |
| created_at | DATETIME | 创建时间 |

### paper_tags（新增关联表）
| 列 | 类型 | 说明 |
|---|---|---|
| paper_id | INTEGER FK | 论文 ID |
| tag_id | INTEGER FK | 标签 ID |

### Paper（修改）
新增 older_id 列，INTEGER FK → Folder，可为空（代表未分类）。

## 关系规则
- 一篇论文必须属于一个文件夹（默认「未分类」即 folder_id=NULL）
- 删除文件夹 → 级联删除其中所有论文及关联数据
- 一篇论文可打多个标签，标签独立存在，删除标签仅解除关联

## 后端 API

新增：
- GET    /api/folders          — 列表（含论文数量）
- POST   /api/folders          — 创建 { name }
- PUT    /api/folders/:id      — 重命名 { name }
- DELETE /api/folders/:id      — 删除文件夹及论文（级联）
- GET    /api/tags             — 标签列表（含使用次数）
- POST   /api/tags             — 创建标签 { name }
- DELETE /api/tags/:id         — 删除标签
- PUT    /api/papers/:id/tags  — 设置论文标签 { tag_ids: [...] }

修改：
- POST /api/papers/upload 增加可选 older_id 参数
- GET  /api/papers 增加可选 older_id、	ag 过滤参数
- GET  /api/papers/:id 响应增加 older_id、older_name、	ags

## 前端改动

### PaperLibrary.vue（侧边栏）
- 顶部「文件夹」区域：列表 + 新建按钮（可创建/重命名/删除文件夹）
- 每个文件夹项显示论文数量，选中后可删除
- 文件夹「未分类」永远存在，不可删除
- 中部「标签」区域（可折叠）：tag pill 展示，点击筛选
- 搜索框保留，支持按文件夹+标签+关键词联合过滤
- 上传弹窗增加「目标文件夹」下拉选择

### PaperReader.vue
- 工具栏或内容区显示当前论文的标签，可编辑
