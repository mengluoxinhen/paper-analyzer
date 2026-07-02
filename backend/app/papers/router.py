import os
import json
import aiofiles
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import DBSession
from app.papers import schemas, crud, utils, service
from app.papers.mineru import parse_pdf_stream, MinerUError
from app.papers.model import Paper

router = APIRouter(prefix="/api/papers", tags=["papers"])
folder_router = APIRouter(prefix="/api/folders", tags=["folders"])
tag_router = APIRouter(prefix="/api/tags", tags=["tags"])


# ═══════════════ Folders ═══════════════

@folder_router.get("", response_model=schemas.FolderListResponse)
async def list_folders(db: AsyncSession = DBSession):
    folders = await crud.get_folders(db)
    uncat = await crud.get_uncategorized_count(db)
    return {"folders": folders, "uncategorized_count": uncat}


@folder_router.post("", response_model=schemas.FolderResponse)
async def create_folder(body: schemas.FolderCreate, db: AsyncSession = DBSession):
    try:
        return await crud.create_folder(db, body.name, body.parent_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@folder_router.put("/{folder_id}", response_model=schemas.FolderResponse)
async def rename_folder(folder_id: str, body: schemas.FolderCreate, db: AsyncSession = DBSession):
    folder = await crud.update_folder(db, folder_id, body.name)
    if not folder:
        raise HTTPException(404, "文件夹不存在")
    return folder


@folder_router.delete("/{folder_id}")
async def delete_folder(folder_id: str, db: AsyncSession = DBSession):
    ok = await crud.delete_folder(db, folder_id)
    if not ok:
        raise HTTPException(404, "文件夹不存在")
    return {"ok": True}


# ═══════════════ Tags ═══════════════

@tag_router.get("", response_model=list[schemas.TagResponse])
async def list_tags(db: AsyncSession = DBSession):
    return await crud.get_tags(db)


@tag_router.post("", response_model=schemas.TagResponse)
async def create_tag(body: schemas.TagCreate, db: AsyncSession = DBSession):
    return await crud.create_tag(db, body.name)


@tag_router.delete("/{tag_id}")
async def delete_tag(tag_id: str, db: AsyncSession = DBSession):
    ok = await crud.delete_tag(db, tag_id)
    if not ok:
        raise HTTPException(404, "标签不存在")
    return {"ok": True}


@router.post("/upload", response_model=schemas.PaperResponse)
async def upload_paper(
    title: str = Query(default=""),
    folder_id: str = Query(default=None),
    pdf_file: UploadFile = File(None),
    db: AsyncSession = DBSession,
):
    if not pdf_file:
        raise HTTPException(400, "请上传 PDF 文件")

    filename = pdf_file.filename or "unknown.pdf"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{ts}_{filename}"

    # Save PDF
    pdf_upload_dir = utils.ensure_upload_dir("pdfs")
    pdf_path = os.path.join(pdf_upload_dir, safe_name)
    pdf_bytes = await pdf_file.read()
    async with aiofiles.open(pdf_path, "wb") as f:
        await f.write(pdf_bytes)

    status = "uploaded"

    # Validate folder_id
    if folder_id is not None:
        folder = await crud.get_folder(db, folder_id)
        if not folder:
            raise HTTPException(400, "目标文件夹不存在")

    paper = await crud.create_paper(
        db, title=title, filename=filename,
        pdf_path=pdf_path, folder_id=folder_id,
    )
    paper.status = status
    await db.commit()
    paper = await crud.get_paper(db, paper.id)
    return await crud.paper_to_response(db, paper)


@router.post("/{paper_id}/parse")
async def parse_paper(paper_id: str, db: AsyncSession = DBSession):
    """Trigger MinerU parsing with SSE progress streaming."""
    paper = await crud.get_paper(db, paper_id)
    if not paper:
        raise HTTPException(404, "论文不存在")
    if not paper.pdf_path or not os.path.isfile(paper.pdf_path):
        raise HTTPException(400, "PDF 文件不存在，请先上传")

    paper.status = "parsing"
    await db.commit()

    pdf_path = paper.pdf_path
    filename = paper.filename

    async def event_stream():
        from app.database import async_session
        import json as _json
        md_content = ""
        batch_id = ""
        try:
            async for event in parse_pdf_stream(pdf_path=pdf_path, file_name=filename):
                stage = event.get("stage", "")
                if stage == "done":
                    md_content = event.get("md_content", "")
                    batch_id = event.get("batch_id", "")
                    yield f"data: {_json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8")
                    break
                yield f"data: {_json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8")
        except MinerUError as e:
            yield f"data: {_json.dumps({'stage': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n".encode("utf-8")
            async with async_session() as s:
                p = await s.get(Paper, paper_id)
                if p:
                    p.status = "parse_failed"
                    await s.commit()
            return

        async with async_session() as s:
            p = await s.get(Paper, paper_id)
            if p and md_content:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                md_upload_dir = utils.ensure_upload_dir("papers")
                safe_md = f"{ts}_{p.filename}.md"
                md_path = os.path.join(md_upload_dir, safe_md)
                async with aiofiles.open(md_path, "w", encoding="utf-8") as f:
                    await f.write(md_content)
                p.md_content = md_content
                p.md_path = md_path
                p.mineru_batch_id = batch_id
                p.status = "parsed"
            elif p:
                p.status = "parse_failed"
            await s.commit()

        yield f"data: [DONE]\n\n".encode("utf-8")

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{paper_id}/pdf")
async def serve_pdf(paper_id: str, db: AsyncSession = DBSession):
    from fastapi.responses import FileResponse
    paper = await crud.get_paper(db, paper_id)
    if not paper or not paper.pdf_path:
        raise HTTPException(404, "PDF 文件不存在")
    if not os.path.isfile(paper.pdf_path):
        raise HTTPException(404, "PDF 文件未找到")
    return FileResponse(paper.pdf_path, media_type="application/pdf")


