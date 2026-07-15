import os
import json
import hashlib
import aiofiles
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import DBSession
from app.papers import schemas, crud, utils, service
from app.papers.mineru import parse_pdf_stream, MinerUError
from app.qa import indexer
from app.papers.model import Paper

DEFAULT_USER_ID = "default_user"

router = APIRouter(prefix="/api/papers", tags=["papers"])
folder_router = APIRouter(prefix="/api/folders", tags=["folders"])
tag_router = APIRouter(prefix="/api/tags", tags=["tags"])
kb_router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge-bases"])
admin_router = APIRouter(prefix="/api/admin", tags=["admin"])


def _is_admin(user_id: str) -> bool:
    return user_id == DEFAULT_USER_ID


# ═══════════════ Knowledge Bases ═══════════════

@kb_router.get("", response_model=list[schemas.KnowledgeBaseResponse])
async def list_knowledge_bases(user_id: str = Query(default=DEFAULT_USER_ID), db: AsyncSession = DBSession):
    return await crud.get_knowledge_bases(db, user_id)


@kb_router.post("", response_model=schemas.KnowledgeBaseResponse)
async def create_knowledge_base(body: schemas.KnowledgeBaseCreate, user_id: str = Query(default=DEFAULT_USER_ID), db: AsyncSession = DBSession):
    kb = await crud.create_knowledge_base(db, body.name, body.description, user_id)
    return {"id": kb.id, "name": kb.name, "description": kb.description or "", "user_id": kb.user_id, "is_shared": kb.is_shared, "paper_count": 0, "created_at": kb.created_at}


@kb_router.put("/{kb_id}", response_model=schemas.KnowledgeBaseResponse)
async def update_knowledge_base(kb_id: str, body: schemas.KnowledgeBaseUpdate, db: AsyncSession = DBSession):
    kb = await crud.update_knowledge_base(db, kb_id, body.name, body.description)
    if not kb:
        raise HTTPException(404, "知识库不存在")
    cnt_result = await db.execute(select(func.count(Paper.id)).where(Paper.knowledge_base_id == kb_id))
    cnt = cnt_result.scalar() or 0
    return {"id": kb.id, "name": kb.name, "description": kb.description or "", "user_id": kb.user_id, "is_shared": kb.is_shared, "paper_count": cnt, "created_at": kb.created_at}


@kb_router.delete("/{kb_id}")
async def delete_knowledge_base(kb_id: str, db: AsyncSession = DBSession):
    ok = await crud.delete_knowledge_base(db, kb_id)
    if not ok:
        raise HTTPException(404, "知识库不存在或无法删除共享库")
    return {"ok": True}


# ═══════════════ Folders ═══════════════

@folder_router.get("", response_model=schemas.FolderListResponse)
async def list_folders(kb_id: str = Query(...), db: AsyncSession = DBSession):
    folders = await crud.get_folders(db, kb_id)
    uncat = await crud.get_uncategorized_count(db, kb_id)
    return {"folders": folders, "uncategorized_count": uncat}


