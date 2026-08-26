import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from second_brain.tools.mcp_client import mcp_status, search_mcp


SAMPLE_PAGE = {
    "object": "page",
    "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "url": "https://www.notion.so/aaaaaaaa",
    "properties": {
        "title": {
            "type": "title",
            "title": [{"plain_text": "Meeting notes"}],
        }
    },
}

SAMPLE_BLOCKS = {
    "results": [
        {
            "type": "paragraph",
            "paragraph": {"rich_text": [{"plain_text": "Hello from Notion"}]},
        },
        {
            "type": "heading_2",
            "heading_2": {"rich_text": [{"plain_text": "Next"}]},
        },
        {
            "type": "image",
            "image": {"type": "external"},
        },
    ]
}


def test_search_mcp_disabled(monkeypatch):
    monkeypatch.setenv("ENABLE_MCP", "false")
    monkeypatch.setenv("NOTION_API_KEY", "secret_test")
    assert search_mcp("anything") == []


def test_search_mcp_missing_token(monkeypatch):
    monkeypatch.setenv("ENABLE_MCP", "true")
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    assert search_mcp("anything") == []


def test_search_mcp_maps_pages(monkeypatch):
    monkeypatch.setenv("ENABLE_MCP", "true")
    monkeypatch.setenv("NOTION_API_KEY", "secret_test")

    def fake_request(method, path, body=None):
        if path == "/search":
            assert method == "POST"
            assert body and body.get("query") == "meeting"
            return {"results": [SAMPLE_PAGE]}
        if path.startswith("/blocks/"):
            return SAMPLE_BLOCKS
        raise AssertionError(f"unexpected path {path}")

    monkeypatch.setattr("second_brain.tools.mcp_client._notion_request", fake_request)
    docs = search_mcp("meeting")
    assert len(docs) == 1
    doc = docs[0]
    assert doc.metadata["source_type"] == "mcp"
    assert doc.metadata["origin"] == "notion"
    assert doc.metadata["source"] == "Meeting notes"
    assert doc.metadata["source_path"] == "https://www.notion.so/aaaaaaaa"
    assert "Hello from Notion" in doc.page_content
    assert "Next" in doc.page_content


def test_mcp_status_off(monkeypatch):
    monkeypatch.setenv("ENABLE_MCP", "false")
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    status = mcp_status()
    assert status["enabled"] is False
    assert status["configured"] is False
    assert status["ok"] is False


def test_mcp_status_missing_token(monkeypatch):
    monkeypatch.setenv("ENABLE_MCP", "true")
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    status = mcp_status()
    assert status["enabled"] is True
    assert status["configured"] is False
    assert "token" in status["error"].lower()


def test_mcp_status_ok(monkeypatch):
    monkeypatch.setenv("ENABLE_MCP", "true")
    monkeypatch.setenv("NOTION_API_KEY", "secret_test")
    monkeypatch.setattr(
        "second_brain.tools.mcp_client._notion_request",
        lambda method, path, body=None: {"id": "user"},
    )
    status = mcp_status()
    assert status["ok"] is True
    assert status["configured"] is True
    assert status["error"] == ""
