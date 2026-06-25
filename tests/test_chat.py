import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from second_brain.rag.chain import ChatContext, ChatMessage, build_chat_system_content


def test_build_chat_system_content_without_note():
    content = build_chat_system_content(None)
    assert "contextual research assistant" in content.lower()


def test_build_chat_system_content_with_note_and_selection():
    ctx = ChatContext(
        note_path="/vault/Notes.md",
        selected_text="important phrase",
        note_excerpt="First paragraph of the note.",
    )
    content = build_chat_system_content(ctx)
    assert "/vault/Notes.md" in content
    assert "important phrase" in content
    assert "First paragraph" in content


def test_build_chat_system_content_truncates_long_excerpt():
    ctx = ChatContext(note_excerpt="x" * 3000)
    content = build_chat_system_content(ctx)
    assert "…" in content
    assert len(content) < 3500


def test_chat_message_roles():
    messages = [
        ChatMessage(role="user", content="Hello"),
        ChatMessage(role="assistant", content="Hi there"),
    ]
    assert messages[0].role == "user"