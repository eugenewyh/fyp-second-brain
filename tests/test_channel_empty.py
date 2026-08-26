"""Per-channel emptiness: no IDEA, no claims, no rememberable notes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from second_brain.memory.channel import channel_is_empty, idea_body  # noqa: E402


def test_missing_path_is_not_empty(tmp_path: Path):
    assert channel_is_empty(str(tmp_path / "nope")) is False
    assert channel_is_empty(None) is False


def test_stub_readme_only_is_empty(tmp_path: Path):
    topic = tmp_path / "Inbox"
    topic.mkdir()
    (topic / "README.md").write_text("# Inbox\n\nProject notes and sources.\n", encoding="utf-8")
    assert channel_is_empty(str(topic)) is True


def test_idea_makes_channel_ready(tmp_path: Path):
    topic = tmp_path / "FYP"
    topic.mkdir()
    (topic / "IDEA.md").write_text("# Idea\n\nTrack DLM vs JSON speed.\n", encoding="utf-8")
    assert idea_body(str(topic)) == "Track DLM vs JSON speed."
    assert channel_is_empty(str(topic)) is False


def test_blank_idea_header_is_empty(tmp_path: Path):
    topic = tmp_path / "FYP"
    topic.mkdir()
    (topic / "IDEA.md").write_text("# Idea\n\n", encoding="utf-8")
    assert channel_is_empty(str(topic)) is True


def test_pdf_note_makes_channel_ready(tmp_path: Path):
    topic = tmp_path / "FYP"
    topic.mkdir()
    (topic / "paper.pdf").write_bytes(b"%PDF-1.4")
    assert channel_is_empty(str(topic)) is False


def test_memory_claims_are_not_rememberable_notes_but_still_fill_channel(tmp_path: Path):
    topic = tmp_path / "FYP"
    claims = topic / "memory" / "claims"
    claims.mkdir(parents=True)
    (claims / "speed.md").write_text(
        "---\nid: speed\nclaim: JSON must survive decode.\nstatus: settled\norigin: dump\n---\n",
        encoding="utf-8",
    )
    assert channel_is_empty(str(topic)) is False
