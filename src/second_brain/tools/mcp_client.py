"""Optional MCP-shaped adapters. Notion REST is the first server (read-only)."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
MAX_PAGES = 3
MAX_CHARS = 4000
MAX_BLOCKS = 50

TEXT_BLOCK_TYPES = frozenset(
    {
        "paragraph",
        "heading_1",
        "heading_2",
        "heading_3",
        "bulleted_list_item",
        "numbered_list_item",
        "quote",
        "callout",
        "to_do",
    }
)


def _enabled() -> bool:
    return os.getenv("ENABLE_MCP", "false").strip().lower() == "true"


def _token() -> str:
    return (os.getenv("NOTION_API_KEY") or "").strip()


def is_mcp_available() -> bool:
    return _enabled() and bool(_token())


def _notion_request(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    token = _token()
    if not token:
        raise RuntimeError("Missing Notion token")
    url = f"{NOTION_API}{path}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"Notion API {exc.code}: {detail or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Notion API unreachable: {exc.reason}") from exc
    if not raw:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        return {}
    return parsed


def mcp_status() -> dict[str, Any]:
    enabled = _enabled()
    configured = bool(_token())
    if not enabled:
        return {"enabled": False, "configured": configured, "ok": False, "error": ""}
    if not configured:
        return {
            "enabled": True,
            "configured": False,
            "ok": False,
            "error": "Missing Notion token",
        }
    try:
        _notion_request("GET", "/users/me")
        return {"enabled": True, "configured": True, "ok": True, "error": ""}
    except Exception as exc:
        logger.warning("Notion health check failed: %s", exc)
        return {
            "enabled": True,
            "configured": True,
            "ok": False,
            "error": str(exc),
        }


def _plain_text(rich: list[dict[str, Any]] | None) -> str:
    if not rich:
        return ""
    return "".join(str(part.get("plain_text") or "") for part in rich)


def _page_title(page: dict[str, Any]) -> str:
    props = page.get("properties") or {}
    if isinstance(props, dict):
        for prop in props.values():
            if not isinstance(prop, dict):
                continue
            if prop.get("type") == "title":
                title = _plain_text(prop.get("title"))
                if title.strip():
                    return title.strip()
    return "Untitled"


def _page_url(page: dict[str, Any]) -> str:
    url = str(page.get("url") or "").strip()
    if url:
        return url
    page_id = str(page.get("id") or "").replace("-", "")
    if page_id:
        return f"https://www.notion.so/{page_id}"
    return ""


def _block_text(block: dict[str, Any]) -> str:
    block_type = str(block.get("type") or "")
    if block_type not in TEXT_BLOCK_TYPES:
        return ""
    data = block.get(block_type) or {}
    if not isinstance(data, dict):
        return ""
    return _plain_text(data.get("rich_text"))


def _page_body(page_id: str) -> str:
    payload = _notion_request("GET", f"/blocks/{page_id}/children?page_size={MAX_BLOCKS}")
    lines: list[str] = []
    for block in payload.get("results") or []:
        if not isinstance(block, dict):
            continue
        text = _block_text(block).strip()
        if text:
            lines.append(text)
        if sum(len(line) for line in lines) >= MAX_CHARS:
            break
    body = "\n".join(lines).strip()
    return body[:MAX_CHARS]


def _page_to_document(page: dict[str, Any]) -> Document | None:
    if page.get("object") != "page":
        return None
    page_id = str(page.get("id") or "")
    if not page_id:
        return None
    title = _page_title(page)
    url = _page_url(page)
    try:
        body = _page_body(page_id)
    except Exception as exc:
        logger.warning("Notion page %s body failed: %s", page_id, exc)
        body = ""
    content = f"Title: {title}\nURL: {url}\n{body}".strip()
    return Document(
        page_content=content,
        metadata={
            "source": title,
            "source_path": url,
            "source_type": "mcp",
            "origin": "notion",
            "page": -1,
            "chunk_index": 0,
        },
    )


def search_mcp(query: str, max_results: int = MAX_PAGES) -> list[Document]:
    if not is_mcp_available():
        return []
    q = (query or "").strip()
    if not q:
        return []
    try:
        payload = _notion_request(
            "POST",
            "/search",
            {
                "query": q,
                "page_size": max(1, min(max_results, MAX_PAGES)),
                "filter": {"value": "page", "property": "object"},
            },
        )
    except Exception as exc:
        logger.warning("Notion search failed: %s", exc)
        return []

    documents: list[Document] = []
    for item in payload.get("results") or []:
        if not isinstance(item, dict):
            continue
        doc = _page_to_document(item)
        if doc is None:
            continue
        documents.append(doc)
        if len(documents) >= max_results:
            break

    logger.info("Notion MCP search: %d result(s) for '%s'", len(documents), q)
    return documents
