# 独立知识库功能设计文档

**日期**: 2026-07-14
**状态**: 待审核

---

## 1. 概述

为 PaperMind 论文管理系统引入知识库（KnowledgeBase）概念，实现论文数据的多维度隔离。

## 2. 核心需求

- 共享知识库：所有成员可见，论文需管理员审核后入库
- 个人知识库：每人可创建多个，互相隔离，上传即用无需审核
- 暂不实现用户系统，API 预留 `user_id` 字段，当前使用默认 ID
- 保留现有数据：全部迁移至共享库

## 3. 数据模型变更

### 3.1 新增表 `knowledge_bases`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(32) PK | UUID |
| name | VARCHAR(200) | 名称 |
| description | VARCHAR(1000) | 描述 |
| user_id | VARCHAR(32) NULL | NULL=共享库，有值=私有库 |
| is_shared | BOOL | 是否为共享库 |
| created_at | DATETIME | 创建时间 |

### 3.2 `papers` 表新增字段

| 字段 | 类型 | 说明 |
|------|------|------|
| kb_id | VARCHAR(32) FK | 所属知识库 |
| review_status | VARCHAR(20) | none / pending / approved / rejected |
| file_md5 | VARCHAR(32) | PDF 文件 MD5（共享库去重用） |
| reviewed_at | DATETIME | 审核时间 |
| review_comment | VARCHAR(500) | 审核意见 |

### 3.3 `folders` 表变更

- 新增 `kb_id` 字段
- 唯一约束改为 `UNIQUE(name, parent_id, kb_id)`

### 3.4 `chat_sessions` 表新增字段

| 字段 | 类型 | 说明 |
|------|------|------|
| kb_id | VARCHAR(32) NULL | 全局对话所属知识库 |

## 4. 共享库去重方案

1. **MD5 精确去重**：上传时计算 PDF 文件 MD5，在共享库已上传论文中查找，命中则拒绝并提示
2. **标题模糊匹配**：解析完成后，用 `difflib.SequenceMatcher` 与共享库已有论文标题比对，相似度 > 85% 时标注"⚠️疑似重复"，提醒管理员注意

## 5. 审核流程

```
用户上传 → MD5查重 → 命中 → 拒绝
                  → 未命中 → 上传PDF + MinerU解析
                              → 标题模糊匹配 → "⚠️疑似重复"
                              → review_status = "pending"

管理员 → 查看待审列表 → 通过 → 状态="approved" + 入 ChromaDB
                    → 驳回 → 状态="rejected" + 填写原因
```


### 5.1 文件夹管理权限

| 知识库类型 | 创建文件夹 | 删除/重命名文件夹 | 上传论文 |
|-----------|----------|----------------|---------|
| 共享库 | 仅管理员 | 仅管理员 | 所有人（需选已有文件夹） |
| 私有库 | 创建者 | 创建者 | 创建者 |

实现方式：文件夹 API 增加 `user_id` 参数，共享库操作时校验是否为管理员（默认 ID），非管理员返回 403。

 隔离

每个 KB 独立一个 ChromaDB 目录，搜索按 KB 取对应集合：

| KB | ChromaDB 路径 |
|----|--------------|
| 共享库 | `chroma_data/kb_shared/` |
| 私有库 A | `chroma_data/kb_{a_id}/` |

迁移时将现有 `chroma_data/` 下数据移至 `chroma_data/kb_shared/`。

## 7. API 设计

### 知识库

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/knowledge-bases?user_id=xxx` | 返回共享库 + 该用户私有库 |
| POST | `/api/knowledge-bases` | 创建 KB |
| PUT | `/api/knowledge-bases/{id}` | 修改 KB 信息 |
| DELETE | `/api/knowledge-bases/{id}` | 删除 KB 及所有内容 |

### 论文（增加 kb_id 参数）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/papers?kb_id=xxx` | 按 KB 查论文 |
| POST | `/api/papers/upload?kb_id=xxx` | 上传（共享库自动 MD5 去重） |

### 审核

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/admin/review?kb_id=xxx` | 获取待审核列表 |
| POST | `/api/admin/review/{paper_id}/approve` | 审核通过 |
| POST | `/api/admin/review/{paper_id}/reject` | 驳回（带 `comment`） |

### QA / Chat（增加 kb_id 参数）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/qa/rebuild?kb_id=xxx` | 重建指定 KB 索引 |
| GET | `/api/chat/sessions?kb_id=xxx` | 全局对话按 KB 过滤 |

## 8. 前端改动

### 论文库页（PaperLayout）

- 侧栏顶部增加 KB 下拉选择器（"共享库" + 我的私有库）
- 齿轮按钮弹出 KB 管理对话框（创建/删除/重命名）
- 切换 KB 时自动刷新论文列表和文件夹
- 共享库时右上角显示"审核管理"入口按钮

### 全局问答页（GlobalQA）

- 顶部增加 KB 选择器
- 对话和索引重建按选中 KB 隔离

### 新页面：审核管理（`/admin/review`）

- 表格展示共享库待审核论文
- 每行：标题、上传时间、文件、⚠️疑似重复提示、通过/驳回按钮
- 驳回弹出输入框填写原因

## 9. 数据迁移

- 自动创建"共享知识库"记录（user_id=NULL, is_shared=true）
- 现有全部论文、文件夹的 `kb_id` 指向共享库
- 现有论文 `review_status` 设为 `approved`
- 现有 ChromaDB 数据移至 `chroma_data/kb_shared/`

## 10. 兼容性

- `user_id` 字段预留，当前使用 `"default_user"`
- 以后接入用户系统时，只需修改前端传递的真实 user_id
- 管理员判断：当前默认 ID 即为管理员



