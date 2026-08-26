import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from second_brain.rag.chain import (
    ChatContext,
    ChatMessage,
    build_chat_system_content,
    chat_with_context,
    THIN_MEMORY_ANSWER,
)


def test_build_chat_system_content_without_note():
    content = build_chat_system_content(None)
    assert "personal assistant" in content.lower()
    assert "invent" in content.lower()


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


def test_thin_memory_refuses_without_llm(monkeypatch):
    from second_brain.memory.recall import MemoryContext
    from second_brain.rag import chain as chain_mod

    monkeypatch.setattr(chain_mod, "recall_for_query", lambda *a, **k: MemoryContext())

    def boom(*_a, **_k):
        raise AssertionError("Ask must not retrieve or call the LLM when memory is thin")

    monkeypatch.setattr(chain_mod, "retrieve", boom)
    monkeypatch.setattr(chain_mod, "invoke_llm", boom)

    resp = chat_with_context([ChatMessage(role="user", content="What is quantum computing?")])
    assert resp.thin_memory is True
    assert "no notes" in resp.answer.lower()
    assert "look it up" in resp.answer.lower()
    assert resp.answer == THIN_MEMORY_ANSWER


def test_ephemeral_attachment_skips_thin_memory(monkeypatch):
    from second_brain.memory.recall import MemoryContext
    from second_brain.rag import chain as chain_mod

    monkeypatch.setattr(chain_mod, "recall_for_query", lambda *a, **k: MemoryContext())
    monkeypatch.setattr(chain_mod, "retrieve", lambda *a, **k: [])

    class Dummy:
        content = "From the attached note, RAG still fabricates citations."

    monkeypatch.setattr(chain_mod, "invoke_llm", lambda *a, **k: Dummy())
    resp = chat_with_context(
        [ChatMessage(role="user", content="Summarise this")],
        context=ChatContext(note_excerpt="RAG still fabricates citations when the corpus is thin."),
    )
    assert resp.thin_memory is False
    assert "fabricates" in resp.answer.lower()


def test_useful_recall_injects_claims(monkeypatch):
    from second_brain.memory.recall import MemoryContext
    from second_brain.rag import chain as chain_mod

    memory = MemoryContext(
        text="[Project claims]\n- [[rag-cites]] RAG still fabricates citations",
        claim_count=1,
    )
    monkeypatch.setattr(chain_mod, "recall_for_query", lambda *a, **k: memory)
    monkeypatch.setattr(chain_mod, "retrieve", lambda *a, **k: [])
    captured: dict[str, str] = {}

    def fake_llm(messages, **_k):
        captured["prompt"] = "\n".join(getattr(m, "content", "") or "" for m in messages)

        class Dummy:
            content = "Your claim [[rag-cites]] says RAG still fabricates citations [1]."

        return Dummy()

    monkeypatch.setattr(chain_mod, "invoke_llm", fake_llm)
    resp = chat_with_context(
        [ChatMessage(role="user", content="Does RAG fabricate citations?")],
        project_path="/vault/proj",
    )
    assert resp.thin_memory is False
    assert "rag still fabricates" in captured["prompt"].lower()


def test_off_topic_ask_does_not_imply_notes(tmp_path, monkeypatch):
    from second_brain.memory.recall import MemoryContext
    from second_brain.rag import chain as chain_mod

    project = tmp_path / "dlm"
    project.mkdir()
    (project / "IDEA.md").write_text(
        "# Idea\n\nTrack diffusion language models and constrained decoding.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        chain_mod,
        "recall_for_query",
        lambda *a, **k: MemoryContext(claim_count=2, text="DiffusionGemma"),
    )

    def boom(*_a, **_k):
        raise AssertionError("Off-topic Ask must not retrieve or call the LLM")

    monkeypatch.setattr(chain_mod, "retrieve", boom)
    monkeypatch.setattr(chain_mod, "invoke_llm", boom)
    resp = chat_with_context(
        [ChatMessage(role="user", content="What is the best espresso machine for a small kitchen?")],
        project_path=str(project),
    )
    assert resp.thin_memory is True
    assert resp.answer == THIN_MEMORY_ANSWER


def test_memory_is_useful_requires_matching_claims():
    from second_brain.memory.recall import MemoryContext, memory_is_useful

    assert memory_is_useful(MemoryContext(has_chat_memory=True, claim_count=0)) is False
    assert memory_is_useful(MemoryContext(claim_count=1)) is True
    assert memory_is_useful(MemoryContext(), has_ephemeral=True) is True
    assert memory_is_useful(MemoryContext(claim_count=3), on_topic=False) is False