from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload
from app.papers.model import Paper, Folder, Tag, paper_tags, Summary, Conversation, Extraction


# ── Folder helpers ──
MAX_FOLDER_DEPTH = 3


async def _get_folder_depth(db: AsyncSession, parent_id: int) -> int:
    """返回从根到 parent 的深度（根深度=0），parent_id=None 则深度=0"""
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


async def get_folder(db: AsyncSession, folder_id: int) -> Folder | None:
    return await db.get(Folder, folder_id)


# ── Folder CRUD ──

async def get_uncategorized_count(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(Paper.id)).where(Paper.folder_id == None))
    return result.scalar() or 0


async def get_folders(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(Folder).options(selectinload(Folder.children)).order_by(Folder.created_at.asc())
    )
    folders = list(result.unique().scalars().all())

    paper_counts = {}

    async def count_papers(folder):
        if folder.id in paper_counts:
            return paper_counts[folder.id]
        cnt_result = await db.execute(
            select(func.count(Paper.id)).where(Paper.folder_id == folder.id)
        )
        cnt = cnt_result.scalar() or 0
        for child in folder.children:
            cnt += await count_papers(child)
        paper_counts[folder.id] = cnt
        return cnt

    def build_tree(parent_id=None):
        nodes = []
        for f in folders:
            if f.parent_id == parent_id:
                cnt = paper_counts.get(f.id, 0)
                nodes.append({
                    "id": f.id,
                    "name": f.name,
                    "parent_id": f.parent_id,
                    "paper_count": cnt,
                    "children": build_tree(f.id),
                    "created_at": f.created_at,
                })
        return nodes

    for f in folders:
        await count_papers(f)

    return build_tree(None)


async def create_folder(db: AsyncSession, name: str, parent_id: int | None = None) -> Folder:
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


async def update_folder(db: AsyncSession, folder_id: int, name: str) -> Folder | None:
    folder = await db.get(Folder, folder_id)
    if folder:
        folder.name = name
        await db.commit()
        await db.refresh(folder)
    return folder


async def delete_folder(db: AsyncSession, folder_id: int) -> bool:
    folder = await db.get(Folder, folder_id)
    if not folder:
        return False
    await db.delete(folder)
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


async def delete_tag(db: AsyncSession, tag_id: int) -> bool:
    tag = await db.get(Tag, tag_id)
    if not tag:
        return False
    await db.delete(tag)
    await db.commit()
    return True


# ── Paper CRUD (modified) ──
async def create_paper(
    db: AsyncSession, title: str, filename: str,
    md_path: str, json_path: str, md_content: str,
    folder_id: int | None = None, pdf_path: str = "",
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
    keyword: str = "", folder_id: int | None = None, tag: str = "",
) -> tuple[list[Paper], int]:
    q = select(Paper).options(selectinload(Paper.tags), selectinload(Paper.folder))
    count_q = select(func.count(Paper.id))

    if keyword:
        q = q.where(Paper.title.contains(keyword))
        count_q = count_q.where(Paper.title.contains(keyword))
    if folder_id == -1:
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
    papers = list(result.unique().scalars().all())
    return papers, total


async def get_paper(db: AsyncSession, paper_id: int) -> Paper | None:
    result = await db.execute(
        select(Paper)
        .options(selectinload(Paper.tags), selectinload(Paper.folder))
        .where(Paper.id == paper_id)
    )
    return result.unique().scalar_one_or_none()


async def update_paper_title(db: AsyncSession, paper_id: int, title: str) -> Paper | None:
    paper = await get_paper(db, paper_id)
    if paper:
        paper.title = title
        await db.commit()
        paper = await get_paper(db, paper_id)
    return paper


async def move_paper(db: AsyncSession, paper_id: int, folder_id: int | None) -> Paper | None:
    paper = await get_paper(db, paper_id)
    if not paper:
        return None
    # validate folder exists if not moving to uncategorized
    if folder_id is not None:
        folder = await db.get(Folder, folder_id)
        if not folder:
            raise ValueError('目标文件夹不存在')
    paper.folder_id = folder_id
    await db.commit()
    paper = await get_paper(db, paper_id)
    return paper


async def delete_paper(db: AsyncSession, paper_id: int) -> bool:
    paper = await get_paper(db, paper_id)
    if paper:
        await db.delete(paper)
        await db.commit()
        return True
    return False


async def set_paper_tags(db: AsyncSession, paper_id: int, tag_ids: list[int]) -> Paper | None:
    paper = await get_paper(db, paper_id)
    if not paper:
        return None
    if tag_ids:
        tag_result = await db.execute(select(Tag).where(Tag.id.in_(tag_ids)))
        paper.tags = list(tag_result.scalars().all())
    else:
        paper.tags = []
    await db.commit()
    paper = await get_paper(db, paper_id)
    return paper


# ── Summary ──
async def create_summary(db: AsyncSession, paper_id: int, **kwargs) -> Summary:
    summary = Summary(paper_id=paper_id, **kwargs)
    db.add(summary)
    await db.commit()
    await db.refresh(summary)
    return summary


async def get_summary(db: AsyncSession, paper_id: int) -> Summary | None:
    result = await db.execute(
        select(Summary).where(Summary.paper_id == paper_id).order_by(Summary.created_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def delete_summaries_for_paper(db: AsyncSession, paper_id: int):
    await db.execute(delete(Summary).where(Summary.paper_id == paper_id))
    await db.commit()


# ── Conversation ──
async def add_conversation(db: AsyncSession, paper_id: int, role: str, content: str, tokens: int = 0) -> Conversation:
    conv = Conversation(paper_id=paper_id, role=role, content=content, tokens=tokens)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


async def get_conversations(db: AsyncSession, paper_id: int, limit: int = 50) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.paper_id == paper_id)
        .order_by(Conversation.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ── Extraction ──
async def save_extractions(db: AsyncSession, paper_id: int, results: list[dict]) -> list[Extraction]:
    objs = []
    for item in results:
        obj = Extraction(paper_id=paper_id, type=item["type"], content=item["content"])
        db.add(obj)
        objs.append(obj)
    await db.commit()
    for o in objs:
        await db.refresh(o)
    return objs


async def get_extractions(db: AsyncSession, paper_id: int) -> list[Extraction]:
    result = await db.execute(select(Extraction).where(Extraction.paper_id == paper_id))
    return list(result.scalars().all())


# ── Helper ──
def paper_to_response(paper: Paper) -> dict:
    return {
        "id": paper.id,
        "title": paper.title,
        "filename": paper.filename,
        "md_path": paper.md_path,
        "json_path": paper.json_path,
        "pdf_path": paper.pdf_path or "",
        "status": paper.status,
        "folder_id": paper.folder_id,
        "folder_name": paper.folder.name if paper.folder else None,
        "tags": [{"id": t.id, "name": t.name} for t in (paper.tags or [])],
        "created_at": paper.created_at,
    }