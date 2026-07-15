import json
import re
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.deps import DBSession
from app.papers.model import Paper
from app.qa import schemas, embedder, indexer

router = APIRouter(prefix="/api/qa", tags=["qa"])

# KB-id-keyed cache for paper topics summary. Invalidated on index rebuild only.
_paper_topics_cache = {}


async def _get_paper_topics(db, kb_id: str) -> str:
    global _paper_topics_cache
    cache_key = kb_id
    if cache_key in _paper_topics_cache:
        return _paper_topics_cache[cache_key]

    from sqlalchemy import select
    from app.papers.model import Paper
    result = await db.execute(
        select(Paper.title, Paper.filename, Paper.md_content)
        .where(Paper.md_content != "", Paper.knowledge_base_id == kb_id)
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
        _paper_topics_cache[cache_key] = "academic research papers"
        return _paper_topics_cache[cache_key]
    try:
        from app.papers.service import _get_llm_config
        from openai import AsyncOpenAI
        cfg = await _get_llm_config(db)
        client = AsyncOpenAI(api_key=cfg["api_key"], base_url=cfg["api_base"])
        title_list = "\n".join(f"- {t}" for t in titles[:50])
        resp = await client.chat.completions.create(
            model=cfg["model"],
            messages=[{"role": "user", "content": f"Below are titles of academic papers in a database. Summarize them into a concise list of research topics and technical keywords (5-10 items, comma-separated, in Chinese or English).\n\nPaper titles:\n{title_list}\n\nTopics and keywords:"}],
            max_tokens=150, temperature=0.1,
        )
        _paper_topics_cache[cache_key] = resp.choices[0].message.content.strip()
        if not _paper_topics_cache[cache_key]:
            _paper_topics_cache[cache_key] = "; ".join(titles[:8])
    except Exception:
        _paper_topics_cache[cache_key] = "; ".join(titles[:8])
    return _paper_topics_cache[cache_key]


_REWRITE_PROMPT = """You are a search query optimizer. The academic paper database contains papers about these topics:

{topics}

Given a question, rewrite it into a keyword-rich Chinese search query (15-30 words) optimized for embedding-based semantic retrieval. Add technical synonyms and related domain terms from the list above that are relevant to the question.

RULES:
- If the question is clearly NOT about any topic above (e.g. biology, medicine, finance), respond ONLY with "NOT_RELEVANT"
- If the question is already well-formed for the domain, add 2-3 related technical keywords to improve recall
- Always output something - never empty

Question: {question}
Optimized query:"""


async def _rewrite_query(question: str, db, kb_id: str) -> str:
    try:
        from app.papers.service import _get_llm_config
        from openai import AsyncOpenAI
        cfg = await _get_llm_config(db)
        topics = await _get_paper_topics(db, kb_id)
        prompt = _REWRITE_PROMPT.format(question=question, topics=topics)
        client = AsyncOpenAI(api_key=cfg["api_key"], base_url=cfg["api_base"])
        resp = await client.chat.completions.create(model=cfg["model"], messages=[{"role": "user", "content": prompt}], max_tokens=100, temperature=0.1)
        rewritten = resp.choices[0].message.content.strip()
        if len(rewritten) < 3: return question
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
async def rebuild_index(kb_id: str = Query(...), db: AsyncSession = DBSession):
    result = await db.execute(
        select(Paper).where(Paper.md_content != "", Paper.knowledge_base_id == kb_id)
    )
    papers = result.scalars().all()
    if not papers:
        return {"ok": True, "indexed_count": 0, "message": "没有已解析的论文"}
    paper_data = [{"id": p.id, "title": p.title or p.filename, "md_content": p.md_content} for p in papers if p.md_content]
    if not paper_data:
        return {"ok": True, "indexed_count": 0, "message": "没有可索引的论文内容"}
    try:
        await indexer.rebuild_all_papers(paper_data, kb_id)
        global _paper_topics_cache
        _paper_topics_cache.pop(kb_id, None)
        return {"ok": True, "indexed_count": len(paper_data), "message": f"成功索引 {len(paper_data)} 篇论文"}
    except Exception as e:
        return {"ok": False, "indexed_count": 0, "message": f"索引重建失败: {str(e)}"}
