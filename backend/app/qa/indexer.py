import re
import chromadb
import os
from app.config import get_settings
from app.qa.embedder import get_embeddings

settings = get_settings()

_LOW_VALUE_SECTION_RE = re.compile(
    r"(?i)^(references?|acknowledg?ments?|ccs\s+concepts|keywords?|acm\s+reference|declarations?)\b"
)

_MAX_CHUNKS_PER_PAPER = 3


def _get_kb_chroma_dir(kb_id: str) -> str:
    """Get ChromaDB directory for a specific knowledge base."""
    return os.path.join(settings.qa_chroma_dir, f"kb_{kb_id}")


def _get_collection(kb_id: str):
    kb_dir = _get_kb_chroma_dir(kb_id)
    os.makedirs(kb_dir, exist_ok=True)
    client = chromadb.PersistentClient(path=kb_dir)
    return client.get_or_create_collection(
        name="paper_chunks",
        metadata={"hnsw:space": "cosine"},
    )


def chunk_paper(md_content: str, paper_id: str, paper_title: str, max_chunk_chars: int = 800, overlap_chars: int = 100) -> list[dict]:
    sections = re.split(r"\n(?=## )", md_content)
    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        title_match = re.match(r"^## (.+)", section)
        section_title = title_match.group(1).strip() if title_match else "正文"
        if _LOW_VALUE_SECTION_RE.match(section_title):
            continue
        if len(section) <= max_chunk_chars:
            chunks.append({"paper_id": paper_id, "paper_title": paper_title, "section": section_title, "text": section})
        else:
            paragraphs = section.split("\n\n")
            current = ""
            for para in paragraphs:
                if len(current) + len(para) > max_chunk_chars and current:
                    chunks.append({"paper_id": paper_id, "paper_title": paper_title, "section": section_title, "text": current.strip()})
                    overlap_text = current[-overlap_chars:] if len(current) > overlap_chars else current
                    current = overlap_text + "\n\n" + para
                else:
                    current = (current + "\n\n" + para).strip() if current else para
            if current.strip():
                chunks.append({"paper_id": paper_id, "paper_title": paper_title, "section": section_title, "text": current.strip()})
    return chunks


async def index_paper(paper_id: str, paper_title: str, md_content: str, kb_id: str):
    chunks = chunk_paper(md_content, paper_id, paper_title)
    if not chunks:
        return
    texts = [c["text"] for c in chunks]
    embeddings = await get_embeddings(texts)
    collection = _get_collection(kb_id)
    ids = [f"{paper_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"paper_id": c["paper_id"], "paper_title": c["paper_title"], "section": c["section"]} for c in chunks]
    collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)


def delete_paper_index(paper_id: str, kb_id: str):
    collection = _get_collection(kb_id)
    try:
        results = collection.get(where={"paper_id": paper_id})
        if results and results["ids"]:
            collection.delete(ids=results["ids"])
    except Exception:
        pass


async def rebuild_all_papers(db_papers: list[dict], kb_id: str):
    collection = _get_collection(kb_id)
    try:
        all_ids = collection.get()["ids"]
        if all_ids:
            collection.delete(ids=all_ids)
    except Exception:
        pass
    all_chunks = []
    for p in db_papers:
        if p.get("md_content"):
            chunks = chunk_paper(p["md_content"], p["id"], p.get("title") or p.get("filename", ""))
            all_chunks.extend(chunks)
    if not all_chunks:
        return
    texts = [c["text"] for c in all_chunks]
    embeddings = []
    for j in range(0, len(texts), 20):
        embeddings.extend(await get_embeddings(texts[j:j + 20]))
    ids = [f"{c['paper_id']}_chunk_{j}" for j, c in enumerate(all_chunks)]
    metadatas = [{"paper_id": c["paper_id"], "paper_title": c["paper_title"], "section": c["section"]} for c in all_chunks]
    collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)


def search_chunks(query_embedding: list[float], kb_id: str, top_k: int = 8) -> list[dict]:
    collection = _get_collection(kb_id)
    fetch_k = max(top_k * 3, top_k + 20)
    try:
        results = collection.query(query_embeddings=[query_embedding], n_results=fetch_k)
    except Exception:
        return []
    out = []
    paper_counts = {}
    if results and results["ids"] and results["ids"][0]:
        for i, chunk_id in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i] if results.get("metadatas") else {}
            doc = results["documents"][0][i] if results.get("documents") else ""
            pid = meta.get("paper_id", "")
            cnt = paper_counts.get(pid, 0)
            if cnt >= _MAX_CHUNKS_PER_PAPER:
                continue
            paper_counts[pid] = cnt + 1
            out.append({"chunk_id": chunk_id, "paper_id": pid, "paper_title": meta.get("paper_title", ""), "section": meta.get("section", ""), "text": doc, "score": results["distances"][0][i] if results.get("distances") else 0})
            if len(out) >= top_k:
                break
    return out
