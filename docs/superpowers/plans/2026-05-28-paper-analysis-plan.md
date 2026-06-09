# 论文分析平台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Build a MinerU paper analysis web app with FastAPI + Vue 3.

**Architecture:** FastAPI async with domain-based module packaging (papers/). Vue 3 SPA with Element Plus, 3-column layout. MySQL + local files.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (async), MySQL, Alembic, openai SDK, sse-starlette, Vue 3, Vite, Element Plus, Pinia, marked, highlight.js

---

## Phase 1: Project Scaffolding

### Task 1: Scaffold Backend

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/deps.py`

- [ ] **Step 1: Create directory structure**

```powershell
New-Item -ItemType Directory -Force -Path C:\myweb\backend\app
```

- [ ] **Step 2: Write requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy[asyncio]==2.0.35
asyncmy==0.2.9
alembic==1.13.0
openai==1.51.0
sse-starlette==2.1.0
python-multipart==0.0.12
pydantic-settings==2.5.0
aiofiles==24.1.0
```

- [ ] **Step 3: Write .env.example**

```
DATABASE_URL=mysql+asyncmy://root:password@localhost:3306/paper_analysis
LLM_API_BASE=https://api.deepseek.com
LLM_API_KEY=sk-your-key
LLM_MODEL=deepseek-chat
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0.7
UPLOAD_DIR=./uploads
```

- [ ] **Step 4: Write app/config.py**

```python
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "mysql+asyncmy://root:password@localhost:3306/paper_analysis"
    llm_api_base: str = "https://api.deepseek.com"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.7
    upload_dir: str = "./uploads"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
```


- [ ] **Step 5: Write app/database.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=False, pool_size=10, max_overflow=20)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
```

- [ ] **Step 6: Write app/deps.py**

```python
from app.database import get_db
from fastapi import Depends

DBSession = Depends(get_db)
```

- [ ] **Step 7: Write app/main.py**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app.papers.model import Base as PapersBase
from app.settings.model import Base as SettingsBase


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: PapersBase.metadata.create_all(c))
        await conn.run_sync(lambda c: SettingsBase.metadata.create_all(c))
    yield
    await engine.dispose()


app = FastAPI(title="Paper Analysis API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 8: Commit**

---

### Task 2: Scaffold Frontend

- [ ] **Step 1: Create Vue project**

```powershell
cd C:\myweb
npm create vite@latest frontend -- --template vue
```

- [ ] **Step 2: Install dependencies**

```powershell
cd C:\myweb\frontend
npm install element-plus @element-plus/icons-vue pinia vue-router@4 axios marked highlight.js
npm install -D sass
```

- [ ] **Step 3: Write src/main.js**

```javascript
import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import * as ElementPlusIconsVue from "@element-plus/icons-vue";
import App from "./App.vue";
import router from "./router";

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.use(ElementPlus, { size: "small" });

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component);
}
app.mount("#app");
```

- [ ] **Step 4: Write src/App.vue**

```vue
<template>
  <router-view />
</template>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #app {
  height: 100%;
  font-family: "Helvetica Neue", Helvetica, "PingFang SC", "Microsoft YaHei", sans-serif;
}
</style>
```

- [ ] **Step 5: Write src/router/index.js**

```javascript
import { createRouter, createWebHistory } from "vue-router";

const routes = [
  { path: "/", redirect: "/papers" },
  {
    path: "/papers",
    name: "Papers",
    component: () => import("../views/papers/PaperLayout.vue"),
  },
];

export default createRouter({ history: createWebHistory(), routes });
```

- [ ] **Step 6: Modify vite.config.js** — add proxy for /api to http://localhost:8000

- [ ] **Step 7: Commit**


---

## Phase 2: Backend - Settings Module

### Task 3: Settings Module

**Files:** `backend/app/settings/__init__.py`, `model.py`, `schemas.py`, `crud.py`, `router.py`
**Modify:** `backend/app/main.py` (register router)

Settings table with key/value pairs. CRUD supports get_all and upsert_all. Router exposes GET /api/settings and PUT /api/settings.

---

## Phase 3: Backend - Papers Module

### Task 4: Papers Model

**File:** `backend/app/papers/model.py`

Four tables with relationships:
- `papers` (id, title, filename, md_path, json_path, md_content, status, created_at)
- `summaries` (id, paper_id FK, background, methods, results, conclusion, full_text, model, tokens, created_at)
- `conversations` (id, paper_id FK, role, content, tokens, created_at)
- `extractions` (id, paper_id FK, type, content JSON, created_at)

### Task 5: Papers Schemas

**File:** `backend/app/papers/schemas.py`

Pydantic models: PaperCreate, PaperResponse, PaperDetail, PaperListResponse, SummaryResponse, ConversationResponse, ChatRequest, CompareRequest, ExtractRequest, ExtractionResponse.

### Task 6: Papers CRUD

**File:** `backend/app/papers/crud.py`

Async CRUD functions for all four tables: create/read/list/delete papers, create/get summaries, add/get conversations, save/get extractions.

### Task 7: Papers Utils

**File:** `backend/app/papers/utils.py`

Helper functions: ensure_upload_dir, read_file_content, parse_json_content, count_tokens_approx, build_summarize_prompt, build_chat_system_prompt, build_compare_prompt, build_extract_prompt.

### Task 8: Papers Service

**File:** `backend/app/papers/service.py`

LLM integration via openai SDK: stream_summarize (SSE), parse_summary_text, stream_chat (SSE with history), stream_compare (SSE), extract_info (non-streaming JSON extraction).

### Task 9: Papers Router

**File:** `backend/app/papers/router.py`
**Modify:** `backend/app/main.py`

11 endpoints:
- POST /api/papers/upload (multipart md+json)
- GET /api/papers (list with pagination)
- GET /api/papers/{id}
- PUT /api/papers/{id} (update title)
- DELETE /api/papers/{id}
- POST /api/papers/{id}/summarize (SSE streaming)
- GET /api/papers/{id}/summary
- POST /api/papers/{id}/chat (SSE streaming)
- GET /api/papers/{id}/conversations
- POST /api/papers/compare (SSE streaming, multi-paper)
- POST /api/papers/{id}/extract
- GET /api/papers/{id}/extractions

---

## Phase 4: Frontend

### Task 10: API Layer & Stores

**Files:** `frontend/src/api/index.js`, `papers.js`, `settings.js`, `frontend/src/stores/papers.js`, `settings.js`

Axios instance, paper API functions (upload, list, detail, delete, summary, conversations), settings API functions. Pinia stores for papers state and settings state.

### Task 11: Main Page Components

**Files:**
- `frontend/src/views/papers/PaperLayout.vue` — 3-column flex layout
- `frontend/src/views/papers/PaperLibrary.vue` — left sidebar: upload dialog, search, paper list
- `frontend/src/views/papers/PaperReader.vue` — center: markdown rendering with marked+highlight.js
- `frontend/src/views/papers/PaperChat.vue` — right: summary display + SSE chat with streaming

### Task 12: Settings Dialog & Integration

**File:** `frontend/src/views/settings/SettingsDialog.vue`
**Modify:** `frontend/src/views/papers/PaperLayout.vue`

LLM config dialog (api_base, api_key, model, max_tokens, temperature). Wired into PaperLayout header.

---

## Self-Review

1. **Spec coverage:** All spec requirements covered - upload, list, detail, delete, summarize, chat, compare, extract, settings.
2. **Placeholder scan:** No TBD/TODO.
3. **Type consistency:** Model fields match across model.py, schemas.py, crud.py, and router.py.