@router.get("", response_model=schemas.PaperListResponse)
async def list_papers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = Query(default=""),
    folder_id: str = Query(default=None),
    tag: str = Query(default=""),
    db: AsyncSession = DBSession,
):
    papers, total = await crud.get_papers(db, page=page, page_size=page_size, keyword=keyword, folder_id=folder_id, tag=tag)
    return {
        "papers": [await crud.paper_to_response(db, p) for p in papers],
        "total": total,
    }


@router.get("/{paper_id}", response_model=schemas.PaperDetail)
async def get_paper(paper_id: str, db: AsyncSession = DBSession):
    paper = await crud.get_paper(db, paper_id)
    if not paper:
        raise HTTPException(404, "论文不存在")
    result = await crud.paper_to_response(db, paper)
    result["md_content"] = paper.md_content
    return result


@router.put("/{paper_id}", response_model=schemas.PaperResponse)
async def update_paper_title(paper_id: str, body: schemas.PaperCreate, db: AsyncSession = DBSession):
    paper = await crud.update_paper_title(db, paper_id, body.title)
    if not paper:
        raise HTTPException(404, "论文不存在")
    return await crud.paper_to_response(db, paper)


@router.delete("/{paper_id}")
async def delete_paper(paper_id: str, db: AsyncSession = DBSession):
    paper = await crud.get_paper(db, paper_id)
    if not paper:
        raise HTTPException(404, "论文不存在")

    # Remove local files
    for p in [paper.pdf_path, paper.md_path, paper.json_path]:
        if p and os.path.isfile(p):
            try:
                os.unlink(p)
            except OSError:
                pass

    ok = await crud.delete_paper(db, paper_id)
    if not ok:
        raise HTTPException(500, "删除失败")
    return {"ok": True}


