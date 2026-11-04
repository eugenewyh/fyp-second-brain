"""Auto-heal empty Chroma when vault files remain on disk."""

from __future__ import annotations

from pathlib import Path


def test_vault_has_ingestible_files(tmp_path: Path):
    from second_brain.memory import vault_index as vi

    assert vi.vault_has_ingestible_files(tmp_path) is False
    (tmp_path / "note.md").write_text("hello", encoding="utf-8")
    assert vi.vault_has_ingestible_files(tmp_path) is True


def test_ensure_vault_indexed_noop_when_populated(monkeypatch, tmp_path: Path):
    from second_brain.memory import vault_index as vi

    monkeypatch.setattr(vi, "collection_count", lambda: 12)
    called = {"ingest": 0}
    monkeypatch.setattr(vi, "ingest_directory", lambda _p: called.__setitem__("ingest", 1))
    assert vi.ensure_vault_indexed(tmp_path) == 12
    assert called["ingest"] == 0


def test_ensure_vault_indexed_reingests_when_empty(monkeypatch, tmp_path: Path):
    from second_brain.memory import vault_index as vi

    (tmp_path / "Coffee").mkdir()
    (tmp_path / "Coffee" / "water.md").write_text("150 ppm", encoding="utf-8")
    state = {"count": 0}

    def fake_count():
        return state["count"]

    def fake_ingest(_path):
        state["count"] = 7
        return 7

    monkeypatch.setattr(vi, "collection_count", fake_count)
    monkeypatch.setattr(vi, "ingest_directory", fake_ingest)
    assert vi.ensure_vault_indexed(tmp_path) == 7
    assert state["count"] == 7
