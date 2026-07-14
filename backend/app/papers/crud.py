from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, insert
from app.papers.model import Paper, Folder, Tag, KnowledgeBase, paper_tags, Summary, Conversation, Extraction, ChatSession
from app.qa import indexer
from difflib import SequenceMatcher


DEFAULT_USER_ID = "default_user"


# ── KnowledgeBase CRUD ──

async def get_knowledge_bases(db: AsyncSession, user_id: str = DEFAULT_USER_ID) -> list[dict]:
    """返回共享库 + 该用户的私有库"""
    result = await db.execute(
        select(KnowledgeBase).where(
            (KnowledgeBase.is_shared == True) | (KnowledgeBase.user_id == user_id)
        ).order_by(KnowledgeBase.is_shared.desc(), KnowledgeBase.created_at.asc())
    )
    kbs = list(result.scalars().all())
    out = []
    for kb in kbs:
        cnt_result = await db.execute(
            select(func.count(Paper.id)).where(Paper.knowledge_base_id == kb.id)
        )
        out.append({
            "id": kb.id,
            "name": kb.name,
            "description": kb.description or "",
            "user_id": kb.user_id,
            "is_shared": kb.is_shared,
            "paper_count": cnt_result.scalar() or 0,
            "created_at": kb.created_at,
        })
    return out


async def get_knowledge_base(db: AsyncSession, kb_id: str) -> KnowledgeBase | None:
    return await db.get(KnowledgeBase, kb_id)


async def create_knowledge_base(db: AsyncSession, name: str, description: str, user_id: str) -> KnowledgeBase:
    kb = KnowledgeBase(name=name, description=description, user_id=user_id, is_shared=False)
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return kb


async def update_knowledge_base(db: AsyncSession, kb_id: str, name: str | None = None, description: str | None = None) -> KnowledgeBase | None:
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        return None
    if name is not None:
        kb.name = name
    if description is not None:
        kb.description = description
    await db.commit()
    await db.refresh(kb)
    return kb


async def delete_knowledge_base(db: AsyncSession, kb_id: str) -> bool:
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb or kb.is_shared:
        return False

    paper_result = await db.execute(select(Paper.id).where(Paper.knowledge_base_id == kb_id))
    paper_ids = [row[0] for row in paper_result.fetchall()]

    await db.execute(delete(ChatSession).where(ChatSession.knowledge_base_id == kb_id))
    if paper_ids:
        await db.execute(delete(paper_tags).where(paper_tags.c.paper_id.in_(paper_ids)))
        await db.execute(delete(Extraction).where(Extraction.paper_id.in_(paper_ids)))
        await db.execute(delete(Conversation).where(Conversation.paper_id.in_(paper_ids)))
        await db.execute(delete(Summary).where(Summary.paper_id.in_(paper_ids)))
        await db.execute(delete(Paper).where(Paper.id.in_(paper_ids)))
    await db.execute(delete(Folder).where(Folder.knowledge_base_id == kb_id))
    await db.execute(delete(Tag).where(Tag.knowledge_base_id == kb_id))
    await db.delete(kb)
    await db.commit()

    import os, shutil
    from app.config import get_settings
    kb_chroma_dir = os.path.join(get_settings().qa_chroma_dir, f"kb_{kb_id}")
    if os.path.isdir(kb_chroma_dir):
        shutil.rmtree(kb_chroma_dir, ignore_errors=True)
    return True


# ── Folder helpers ──
MAX_FOLDER_DEPTH = 3


async def _get_folder_depth(db: AsyncSession, parent_id: str) -> int:
    depth = 0
    current_id = parent_id
    while current_id is not None:
        depth += 1
        if depth > MAX_FOLDER_DEPTH:
            break
        row = await db.get(Folder, current_id)
        if not row:
            break
        current_id = row.parent_id
    return depth


async def get_folder(db: AsyncSession, folder_id: str) -> Folder | None:
    return await db.get(Folder, folder_id)


async def _get_child_folder_ids(db: AsyncSession, folder_id: str) -> list[str]:
    ids = [folder_id]
    children_result = await db.execute(
        select(Folder.id).where(Folder.parent_id == folder_id)
    )
    for (child_id,) in children_result.fetchall():
        ids.extend(await _get_child_folder_ids(db, child_id))
    return ids


# ── Folder CRUD ──

