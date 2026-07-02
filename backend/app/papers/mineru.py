"""
MinerU v4 batch upload API service.
"""
import asyncio
import os
import tempfile
import zipfile
from pathlib import Path
from typing import AsyncGenerator

import httpx
import aiofiles

from app.config import get_settings


class MinerUError(Exception):
    """MinerU API error."""


async def _post_batch_upload(
    files: list[dict],
    model_version: str = "vlm",
) -> dict:
    settings = get_settings()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.mineru_api_token}",
    }
    body = {"files": files, "model_version": model_version}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(settings.mineru_batch_url, headers=headers, json=body)
        if resp.status_code != 200:
            raise MinerUError(f"获取上传URL失败: HTTP {resp.status_code} {resp.text}")
        result = resp.json()
        if result.get("code") != 0:
            raise MinerUError(f"获取上传URL失败: {result.get('msg', 'unknown error')}")
        return result["data"]


async def _upload_file_to_url(file_url: str, file_path: str) -> None:
    try:
        async with aiofiles.open(file_path, "rb") as f:
            content = await f.read()
    except FileNotFoundError:
        raise MinerUError(f"文件未找到: {file_path}")
    async with httpx.AsyncClient(timeout=600.0) as client:
        resp = await client.put(file_url, content=content)
        if resp.status_code != 200:
            raise MinerUError(f"上传文件到OSS失败: HTTP {resp.status_code}")


def _extract_md_from_zip(zip_path: str) -> str:
    """Extract full.md from a zip file. Returns md content string."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        target = None
        for name in names:
            if name.endswith("full.md"):
                target = name
                break
        if not target:
            for name in names:
                if "full" in name.lower() and name.endswith(".md"):
                    target = name
                    break
        if not target:
            for name in names:
                if name.endswith(".md"):
                    target = name
                    break
        if not target:
            raise MinerUError(f"zip 中未找到 md 文件，内容: {names[:20]}")
        return zf.read(target).decode("utf-8", errors="replace")


async def _stream_download_zip(zip_url: str, tmp_path: str):
    """
    Download a zip file with streaming, yielding progress events.
    Yields: {"stage": "downloading", "message": str, "progress": int}
    """
    async with httpx.AsyncClient(timeout=600.0, follow_redirects=True) as client:
        async with client.stream("GET", zip_url) as resp:
            if resp.status_code != 200:
                raise MinerUError(f"下载结果失败: HTTP {resp.status_code}")

            content_length = int(resp.headers.get("content-length", 0))
            downloaded = 0

            with open(tmp_path, "wb") as f:
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if content_length > 0:
                        pct = 85 + int((downloaded / content_length) * 12)  # 85-97%
                        mb = downloaded / (1024 * 1024)
                        total_mb = content_length / (1024 * 1024)
                        yield {
                            "stage": "downloading",
                            "message": f"下载 {mb:.1f}/{total_mb:.1f} MB",
                            "progress": min(pct, 97),
                        }
                    else:
                        mb = downloaded / (1024 * 1024)
                        yield {
                            "stage": "downloading",
                            "message": f"已下载 {mb:.1f} MB",
                            "progress": min(85 + int(mb), 97),
                        }


async def parse_pdf_stream(
    pdf_path: str,
    file_name: str,
    data_id: str = "",
    model_version: str = "",
) -> AsyncGenerator[dict, None]:
    """
    Parse PDF with streaming progress updates.
    """
    settings = get_settings()
    if not settings.mineru_api_token:
        raise MinerUError("MINERU_API_TOKEN 未配置")

    if not model_version:
        model_version = settings.mineru_model_version
    if not data_id:
        data_id = Path(file_name).stem

    # Stage 1: get upload URL
    yield {"stage": "getting_url", "message": "获取上传链接...", "progress": 5}
    batch_data = await _post_batch_upload(
        files=[{"name": file_name, "data_id": data_id}],
        model_version=model_version,
    )
    batch_id = batch_data["batch_id"]
    file_urls = batch_data["file_urls"]
    if not file_urls:
        raise MinerUError("未获取到上传URL")

    # Stage 2: upload to OSS
    yield {"stage": "uploading", "message": "上传文件中...", "progress": 15}
    await _upload_file_to_url(file_urls[0], pdf_path)

    # Stage 3: poll for result
    yield {"stage": "parsing", "message": "已提交，等待解析...", "progress": 20}

    result_url = f"{settings.mineru_result_url.rstrip('/')}/{batch_id}"
    headers = {"Authorization": f"Bearer {settings.mineru_api_token}"}

    for attempt in range(settings.mineru_poll_max_retries):
        await asyncio.sleep(settings.mineru_poll_interval)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(result_url, headers=headers)
                if resp.status_code != 200:
                    continue
                result = resp.json()
                if result.get("code") != 0:
                    continue

                data = result.get("data", {})
                items = data.get("extract_result", [])
                if not items:
                    continue

                first = items[0]
                state = first.get("state", "")

                if state == "done":
                    zip_url = first.get("full_zip_url", "")
                    if not zip_url:
                        raise MinerUError("解析完成但未返回结果下载地址")

                    # Download zip with progress
                    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                        tmp_path = tmp.name
                    try:
                        async for prog in _stream_download_zip(zip_url, tmp_path):
                            yield prog
                        md_content = _extract_md_from_zip(tmp_path)
                    finally:
                        try:
                            os.unlink(tmp_path)
                        except OSError:
                            pass

                    print(f"[MinerU] batch_id={batch_id} md_length={len(md_content)} preview={md_content[:200]}")
                    yield {
                        "stage": "done",
                        "message": "完成",
                        "progress": 100,
                        "md_content": md_content,
                        "batch_id": batch_id,
                    }
                    return

                if state == "failed":
                    err = first.get("err_msg", "未知错误")
                    raise MinerUError(f"解析失败: {err}")

                if state == "running":
                    prog = first.get("extract_progress", {})
                    extracted = prog.get("extracted_pages", 0)
                    total = prog.get("total_pages", 0)
                    if total > 0:
                        pct = 20 + int((extracted / total) * 60)
                        yield {
                            "stage": "parsing",
                            "message": f"解析 {extracted}/{total} 页",
                            "progress": pct,
                        }
                    else:
                        yield {
                            "stage": "parsing",
                            "message": "解析中...",
                            "progress": 30 + min(attempt, 30),
                        }
                else:
                    msgs = {
                        "waiting-file": "等待文件就绪...",
                        "pending": "排队中...",
                        "converting": "格式转换...",
                    }
                    yield {
                        "stage": "parsing",
                        "message": msgs.get(state, state),
                        "progress": 20 + min(attempt, 10),
                    }
        except MinerUError:
            raise
        except Exception:
            continue

    raise MinerUError(f"解析超时: 已轮询 {settings.mineru_poll_max_retries} 次仍未完成")

