import json
import traceback
from openai import AsyncOpenAI
from app.config import get_settings
from app.papers.utils import (
    build_summarize_prompt,
    build_chat_system_prompt,
    build_compare_prompt,
    build_extract_prompt,
    count_tokens_approx,
)


async def _get_llm_config(db=None):
    env = get_settings()
    config = {
        "api_base": env.llm_api_base,
        "api_key": env.llm_api_key,
        "model": env.llm_model,
        "max_tokens": env.llm_max_tokens,
        "temperature": env.llm_temperature,
    }
    if db:
        try:
            from app.settings.crud import get_all as get_all_settings
            rows = await get_all_settings(db)
            db_map = {r.key: r.value for r in rows}
            if db_map.get("llm_api_base"):
                config["api_base"] = db_map["llm_api_base"]
            if db_map.get("llm_api_key"):
                config["api_key"] = db_map["llm_api_key"]
            if db_map.get("llm_model"):
                config["model"] = db_map["llm_model"]
            if db_map.get("llm_max_tokens"):
                config["max_tokens"] = int(db_map["llm_max_tokens"])
            if db_map.get("llm_temperature"):
                config["temperature"] = float(db_map["llm_temperature"])
        except Exception:
            pass
    return config


async def _get_client(db=None):
    cfg = await _get_llm_config(db)
    return AsyncOpenAI(api_key=cfg["api_key"], base_url=cfg["api_base"]), cfg


async def stream_summarize(paper_content: str, db=None):
    client, cfg = await _get_client(db)
    prompt = build_summarize_prompt(paper_content)

    try:
        stream = await client.chat.completions.create(
            model=cfg["model"],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=cfg["max_tokens"],
            temperature=cfg["temperature"],
            stream=True,
        )

        full_text = ""
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                full_text += delta.content
                yield delta.content
        yield f"__DONE__{full_text}"
    except Exception as e:
        yield f"__DONE____ERROR__{str(e)}"



def parse_summary_text(full_text: str) -> dict:
    """Robust summary parser that handles various LLM header formats."""
    import re

    sections = {"problem": "", "conclusion": "", "conditions": ""}
    current = None

    # Expanded markers: (keyword, match_exact)
    markers = [
        # problem variants (longest first for priority)
        ("解决的问题", "problem"),
        ("研究的问题", "problem"),
        ("核心问题", "problem"),
        ("研究问题", "problem"),
        ("研究目的", "problem"),
        ("研究目标", "problem"),
        ("问题", "problem"),       # generic, must be exact (no suffix)
        # conclusion
        ("结论", "conclusion"),
        ("主要结论", "conclusion"),
        ("研究结论", "conclusion"),
        # conditions
        ("工况", "conditions"),
        ("实验条件", "conditions"),
        ("仿真条件", "conditions"),
        ("实验工况", "conditions"),
    ]

    for line in full_text.split("\n"):
        stripped = line.strip()
        matched = None

        # Try to match a header
        for keyword, key in markers:
            prefix2 = f"## {keyword}"
            prefix3 = f"### {keyword}"
            if stripped.startswith(prefix2) or stripped.startswith(prefix3):
                matched = key
                # Extract inline content after header (e.g., "## 解决的问题：xxx")
                rest = ""
                if stripped.startswith(prefix2):
                    rest = stripped[len(prefix2):]
                else:
                    rest = stripped[len(prefix3):]
                # Remove leading colon/separator and capture inline text
                inline = re.sub(r'^[：:]\s*', '', rest).strip()
                if inline:
                    sections[key] += inline + "\n"
                break

        if matched:
            current = matched
            continue

        if current and stripped:
            sections[current] += stripped + "\n"

    # If no sections found at all, treat entire text as problem
    if not any(sections.values()):
        sections["problem"] = full_text.strip()

    # If problem is still empty but full_text exists, try extracting from raw text
    if not sections["problem"].strip() and full_text:
        # Try to find "解决的问题" or similar in the raw text and extract content
        problem_patterns = [
            r'##\s*解决的问题\s*[：:]?\s*\n?(.*?)(?=##\s|###\s|\Z)',
            r'##\s*问题\s*[：:]?\s*\n?(.*?)(?=##\s|###\s|\Z)',
            r'##\s*研究问题\s*[：:]?\s*\n?(.*?)(?=##\s|###\s|\Z)',
            r'##\s*核心问题\s*[：:]?\s*\n?(.*?)(?=##\s|###\s|\Z)',
        ]
        for pat in problem_patterns:
            m = re.search(pat, full_text, re.DOTALL)
            if m and m.group(1).strip():
                sections["problem"] = m.group(1).strip()
                break

    return sections


async def stream_chat(paper_content: str, history: list[dict], user_message: str, db=None):
    client, cfg = await _get_client(db)
    system_prompt = build_chat_system_prompt(paper_content)

    messages = [{"role": "system", "content": system_prompt}]
    for h in history[-20:]:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": user_message})

    try:
        stream = await client.chat.completions.create(
            model=cfg["model"],
            messages=messages,
            max_tokens=cfg["max_tokens"],
            temperature=cfg["temperature"],
            stream=True,
        )

        full_text = ""
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                full_text += delta.content
                yield delta.content
        yield f"__DONE__{full_text}"
    except Exception as e:
        yield f"__DONE____ERROR__{str(e)}"


async def stream_compare(paper_contents: list[dict], db=None):
    client, cfg = await _get_client(db)
    prompt = build_compare_prompt(paper_contents)

    try:
        stream = await client.chat.completions.create(
            model=cfg["model"],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=cfg["max_tokens"],
            temperature=cfg["temperature"],
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
    except Exception as e:
        yield f"__ERROR__{str(e)}"


async def extract_info(paper_content: str, types: list[str], db=None) -> list[dict]:
    client, cfg = await _get_client(db)
    prompt = build_extract_prompt(paper_content, types)

    try:
        response = await client.chat.completions.create(
            model=cfg["model"],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=cfg["max_tokens"],
            temperature=0.3,
        )

        content = response.choices[0].message.content
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content
        data = json.loads(json_str)
        return data.get("items", [])
    except (json.JSONDecodeError, IndexError):
        return [{"type": "error", "content": {"raw": content}}]
    except Exception as e:
        return [{"type": "error", "content": {"raw": str(e)}}]
