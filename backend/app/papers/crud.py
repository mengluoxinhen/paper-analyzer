from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, insert
from app.papers.model import Paper, Folder, Tag, paper_tags, Summary, Conversation, Extraction


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
    """Recursively collect all descendant folder ids."""
    ids = [folder_id]
    children_result = await db.execute(
        select(Folder.id).where(Folder.parent_id == folder_id)
    )
    for (child_id,) in children_result.fetchall():
        ids.extend(await _get_child_folder_ids(db, child_id))
    return ids


# ── Folder CRUD ──

async def get_uncategorized_count(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(Paper.id)).where(Paper.folder_id == None))
    return result.scalar() or 0


async def get_folders(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(Folder).order_by(Folder.created_at.asc()))
    folders = list(result.scalars().all())

    # Preload all paper counts per folder
    paper_counts = {}
    all_folders = {f.id: f for f in folders}
    for f in folders:
        # Count papers directly in this folder plus children
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
                    "paper_count": paper_counts.get(f.id, 0),
                    "children": build_tree(f.id),
                    "created_at": f.created_at,
                })
        return nodes

    return build_tree(None)


async def create_folder(db: AsyncSession, name: str, parent_id: str | None = None) -> Folder:
    if parent_id is not None:
        depth = await _get_folder_depth(db, parent_id)
        if depth >= MAX_FOLDER_DEPTH:
            raise ValueError(f"文件夹嵌套不能超过{MAX_FOLDER_DEPTH}层")
        parent = await db.get(Folder, parent_id)
        if not parent:
            raise ValueError("父文件夹不存在")
    folder = Folder(name=name, parent_id=parent_id)
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

    # Collect all descendant folder ids + self
    all_folder_ids = await _get_child_folder_ids(db, folder_id)

    # Find all papers in these folders
    paper_result = await db.execute(
        select(Paper.id).where(Paper.folder_id.in_(all_folder_ids))
    )
    paper_ids = [row[0] for row in paper_result.fetchall()]

    # Delete children: paper_tags, extractions, conversations, summaries, papers
    if paper_ids:
        await db.execute(delete(paper_tags).where(paper_tags.c.paper_id.in_(paper_ids)))
        await db.execute(delete(Extraction).where(Extraction.paper_id.in_(paper_ids)))
        await db.execute(delete(Conversation).where(Conversation.paper_id.in_(paper_ids)))
        await db.execute(delete(Summary).where(Summary.paper_id.in_(paper_ids)))
        await db.execute(delete(Paper).where(Paper.id.in_(paper_ids)))

    # Delete child folders (bottom-up)
    for fid in reversed(all_folder_ids):
        await db.execute(delete(Folder).where(Folder.id == fid))

    await db.commit()
    return True


# ── Tag CRUD ──
async def get_tags(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(Tag).order_by(Tag.created_at.asc()))
    tags = list(result.scalars().all())
    out = []
    for t in tags:
        cnt_result = await db.execute(
            select(func.count()).select_from(paper_tags).where(paper_tags.c.tag_id == t.id)
        )
        cnt = cnt_result.scalar() or 0
        out.append({"id": t.id, "name": t.name, "paper_count": cnt, "created_at": t.created_at})
    return out


async def create_tag(db: AsyncSession, name: str) -> Tag:
    tag = Tag(name=name)
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
async def create_paper(
    db: AsyncSession, title: str, filename: str,
    pdf_path: str = "", folder_id: str | None = None,
    md_path: str = "", json_path: str = "", md_content: str = "",
) -> Paper:
    paper = Paper(
        title=title, filename=filename,
        md_path=md_path, json_path=json_path,
        md_content=md_content, pdf_path=pdf_path,
        folder_id=folder_id,
    )
    db.add(paper)
    await db.commit()
    await db.refresh(paper)
    return paper


async def get_papers(
    db: AsyncSession, page: int = 1, page_size: int = 20,
    keyword: str = "", folder_id: str | None = None, tag: str = "",
) -> tuple[list[Paper], int]:
    q = select(Paper)
    count_q = select(func.count(Paper.id))

    if keyword:
        q = q.where(Paper.title.contains(keyword))
        count_q = count_q.where(Paper.title.contains(keyword))
    if folder_id == "-1":
        q = q.where(Paper.folder_id == None)
        count_q = count_q.where(Paper.folder_id == None)
    elif folder_id is not None:
        q = q.where(Paper.folder_id == folder_id)
        count_q = count_q.where(Paper.folder_id == folder_id)
    if tag:
        tag_subq = select(paper_tags.c.paper_id).join(Tag).where(Tag.name == tag)
        q = q.where(Paper.id.in_(tag_subq))
        count_q = count_q.where(Paper.id.in_(tag_subq))

    q = q.order_by(Paper.created_at.desc()).offset((page - 1) * page_size).limit(page_size)

    total_result = await db.execute(count_q)
    total = total_result.scalar()

    result = await db.execute(q)
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
    # Manual cascade
    await db.execute(delete(paper_tags).where(paper_tags.c.paper_id == paper_id))
    await db.execute(delete(Extraction).where(Extraction.paper_id == paper_id))
    await db.execute(delete(Conversation).where(Conversation.paper_id == paper_id))
    await db.execute(delete(Summary).where(Summary.paper_id == paper_id))
    await db.delete(paper)
    await db.commit()
    return True


async def set_paper_tags(db: AsyncSession, paper_id: str, tag_ids: list[str]) -> Paper | None:
    paper = await db.get(Paper, paper_id)
    if not paper:
        return None
    # Delete existing tags
    await db.execute(delete(paper_tags).where(paper_tags.c.paper_id == paper_id))
    # Insert new tags
    for tid in tag_ids:
        await db.execute(
            insert(paper_tags).values(paper_id=paper_id, tag_id=tid).prefix_with("IGNORE")
        )
    await db.commit()
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
        "md_path": paper.md_path,
        "json_path": paper.json_path,
        "pdf_path": paper.pdf_path or "",
        "status": paper.status,
        "folder_id": paper.folder_id,
        "folder_name": folder.name if folder else None,
        "tags": [{"id": t.id, "name": t.name} for t in tags],
        "created_at": paper.created_at,
    }
