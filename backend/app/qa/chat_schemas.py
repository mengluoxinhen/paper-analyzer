from datetime import datetime
from pydantic import BaseModel


class QARequest(BaseModel):
    question: str


class QARebuildResponse(BaseModel):
    ok: bool
    indexed_count: int = 0
    message: str = ""


# ── Chat Session ──

class ChatSessionCreate(BaseModel):
    paper_id: str | None = None
    title: str = ""


class ChatSessionItem(BaseModel):
    id: str
    title: str
    paper_id: str | None = None
    created_at: datetime | None = None
    message_count: int = 0
    preview: str = ""


class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSessionItem] = []


class ChatMessageItem(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    tokens: int = 0
    created_at: datetime | None = None


class ChatSendRequest(BaseModel):
    message: str


class ChatSessionRename(BaseModel):
    title: str