@router.put("/{paper_id}/move", response_model=schemas.PaperResponse)
async def move_paper(paper_id: str, body: schemas.PaperMoveRequest, db: AsyncSession = DBSession):
    try:
        paper = await crud.move_paper(db, paper_id, body.folder_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not paper:
        raise HTTPException(404, "论文不存在")
    return await crud.paper_to_response(db, paper)


@router.put("/{paper_id}/tags", response_model=schemas.PaperResponse)
async def update_tags(paper_id: str, body: schemas.PaperTagUpdate, db: AsyncSession = DBSession):
    paper = await crud.set_paper_tags(db, paper_id, body.tag_ids)
    if not paper:
        raise HTTPException(404, "论文不存在")
    return await crud.paper_to_response(db, paper)


@router.post("/{paper_id}/summarize")
async def summarize_paper(paper_id: str, db: AsyncSession = DBSession):
    paper = await crud.get_paper(db, paper_id)
    if not paper:
        raise HTTPException(404, "论文不存在")

    # Return cached summary if available
    existing = await crud.get_summary(db, paper_id)
    if existing and existing.full_text:
        import json
        cached_data = json.dumps({
            "problem": existing.problem or "",
            "conclusion": existing.conclusion or "",
            "conditions": existing.conditions or "",
            "full_text": existing.full_text or "",
        })
        async def cached_stream():
            yield f"data: __CACHED__{cached_data}\n\n".encode("utf-8")
            yield f"data: [DONE]\n\n".encode("utf-8")
        return StreamingResponse(cached_stream(), media_type="text/event-stream")

    content = paper.md_content
    if not content and paper.md_path:
        content = utils.read_file_content(paper.md_path)

    if not content:
        raise HTTPException(400, "没有可用的论文内容")

    async def event_stream():
        full_text = ""
        async for chunk in service.stream_summarize(content, db):
            if chunk.startswith("__DONE__"):
                full_text = chunk[7:]
                break
            yield f"data: {chunk}\n\n".encode("utf-8")

        sections = service.parse_summary_text(full_text)
        total_tokens = utils.count_tokens_approx(full_text)
        await crud.create_summary(
            db, paper_id,
            problem=sections.get("problem", ""),
            conclusion=sections.get("conclusion", ""),
            conditions=sections.get("conditions", ""),
            full_text=full_text,
            model="llm",
            tokens=total_tokens,
        )
        yield f"data: [DONE]\n\n".encode("utf-8")

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{paper_id}/summary")
async def get_summary(paper_id: str, db: AsyncSession = DBSession):
    summary = await crud.get_summary(db, paper_id)
    if not summary:
        return {}
    return summary


@router.post("/{paper_id}/chat")
async def chat_with_paper(paper_id: str, body: schemas.ChatRequest, db: AsyncSession = DBSession):
    paper = await crud.get_paper(db, paper_id)
    if not paper:
        raise HTTPException(404, "论文不存在")

    content = paper.md_content
    if not content and paper.md_path:
        content = utils.read_file_content(paper.md_path)

    if not content:
        raise HTTPException(400, "没有可用的论文内容")

    user_tokens = utils.count_tokens_approx(body.message)
    await crud.add_conversation(db, paper_id, "user", body.message, user_tokens)

    history_objs = await crud.get_conversations(db, paper_id)
    history = [{"role": h.role, "content": h.content} for h in reversed(history_objs)]

    async def event_stream():
        full_text = ""
        async for chunk in service.stream_chat(content, history[:-1], body.message, db):
            if chunk.startswith("__DONE__"):
                full_text = chunk[7:]
                break
            yield f"data: {chunk}\n\n".encode("utf-8")

        assistant_tokens = utils.count_tokens_approx(full_text)
        await crud.add_conversation(db, paper_id, "assistant", full_text, assistant_tokens)
        yield f"data: [DONE]\n\n".encode("utf-8")

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{paper_id}/conversations", response_model=list[schemas.ConversationResponse])
async def get_conversations(
    paper_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = DBSession,
):
    convs = await crud.get_conversations(db, paper_id, limit)
    return list(reversed(convs))


@router.post("/compare")
async def compare_papers(body: schemas.CompareRequest, db: AsyncSession = DBSession):
    contents = []
    for pid in body.paper_ids:
        paper = await crud.get_paper(db, pid)
        if paper:
            content = paper.md_content
            if not content and paper.md_path:
                content = utils.read_file_content(paper.md_path)
            contents.append({"title": paper.title or paper.filename, "content": content})

    if len(contents) < 2:
        raise HTTPException(400, "至少需要2篇论文进行对比")

    async def event_stream():
        async for chunk in service.stream_compare(contents, db):
            yield f"data: {chunk}\n\n".encode("utf-8")
        yield f"data: [DONE]\n\n".encode("utf-8")

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/{paper_id}/extract", response_model=list[schemas.ExtractionResponse])
async def extract_paper_info(paper_id: str, body: schemas.ExtractRequest, db: AsyncSession = DBSession):
    paper = await crud.get_paper(db, paper_id)
    if not paper:
        raise HTTPException(404, "论文不存在")

    content = paper.md_content
    if not content and paper.md_path:
        content = utils.read_file_content(paper.md_path)

    if not content:
        raise HTTPException(400, "没有可用的论文内容")

    items = await service.extract_info(content, body.types, db)
    return await crud.save_extractions(db, paper_id, items)


@router.get("/{paper_id}/extractions", response_model=list[schemas.ExtractionResponse])
async def get_extractions(paper_id: str, db: AsyncSession = DBSession):
    return await crud.get_extractions(db, paper_id)








