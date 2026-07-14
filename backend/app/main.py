import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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


app = FastAPI(title="PaperMind API", version="1.0.0", lifespan=lifespan)

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


from app.settings.router import router as settings_router
from app.papers.router import router as papers_router, folder_router, tag_router, kb_router, admin_router
from app.qa.router import router as qa_router
from app.qa.chat_router import router as chat_router

app.include_router(settings_router)
app.include_router(kb_router)
app.include_router(admin_router)
app.include_router(folder_router)
app.include_router(tag_router)
app.include_router(papers_router)
app.include_router(qa_router)
app.include_router(chat_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
