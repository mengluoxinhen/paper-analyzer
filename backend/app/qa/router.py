import json
import re
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.deps import DBSession
from app.papers.model import Paper
from app.qa import schemas, embedder, indexer

router = APIRouter(prefix="/api/qa", tags=["qa"])

# Dynamic paper topics cache (cleared on rebuild)
_paper_topics_cache = None


async def _get_paper_topics(db) -> str:
    global _paper_topics_cache
    if _paper_topics_cache is not None:
        return _paper_topics_cache

    # Extract paper descriptions: prefer first heading from content, fallback to filename
    from sqlalchemy import select
    from app.papers.model import Paper
    result = await db.execute(
        select(Paper.title, Paper.filename, Paper.md_content)
        .where(Paper.md_content != "")
    )
    rows = result.all()

    titles = []
    for row in rows:
        if row.title and row.title.strip():
            titles.append(row.title)
        elif row.md_content:
            m = re.search(r"^# (.+)", row.md_content, re.MULTILINE)
            if m:
                titles.append(m.group(1).strip()[:120])
            else:
                titles.append(row.filename)
        else:
            titles.append(row.filename)

    if not titles:
        _paper_topics_cache = "academic research papers"
        return _paper_topics_cache

    # Use LLM to summarize titles into a topic/keyword list
    try:
        from app.papers.service import _get_llm_config
        from openai import AsyncOpenAI

        cfg = await _get_llm_config(db)
        client = AsyncOpenAI(api_key=cfg["api_key"], base_url=cfg["api_base"])

        title_list = "\n".join(f"- {t}" for t in titles[:50])
        resp = await client.chat.completions.create(
            model=cfg["model"],
            messages=[{
                "role": "user",
                "content": (
                    "Below are titles of academic papers in a database. "
                    "Summarize them into a concise list of research topics and technical keywords "
                    "(5-10 items, comma-separated, in Chinese or English). Focus on domain-specific terms.\n\n"
                    f"Paper titles:\n{title_list}\n\nTopics and keywords:"
                )
            }],
            max_tokens=150,
            temperature=0.1,
        )
        _paper_topics_cache = resp.choices[0].message.content.strip()
        if not _paper_topics_cache:
            _paper_topics_cache = "; ".join(titles[:8])
    except Exception:
        _paper_topics_cache = "; ".join(titles[:8])

    return _paper_topics_cache

    from app.qa.indexer import _get_collection
    try:
        collection = _get_collection()
        all_data = collection.get(include=["metadatas"])
        titles = list(set(m["paper_title"] for m in all_data["metadatas"]))
    except Exception:
        titles = []

    if not titles:
        from sqlalchemy import select
        from app.papers.model import Paper
        result = await db.execute(
            select(Paper.title, Paper.filename).where(Paper.md_content != "")
        )
        rows = result.all()
        titles = [row.title or row.filename for row in rows]

    if not titles:
        _paper_topics_cache = "academic research papers"
        return _paper_topics_cache

    try:
        from app.papers.service import _get_llm_config
        from openai import AsyncOpenAI

        cfg = await _get_llm_config(db)
        client = AsyncOpenAI(api_key=cfg["api_key"], base_url=cfg["api_base"])

        title_list = "\n".join(f"- {t}" for t in titles[:50])
        resp = await client.chat.completions.create(
            model=cfg["model"],
            messages=[{
                "role": "user",
                "content": (
                    "Below are titles of academic papers in a database. "
                    "Summarize them into a concise list of research topics and technical keywords "
                    "(5-10 items, comma-separated). Focus on domain-specific terms.\n\n"
                    f"Paper titles:\n{title_list}\n\nTopics and keywords:"
                )
            }],
            max_tokens=150,
            temperature=0.1,
        )
        _paper_topics_cache = resp.choices[0].message.content.strip()
    except Exception:
        _paper_topics_cache = "; ".join(titles[:8])

    return _paper_topics_cache



_REWRITE_PROMPT = """You are a search query optimizer. The academic paper database contains papers about these topics:

{topics}

Given a question, rewrite it into a keyword-rich Chinese search query (15-30 words) optimized for embedding-based semantic retrieval. Add technical synonyms and related domain terms from the list above that are relevant to the question.

RULES:
- If the question is clearly NOT about any topic above (e.g. biology, medicine, finance), respond ONLY with "NOT_RELEVANT"
- If the question is already well-formed for the domain, add 2-3 related technical keywords to improve recall
- Always output something - never empty

Question: {question}
Optimized query:"""


async def _rewrite_query(question: str, db) -> str:
    """Use LLM to rewrite the query for better retrieval. Returns original if LLM fails."""
    try:
        from app.papers.service import _get_llm_config
        from openai import AsyncOpenAI

        cfg = await _get_llm_config(db)
        topics = await _get_paper_topics(db)
        prompt = _REWRITE_PROMPT.format(question=question, topics=topics)

        client = AsyncOpenAI(api_key=cfg["api_key"], base_url=cfg["api_base"])
        resp = await client.chat.completions.create(
            model=cfg["model"],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.1,
        )
        rewritten = resp.choices[0].message.content.strip()
        if len(rewritten) < 3:
            return question
        return rewritten
    except Exception:
        return question


def _build_qa_prompt(question: str, chunks: list[dict]) -> str:
    sources_text = ""
    for i, c in enumerate(chunks):
        sources_text += f"\n【来源{i+1}】《{c['paper_title']}》（{c['section']}节）\n{c['text']}\n"

    return f"""你是一个专业的学术论文问答助手。请根据以下从多篇论文中检索到的相关片段，回答用户的问题。

要求：
- 优先基于提供的论文片段作答，不要编造未出现的信息
- 回答中请标注信息来源，例如"根据《xxx》论文..."
- 如果检索到的片段不足以回答问题，请如实说明
- 回答要结构清晰、专业准确

【输出格式】只输出纯 Markdown 源码，不要添加任何开场白、过渡语、总结语或解释性文字。标题独占一行，标题与正文之间用空行分隔：

### 第一个要点

这是该要点的详细解释。其中使用 **粗体** 强调关键概念。

### 第二个要点

- 使用无序列表列出子项
- 每个子项中也可以包含 **粗体**

| 列A | 列B |
| --- | --- |
| 数据1 | 数据2 |

### 第三个要点

正文内容...

{sources_text}

---

用户问题：{question}"""

@router.post("/rebuild", response_model=schemas.QARebuildResponse)
async def rebuild_index(db: AsyncSession = DBSession):
    result = await db.execute(
        select(Paper).where(Paper.md_content != "")
    )
    papers = result.scalars().all()

    if not papers:
        return {"ok": True, "indexed_count": 0, "message": "没有已解析的论文"}

    paper_data = []
    for p in papers:
        content = p.md_content
        if content:
            paper_data.append({
                "id": p.id,
                "title": p.title or p.filename,
                "md_content": content,
            })

    if not paper_data:
        return {"ok": True, "indexed_count": 0, "message": "没有可索引的论文内容"}

    try:
        await indexer.rebuild_all_papers(paper_data)
        global _paper_topics_cache
        _paper_topics_cache = None
        return {"ok": True, "indexed_count": len(paper_data), "message": f"成功索引 {len(paper_data)} 篇论文"}
    except Exception as e:
        return {"ok": False, "indexed_count": 0, "message": f"索引重建失败: {str(e)}"}