async def get_uncategorized_count(db: AsyncSession, kb_id: str) -> int:
    result = await db.execute(
        select(func.count(Paper.id)).where(
            Paper.folder_id == None, Paper.knowledge_base_id == kb_id
        )
    )
    return result.scalar() or 0


async def get_folders(db: AsyncSession, kb_id: str) -> list[dict]:
    result = await db.execute(
        select(Folder).where(Folder.knowledge_base_id == kb_id).order_by(Folder.created_at.asc())
    )
    folders = list(result.scalars().all())

    paper_counts = {}
    for f in folders:
        descendant_ids = await _get_child_folder_ids(db, f.id)
        cnt_result = await db.execute(
            select(func.count(Paper.id)).where(Paper.folder_id.in_(descendant_ids))
        )
        paper_counts[f.id] = cnt_result.scalar() or 0

    def build_tree(parent_id=None):
        nodes = []
        for f in folders:
            if f.parent_id == parent_id:
                nodes.append({
                    "id": f.id, "name": f.name, "parent_id": f.parent_id,
                    "knowledge_base_id": f.knowledge_base_id,
                    "paper_count": paper_counts.get(f.id, 0),
                    "children": build_tree(f.id),
                    "created_at": f.created_at,
                })
        return nodes

    return build_tree(None)


async def create_folder(db: AsyncSession, name: str, parent_id: str | None, kb_id: str) -> Folder:
    if parent_id is not None:
        depth = await _get_folder_depth(db, parent_id)
        if depth >= MAX_FOLDER_DEPTH:
            raise ValueError(f"文件夹嵌套不能超过{MAX_FOLDER_DEPTH}层")
        parent = await db.get(Folder, parent_id)
        if not parent:
            raise ValueError("父文件夹不存在")
    folder = Folder(name=name, parent_id=parent_id, knowledge_base_id=kb_id)
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return folder


async def update_folder(db: AsyncSession, folder_id: str, name: str) -> Folder | None:
    folder = await db.get(Folder, folder_id)
    if folder:
        folder.name = name
        await db.commit()
        await db.refresh(folder)
    return folder


async def delete_folder(db: AsyncSession, folder_id: str) -> bool:
    folder = await db.get(Folder, folder_id)
    if not folder:
        return False
    kb_id = folder.knowledge_base_id
    all_folder_ids = await _get_child_folder_ids(db, folder_id)
    paper_result = await db.execute(select(Paper.id).where(Paper.folder_id.in_(all_folder_ids)))
    paper_ids = [row[0] for row in paper_result.fetchall()]
    if paper_ids:
        await db.execute(delete(paper_tags).where(paper_tags.c.paper_id.in_(paper_ids)))
        await db.execute(delete(Extraction).where(Extraction.paper_id.in_(paper_ids)))
        await db.execute(delete(Conversation).where(Conversation.paper_id.in_(paper_ids)))
        await db.execute(delete(Summary).where(Summary.paper_id.in_(paper_ids)))
        await db.execute(delete(Paper).where(Paper.id.in_(paper_ids)))
    for fid in reversed(all_folder_ids):
        await db.execute(delete(Folder).where(Folder.id == fid))
    await db.commit()
    if paper_ids:
        for pid in paper_ids:
            try: indexer.delete_paper_index(pid, kb_id)
            except Exception: pass
    return True


# ── Tag CRUD ──

async def get_tags(db: AsyncSession, kb_id: str) -> list[dict]:
    result = await db.execute(
        select(Tag).where(Tag.knowledge_base_id == kb_id).order_by(Tag.created_at.asc())
    )
    tags = list(result.scalars().all())
    out = []
    for t in tags:
        cnt_result = await db.execute(
            select(func.count()).select_from(paper_tags).where(paper_tags.c.tag_id == t.id)
        )
        out.append({
            "id": t.id, "name": t.name, "knowledge_base_id": t.knowledge_base_id,
            "paper_count": cnt_result.scalar() or 0, "created_at": t.created_at
        })
    return out


async def create_tag(db: AsyncSession, name: str, kb_id: str) -> Tag:
    tag = Tag(name=name, knowledge_base_id=kb_id)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


async def delete_tag(db: AsyncSession, tag_id: str) -> bool:
    tag = await db.get(Tag, tag_id)
    if not tag:
        return False
    await db.execute(delete(paper_tags).where(paper_tags.c.tag_id == tag_id))
    await db.delete(tag)
    await db.commit()
    return True