@folder_router.post("", response_model=schemas.FolderResponse)
async def create_folder(body: schemas.FolderCreate, user_id: str = Query(default=DEFAULT_USER_ID), db: AsyncSession = DBSession):
    # 共享库的文件夹仅管理员可创建
    kb = await crud.get_knowledge_base(db, body.knowledge_base_id)
    if kb and kb.is_shared and not _is_admin(user_id):
        raise HTTPException(403, "共享库的文件夹仅管理员可创建")
    try:
        return await crud.create_folder(db, body.name, body.parent_id, body.knowledge_base_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@folder_router.put("/{folder_id}", response_model=schemas.FolderResponse)
async def rename_folder(folder_id: str, body: schemas.FolderRename, user_id: str = Query(default=DEFAULT_USER_ID), db: AsyncSession = DBSession):
    folder = await crud.get_folder(db, folder_id)
    if not folder:
        raise HTTPException(404, "文件夹不存在")
    kb = await crud.get_knowledge_base(db, folder.knowledge_base_id)
    if kb and kb.is_shared and not _is_admin(user_id):
        raise HTTPException(403, "共享库的文件夹仅管理员可操作")
    folder = await crud.update_folder(db, folder_id, body.name)
    return folder


@folder_router.delete("/{folder_id}")
async def delete_folder(folder_id: str, user_id: str = Query(default=DEFAULT_USER_ID), db: AsyncSession = DBSession):
    folder = await crud.get_folder(db, folder_id)
    if not folder:
        raise HTTPException(404, "文件夹不存在")
    kb = await crud.get_knowledge_base(db, folder.knowledge_base_id)
    if kb and kb.is_shared and not _is_admin(user_id):
        raise HTTPException(403, "共享库的文件夹仅管理员可操作")
    ok = await crud.delete_folder(db, folder_id)
    if not ok:
        raise HTTPException(404, "文件夹不存在")
    return {"ok": True}


# ═══════════════ Tags ═══════════════

@tag_router.get("", response_model=list[schemas.TagResponse])
async def list_tags(kb_id: str = Query(...), db: AsyncSession = DBSession):
    return await crud.get_tags(db, kb_id)


@tag_router.post("", response_model=schemas.TagResponse)
async def create_tag(body: schemas.TagCreate, user_id: str = Query(default=DEFAULT_USER_ID), db: AsyncSession = DBSession):
    kb = await crud.get_knowledge_base(db, body.knowledge_base_id)
    if kb and kb.is_shared and not _is_admin(user_id):
        raise HTTPException(403, "共享库的标签仅管理员可创建")
    return await crud.create_tag(db, body.name, body.knowledge_base_id)


@tag_router.delete("/{tag_id}")
async def delete_tag(tag_id: str, user_id: str = Query(default=DEFAULT_USER_ID), db: AsyncSession = DBSession):
    ok = await crud.delete_tag(db, tag_id)
    if not ok:
        raise HTTPException(404, "标签不存在")
    return {"ok": True}


# ═══════════════ Papers ═══════════════

@router.get("", response_model=schemas.PaperListResponse)
async def list_papers(
    kb_id: str = Query(...),
    folder_id: str | None = Query(None),
    keyword: str = Query(default=""),
    tag: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = DBSession,
):
    papers, total = await crud.get_papers(db, kb_id, folder_id, keyword, tag, page, page_size)
    paper_responses = [await crud.paper_to_response(db, p) for p in papers]
    return {"papers": paper_responses, "total": total}


@router.get("/{paper_id}", response_model=schemas.PaperDetail)
async def get_paper(paper_id: str, db: AsyncSession = DBSession):
    paper = await crud.get_paper(db, paper_id)
    if not paper:
        raise HTTPException(404, "论文不存在")
    resp = await crud.paper_to_response(db, paper)
    resp["md_content"] = paper.md_content or ""
    return resp


@router.post("/upload", response_model=schemas.PaperResponse)
async def upload_paper(
    title: str = Query(default=""),
    folder_id: str = Query(default=None),
    kb_id: str = Query(...),
    pdf_file: UploadFile = File(None),
    db: AsyncSession = DBSession,
):
    if not pdf_file:
        raise HTTPException(400, "请上传 PDF 文件")

    filename = pdf_file.filename or "unknown.pdf"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{ts}_{filename}"

    pdf_upload_dir = utils.ensure_upload_dir("pdfs")
    pdf_path = os.path.join(pdf_upload_dir, safe_name)
    pdf_bytes = await pdf_file.read()
    async with aiofiles.open(pdf_path, "wb") as f:
        await f.write(pdf_bytes)

    # 计算 MD5
    file_md5 = hashlib.md5(pdf_bytes).hexdigest()

    # 验证 KB 存在
    kb = await crud.get_knowledge_base(db, kb_id)
    if not kb:
        raise HTTPException(400, "知识库不存在")

    # 共享库 MD5 去重
    if kb.is_shared:
        dup = await crud.check_duplicate_md5(db, kb_id, file_md5)
        if dup:
            if dup.review_status == "pending":
                # 替换旧的待审核论文
                await crud.delete_paper(db, dup.id)
            else:
                # 删除刚上传的文件
                try: os.unlink(pdf_path)
                except OSError: pass
                raise HTTPException(400, f"该论文已存在于共享库中：{dup.title or dup.filename}")

    # 验证 folder_id
    if folder_id is not None:
        folder = await crud.get_folder(db, folder_id)
        if not folder:
            raise HTTPException(400, "目标文件夹不存在")

    # 共享库上传设为 pending 审核状态
    review_status = "pending" if kb.is_shared else "none"

    paper = await crud.create_paper(
        db, title=title, filename=filename,
        pdf_path=pdf_path, folder_id=folder_id, kb_id=kb_id,
        file_md5=file_md5, review_status=review_status,
    )
    paper.status = "uploaded"
    await db.commit()
    paper = await crud.get_paper(db, paper.id)
    return await crud.paper_to_response(db, paper)


@router.post("/{paper_id}/parse")
async def parse_paper(paper_id: str, db: AsyncSession = DBSession):
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
            async with async_session() as s2:
                p = await crud.get_paper(s2, paper_id)
                if p: p.status = "parse_failed"; await s2.commit()
            yield f"data: {_json.dumps({'stage': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n".encode("utf-8")
            return

        async with async_session() as s2:
            p = await crud.get_paper(s2, paper_id)
            if p:
                p.md_content = md_content
                p.mineru_batch_id = batch_id
                p.status = "parsed"
                await s2.commit()
                # 只有审核通过 / 私有库的才入索引
                if p.review_status == "approved" or p.review_status == "none":
                    try:
                        await indexer.index_paper(p.id, p.title or p.filename, md_content, p.knowledge_base_id)
                    except Exception: pass

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{paper_id}/pdf")
async def get_paper_pdf(paper_id: str, db: AsyncSession = DBSession):
    paper = await crud.get_paper(db, paper_id)
    if not paper or not paper.pdf_path or not os.path.isfile(paper.pdf_path):
        raise HTTPException(404, "PDF文件不存在")
    return FileResponse(paper.pdf_path, media_type="application/pdf", filename=paper.filename, content_disposition_type="inline")

@router.put("/{paper_id}/title", response_model=schemas.PaperResponse)
async def update_title(paper_id: str, body: schemas.PaperCreate, user_id: str = Query(default=DEFAULT_USER_ID), db: AsyncSession = DBSession):
    paper = await crud.get_paper(db, paper_id)
    if not paper:
        raise HTTPException(404, "论文不存在")
    # 共享库只有管理员能编辑
    kb = await crud.get_knowledge_base(db, paper.knowledge_base_id)
    if kb and kb.is_shared and not _is_admin(user_id):
        raise HTTPException(403, "共享库的论文标题仅管理员可编辑")
    paper = await crud.update_paper_title(db, paper_id, body.title)
    return await crud.paper_to_response(db, paper)


@router.delete("/{paper_id}")
async def delete_paper(paper_id: str, user_id: str = Query(default=DEFAULT_USER_ID), db: AsyncSession = DBSession):
    paper = await crud.get_paper(db, paper_id)
    if not paper:
        raise HTTPException(404, "论文不存在")
    kb = await crud.get_knowledge_base(db, paper.knowledge_base_id)
    if kb and kb.is_shared and not _is_admin(user_id):
        raise HTTPException(403, "共享库的论文仅管理员可删除")
    for p in [paper.pdf_path]:
        if p and os.path.isfile(p):
            try: os.unlink(p)
            except OSError: pass
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
    existing = await crud.get_summary(db, paper_id)
    if existing and existing.full_text:
        import json
        cached_data = json.dumps({"problem": existing.problem or "", "conclusion": existing.conclusion or "", "conditions": existing.conditions or "", "innovation": existing.innovation or "", "paper_type": existing.paper_type or "", "full_text": existing.full_text or ""})
        async def cached_stream():
            yield f"data: __CACHED__{cached_data}\n\n".encode("utf-8")
            yield f"data: [DONE]\n\n".encode("utf-8")
        return StreamingResponse(cached_stream(), media_type="text/event-stream")
    content = paper.md_content
    if not content:
        raise HTTPException(400, "没有可用的论文内容")
    async def event_stream():
        full_text = ""
        async for chunk in service.stream_summarize(content, db):
            if chunk.startswith("__DONE__"):
                full_text = chunk[7:]; break
            yield f"data: {json.dumps(chunk)}\n\n".encode("utf-8")
        sections = service.parse_summary_text(full_text)
        await crud.create_summary(db, paper_id, problem=sections.get("problem",""), conclusion=sections.get("conclusion",""), conditions=sections.get("conditions",""), innovation=sections.get("innovation",""), paper_type=sections.get("paper_type",""), full_text=full_text, model="llm", tokens=utils.count_tokens_approx(full_text))
        yield f"data: [DONE]\n\n".encode("utf-8")
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@router.get("/{paper_id}/summary", response_model=schemas.SummaryResponse)
async def get_paper_summary(paper_id: str, db: AsyncSession = DBSession):
    existing = await crud.get_summary(db, paper_id)
    if not existing:
        raise HTTPException(404, "暂无总结")
    return existing


@router.post("/compare")
async def compare_papers(body: schemas.CompareRequest, db: AsyncSession = DBSession):
    contents = []
    for pid in body.paper_ids:
        paper = await crud.get_paper(db, pid)
        if paper: contents.append({"title": paper.title or paper.filename, "content": paper.md_content})
    if len(contents) < 2: raise HTTPException(400, "至少需要2篇论文进行对比")
    async def event_stream():
        async for chunk in service.stream_compare(contents, db): yield f"data: {json.dumps(chunk)}\n\n".encode("utf-8")
        yield f"data: [DONE]\n\n".encode("utf-8")
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/{paper_id}/extract", response_model=list[schemas.ExtractionResponse])
async def extract_paper_info(paper_id: str, body: schemas.ExtractRequest, db: AsyncSession = DBSession):
    paper = await crud.get_paper(db, paper_id)
    if not paper: raise HTTPException(404, "论文不存在")
    content = paper.md_content
    if not content: raise HTTPException(400, "论文内容为空，请先解析")
    items = await service.extract_info(content, body.types, db)
    return await crud.save_extractions(db, paper_id, items)


@router.get("/{paper_id}/extractions", response_model=list[schemas.ExtractionResponse])
async def get_extractions(paper_id: str, db: AsyncSession = DBSession):
    return await crud.get_extractions(db, paper_id)


# ═══════════════ Admin Review ═══════════════

@admin_router.get("/review", response_model=schemas.ReviewListResponse)
async def list_pending(kb_id: str = Query(...), db: AsyncSession = DBSession):
    papers = await crud.get_pending_papers(db, kb_id)
    return {"papers": papers, "total": len(papers)}


@admin_router.post("/review/{paper_id}/approve")
async def approve_paper(paper_id: str, db: AsyncSession = DBSession):
    paper = await crud.approve_paper(db, paper_id)
    if not paper:
        raise HTTPException(404, "论文不存在")
    # 审核通过后入 ChromaDB
    if paper.md_content:
        try:
            await indexer.index_paper(paper.id, paper.title or paper.filename, paper.md_content, paper.knowledge_base_id)
        except Exception: pass
    return {"ok": True}


@admin_router.post("/review/{paper_id}/reject")
async def reject_paper(paper_id: str, body: schemas.ReviewRejectRequest, db: AsyncSession = DBSession):
    paper = await crud.reject_paper(db, paper_id, body.comment)
    if not paper:
        raise HTTPException(404, "论文不存在")
    return {"ok": True}
