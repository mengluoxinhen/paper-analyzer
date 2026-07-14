from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from app.papers.model import ChatSession, ChatMessage


async def create_chat_session(db: AsyncSession, title: str = "", paper_id: str | None = None, kb_id: str | None = None) -> ChatSession:
    if not title:
        title = "新对话"
    session = ChatSession(title=title, paper_id=paper_id, knowledge_base_id=kb_id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_chat_sessions(db: AsyncSession, paper_id: str | None = None, kb_id: str | None = None) -> list[dict]:
    if paper_id is not None:
        stmt = select(ChatSession).where(ChatSession.paper_id == paper_id).order_by(ChatSession.created_at.desc())
    elif kb_id is not None:
        stmt = select(ChatSession).where(ChatSession.paper_id.is_(None), ChatSession.knowledge_base_id == kb_id).order_by(ChatSession.created_at.desc())
    else:
        stmt = select(ChatSession).where(ChatSession.paper_id.is_(None)).order_by(ChatSession.created_at.desc())
    result = await db.execute(stmt)
    sessions = list(result.scalars().all())
    out = []
    for s in sessions:
        cnt_result = await db.execute(select(func.count(ChatMessage.id)).where(ChatMessage.session_id == s.id))
        msg_count = cnt_result.scalar() or 0
        last_msg_result = await db.execute(select(ChatMessage.content).where(ChatMessage.session_id == s.id).order_by(ChatMessage.created_at.desc()).limit(1))
        last_row = last_msg_result.first()
        preview = last_row[0][:80] if last_row else ""
        out.append({"id": s.id, "title": s.title, "paper_id": s.paper_id, "kb_id": s.knowledge_base_id, "created_at": s.created_at, "message_count": msg_count, "preview": preview})
    return out


async def get_chat_session(db: AsyncSession, session_id: str) -> ChatSession | None:
    return await db.get(ChatSession, session_id)


async def update_chat_session_title(db: AsyncSession, session_id: str, title: str) -> ChatSession | None:
    session = await db.get(ChatSession, session_id)
    if session:
        session.title = title
        await db.commit()
        await db.refresh(session)
    return session


async def delete_chat_session(db: AsyncSession, session_id: str) -> bool:
    session = await db.get(ChatSession, session_id)
    if not session:
        return False
    await db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
    await db.delete(session)
    await db.commit()
    return True


async def add_chat_message(db: AsyncSession, session_id: str, role: str, content: str, tokens: int = 0) -> ChatMessage:
    msg = ChatMessage(session_id=session_id, role=role, content=content, tokens=tokens)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def get_chat_messages(db: AsyncSession, session_id: str, limit: int = 100) -> list[ChatMessage]:
    result = await db.execute(select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.desc()).limit(limit))
    return list(result.scalars().all())