# ── Paper CRUD ──

async def create_paper(db: AsyncSession, title: str, filename: str,
                       pdf_path: str, folder_id: str | None = None,
                       kb_id: str | None = None, file_md5: str = "",
                       review_status: str = "none") -> Paper:
    paper = Paper(
        title=title, filename=filename, pdf_path=pdf_path,
        folder_id=folder_id, knowledge_base_id=kb_id or "",
        file_md5=file_md5, review_status=review_status
    )
    db.add(paper)
    await db.commit()
    await db.refresh(paper)
    return paper


async def get_papers(
    db: AsyncSession, kb_id: str,
    folder_id: str | None = None, keyword: str = "", tag: str = "",
    page: int = 1, page_size: int = 50,
) -> tuple[list[Paper], int]:
    query = select(Paper).where(Paper.knowledge_base_id == kb_id)
    count_query = select(func.count(Paper.id)).where(Paper.knowledge_base_id == kb_id)

    if folder_id is not None:
        descendant_ids = await _get_child_folder_ids(db, folder_id)
        query = query.where(Paper.folder_id.in_(descendant_ids))
        count_query = count_query.where(Paper.folder_id.in_(descendant_ids))

    if keyword:
        like = f"%{keyword}%"
        cond = Paper.title.ilike(like) | Paper.filename.ilike(like)
        query = query.where(cond)
        count_query = count_query.where(cond)

    if tag:
        query = query.join(paper_tags, Paper.id == paper_tags.c.paper_id).join(
            Tag, paper_tags.c.tag_id == Tag.id
        ).where(Tag.name == tag)
        count_query = count_query.join(
            paper_tags, Paper.id == paper_tags.c.paper_id
        ).join(Tag, paper_tags.c.tag_id == Tag.id).where(Tag.name == tag)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Paper.created_at.desc()).offset(
        (page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    papers = list(result.scalars().all())
    return papers, total


async def _get_paper_tags(db: AsyncSession, paper_id: str) -> list[Tag]:
    result = await db.execute(
        select(Tag).join(paper_tags, Tag.id == paper_tags.c.tag_id)
        .where(paper_tags.c.paper_id == paper_id)
    )
    return list(result.scalars().all())


async def _get_paper_folder(db: AsyncSession, folder_id: str | None) -> Folder | None:
    if folder_id is None:
        return None
    return await db.get(Folder, folder_id)


async def get_paper(db: AsyncSession, paper_id: str) -> Paper | None:
    return await db.get(Paper, paper_id)


async def update_paper_title(db: AsyncSession, paper_id: str, title: str) -> Paper | None:
    paper = await db.get(Paper, paper_id)
    if paper:
        paper.title = title
        await db.commit()
        await db.refresh(paper)
    return paper


async def move_paper(db: AsyncSession, paper_id: str, folder_id: str | None) -> Paper | None:
    paper = await db.get(Paper, paper_id)
    if not paper:
        return None
    if folder_id is not None:
        folder = await db.get(Folder, folder_id)
        if not folder:
            raise ValueError("目标文件夹不存在")
    paper.folder_id = folder_id
    await db.commit()
    await db.refresh(paper)
    return paper


async def delete_paper(db: AsyncSession, paper_id: str) -> bool:
    paper = await db.get(Paper, paper_id)
    if not paper:
        return False
    kb_id = paper.knowledge_base_id
    await db.execute(delete(paper_tags).where(paper_tags.c.paper_id == paper_id))
    await db.execute(delete(Extraction).where(Extraction.paper_id == paper_id))
    await db.execute(delete(Conversation).where(Conversation.paper_id == paper_id))
    await db.execute(delete(Summary).where(Summary.paper_id == paper_id))
    await db.delete(paper)
    await db.commit()
    try:
        indexer.delete_paper_index(paper_id, kb_id)
    except Exception:
        pass
    return True


async def set_paper_tags(db: AsyncSession, paper_id: str, tag_ids: list[str]) -> Paper | None:
    paper = await db.get(Paper, paper_id)
    if not paper:
        return None
    await db.execute(delete(paper_tags).where(paper_tags.c.paper_id == paper_id))
    for tid in tag_ids:
        await db.execute(
            insert(paper_tags).values(paper_id=paper_id, tag_id=tid).prefix_with("IGNORE")
        )
    await db.commit()
    return paper


async def check_duplicate_md5(db: AsyncSession, kb_id: str, file_md5: str) -> Paper | None:
    result = await db.execute(
        select(Paper).where(Paper.knowledge_base_id == kb_id, Paper.file_md5 == file_md5)
    )
    return result.scalar_one_or_none()


def _title_similar(a: str, b: str) -> bool:
    if not a or not b:
        return False
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio() > 0.85


# ── Review CRUD ──

async def get_pending_papers(db: AsyncSession, kb_id: str) -> list[dict]:
    result = await db.execute(
        select(Paper).where(
            Paper.knowledge_base_id == kb_id,
            Paper.review_status == "pending"
        ).order_by(Paper.created_at.desc())
    )
    papers = list(result.scalars().all())
    out = []
    for p in papers:
        is_dup = False
        dup_title = ""
        if p.title:
            approved = await db.execute(
                select(Paper.title).where(
                    Paper.knowledge_base_id == kb_id,
                    Paper.review_status == "approved"
                )
            )
            for (at,) in approved.fetchall():
                if at and _title_similar(p.title, at):
                    is_dup = True
                    dup_title = at
                    break
        out.append({
            "id": p.id, "title": p.title, "filename": p.filename,
            "created_at": p.created_at,
            "is_duplicate": is_dup, "duplicate_title": dup_title
        })
    return out


async def approve_paper(db: AsyncSession, paper_id: str) -> Paper | None:
    paper = await db.get(Paper, paper_id)
    if not paper:
        return None
    paper.review_status = "approved"
    paper.reviewed_at = func.now()
    await db.commit()
    await db.refresh(paper)
    return paper


async def reject_paper(db: AsyncSession, paper_id: str, comment: str) -> Paper | None:
    paper = await db.get(Paper, paper_id)
    if not paper:
        return None
    paper.review_status = "rejected"
    paper.review_comment = comment
    paper.reviewed_at = func.now()
    await db.commit()
    await db.refresh(paper)
    return paper


# ── Summary ──

async def create_summary(db: AsyncSession, paper_id: str, **kwargs) -> Summary:
    summary = Summary(paper_id=paper_id, **kwargs)
    db.add(summary)
    await db.commit()
    await db.refresh(summary)
    return summary


async def get_summary(db: AsyncSession, paper_id: str) -> Summary | None:
    result = await db.execute(
        select(Summary).where(Summary.paper_id == paper_id)
        .order_by(Summary.created_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


# ── Conversation ──

async def add_conversation(db: AsyncSession, paper_id: str, role: str, content: str, tokens: int = 0) -> Conversation:
    conv = Conversation(paper_id=paper_id, role=role, content=content, tokens=tokens)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


async def get_conversations(db: AsyncSession, paper_id: str, limit: int = 50) -> list[Conversation]:
    result = await db.execute(
        select(Conversation).where(Conversation.paper_id == paper_id)
        .order_by(Conversation.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


# ── Extraction ──

async def save_extractions(db: AsyncSession, paper_id: str, results: list[dict]) -> list[Extraction]:
    await db.execute(delete(Extraction).where(Extraction.paper_id == paper_id))
    objs = []
    for item in results:
        obj = Extraction(paper_id=paper_id, type=item["type"], content=item["content"])
        db.add(obj)
        objs.append(obj)
    await db.commit()
    for o in objs:
        await db.refresh(o)
    return objs


async def get_extractions(db: AsyncSession, paper_id: str) -> list[Extraction]:
    result = await db.execute(select(Extraction).where(Extraction.paper_id == paper_id))
    return list(result.scalars().all())


# ── Helper ──

async def paper_to_response(db: AsyncSession, paper: Paper) -> dict:
    tags = await _get_paper_tags(db, paper.id)
    folder = await _get_paper_folder(db, paper.folder_id)
    return {
        "id": paper.id,
        "title": paper.title,
        "filename": paper.filename,
        "pdf_path": paper.pdf_path or "",
        "status": paper.status,
        "folder_id": paper.folder_id,
        "folder_name": folder.name if folder else None,
        "knowledge_base_id": paper.knowledge_base_id,
        "review_status": paper.review_status,
        "file_md5": paper.file_md5 or "",
        "review_comment": paper.review_comment or "",
        "tags": [{"id": t.id, "name": t.name} for t in tags],
        "created_at": paper.created_at,
    }
