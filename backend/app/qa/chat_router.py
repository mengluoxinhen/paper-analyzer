import json
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import DBSession
from app.papers import crud as papers_crud, utils as papers_utils
from app.papers.model import Paper
from app.qa.chat_crud import (
    create_chat_session, get_chat_sessions, get_chat_session,
    update_chat_session_title, delete_chat_session,
    add_chat_message, get_chat_messages,
)
from app.qa.chat_schemas import (
    ChatSessionCreate, ChatSessionListResponse,
    ChatMessageItem, ChatSendRequest, ChatSessionRename,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])

_MD_FORMAT = """
【输出格式】只输出纯 Markdown 源码，不要添加任何开场白、过渡语、总结语。严格遵循以下规则：

- 标题（##、###）独占一行，标题与正文之间用空行分隔
- 用 **粗体** 强调关键概念、数值、方法
- 列表用 - 开头，子项缩进2空格
- 表格对齐，表头与表体用 | --- | 分隔
- 不要输出"好的""以下是回答""总结一下"等废话
"""

@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_sessions(
    paper_id: str | None = Query(None, description="Filter by paper; omit for global"),
    kb_id: str | None = Query(None, description="Filter by knowledge base"),
    db: AsyncSession = DBSession,
):
    sessions = await get_chat_sessions(db, paper_id=paper_id, kb_id=kb_id)
    return {"sessions": sessions}


@router.post("/sessions")
async def create_session(body: ChatSessionCreate, db: AsyncSession = DBSession):
    session = await create_chat_session(db, title=body.title, paper_id=body.paper_id, kb_id=body.kb_id)
    return {
        "id": session.id,
        "title": session.title,
        "paper_id": session.paper_id,
        "kb_id": session.knowledge_base_id,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "message_count": 0,
        "preview": "",
    }


@router.put("/sessions/{session_id}")
async def rename_session(session_id: str, body: ChatSessionRename, db: AsyncSession = DBSession):
    session = await update_chat_session_title(db, session_id, body.title)
    if not session:
        raise HTTPException(404, "会话不存在")
    return {"ok": True}


@router.delete("/sessions/{session_id}")
async def remove_session(session_id: str, db: AsyncSession = DBSession):
    ok = await delete_chat_session(db, session_id)
    if not ok:
        raise HTTPException(404, "会话不存在")
    return {"ok": True}


@router.get("/sessions/{session_id}/messages")
async def list_messages(session_id: str, db: AsyncSession = DBSession):
    session = await get_chat_session(db, session_id)
    if not session:
        raise HTTPException(404, "会话不存在")
    msgs = await get_chat_messages(db, session_id)
    return [
        {"id": m.id, "session_id": m.session_id, "role": m.role, "content": m.content, "tokens": m.tokens, "created_at": m.created_at.isoformat() if m.created_at else None}
        for m in reversed(msgs)
    ]


@router.post("/sessions/{session_id}/send")
async def send_message(session_id: str, body: ChatSendRequest, db: AsyncSession = DBSession):
    session = await get_chat_session(db, session_id)
    if not session:
        raise HTTPException(404, "会话不存在")

    message = body.message.strip()
    if not message:
        raise HTTPException(400, "消息不能为空")

    if session.title == "新对话" or not session.title:
        title = message[:60] + ("..." if len(message) > 60 else "")
        await update_chat_session_title(db, session_id, title)

    user_tokens = papers_utils.count_tokens_approx(message)
    await add_chat_message(db, session_id, "user", message, user_tokens)

    history_msgs = await get_chat_messages(db, session_id)
    history = [{"role": m.role, "content": m.content} for m in reversed(history_msgs)]
    history_for_prompt = history[:-1] if len(history) > 1 else []

    paper_id = session.paper_id
    kb_id = session.knowledge_base_id

    async def event_stream():
        from app.papers.service import _get_llm_config
        from openai import AsyncOpenAI
        cfg = await _get_llm_config(db)
        client = AsyncOpenAI(api_key=cfg["api_key"], base_url=cfg["api_base"])
        full_text = ""

        if paper_id:
            paper = await papers_crud.get_paper(db, paper_id)
            if not paper or not paper.md_content:
                yield f"data: __ERROR__论文不存在或未解析\n\n".encode("utf-8")
                return
            content = paper.md_content
            system_prompt = "你是一个专业的学术论文问答助手。请严格基于提供的论文内容回答用户问题。如果用户问及对话历史或之前的问题，请根据对话记录如实回答。不要编造信息，如不确定请说明。" + _MD_FORMAT
            max_content_len = 64000
            if len(content) > max_content_len:
                content = content[:max_content_len] + "\n\n[论文内容过长，已截断]"
            # 论文内容放入 system prompt，不会被历史窗口截断
            system_prompt_full = f"{system_prompt}\n\n【论文内容】\n\n{content}"
            msgs = [{"role": "system", "content": system_prompt_full}]
            for h in history_for_prompt[-10:]:
                msgs.append(h)
            msgs.append({"role": "user", "content": message})
            try:
                stream = await client.chat.completions.create(model=cfg["model"], messages=msgs, max_tokens=cfg.get("max_tokens", 2048), temperature=cfg.get("temperature", 0.3), stream=True)
                async for chunk in stream:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        full_text += delta.content
                        yield f"data: {json.dumps(delta.content)}\n\n".encode("utf-8")
            except Exception as e:
                yield f"data: __ERROR__{str(e)}\n\n".encode("utf-8")
        else:
            from app.qa.router import _rewrite_query, _build_qa_prompt
            from app.qa import embedder, indexer
            search_query = await _rewrite_query(message, db, kb_id or "")
            if "NOT_RELEVANT" in search_query:
                search_query = message
            try:
                query_emb = await embedder.get_embedding(search_query)
            except Exception as e:
                yield f"data: __ERROR__Embedding 请求失败: {e}\n\n".encode("utf-8")
                return
            chunks = indexer.search_chunks(query_emb, kb_id or "", top_k=8)
            if not chunks:
                yield f"data: {json.dumps('未在知识库中找到与您问题相关的论文内容，请尝试更具体的问题。')}\n\n".encode("utf-8")
            else:
                prompt = _build_qa_prompt(message, chunks)
                if history_for_prompt:
                    history_text = "\n\n".join(f"{h['role']}: {h['content']}" for h in history_for_prompt[-6:])
                    prompt = f"历史对话：\n{history_text}\n\n{prompt}"
                try:
                    stream = await client.chat.completions.create(model=cfg["model"], messages=[{"role": "user", "content": prompt}], max_tokens=cfg.get("max_tokens", 2048), temperature=cfg.get("temperature", 0.3), stream=True)
                    async for chunk in stream:
                        delta = chunk.choices[0].delta
                        if delta.content: full_text += delta.content; yield f"data: {json.dumps(delta.content)}\n\n".encode("utf-8")
                    # Send source references
                    sources_info = [{"paper_id": ch["paper_id"], "paper_title": ch["paper_title"], "section": ch.get("section", "")} for ch in chunks]
                    yield f"data: __SOURCES__{json.dumps(sources_info, ensure_ascii=False)}\n\n".encode("utf-8")
                except Exception as e:
                    yield f"data: __ERROR__{str(e)}\n\n".encode("utf-8")
                    return


        assistant_tokens = papers_utils.count_tokens_approx(full_text)
        await add_chat_message(db, session_id, "assistant", full_text, assistant_tokens)
        yield f"data: [DONE]\n\n".encode("utf-8")

    return StreamingResponse(event_stream(), media_type="text/event-stream")