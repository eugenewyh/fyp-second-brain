"""Tests for daily review planning, digests, and scheduler helpers."""

from __future__ import annotations

import sys
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from second_brain.agent.daily_review import (
    find_changed_files,
    load_review_state,
    plan_daily_review,
    run_daily_review,
    save_review_state,
)
from second_brain.memory.digest import (
    collect_open_questions,
    get_digest,
    list_digests,
    list_learning_cards,
    parse_learning_card,
    write_daily_digest,
)
from sidecar.scheduler import (
    needs_catch_up,
    past_scheduled_hour,
    seconds_until_hour,
    should_auto_catch_up,
)


def _write_learning_card(path: Path, *, query: str, questions: list[str], day: str) -> None:
    qs = "\n".join(f"- {q}" for q in questions) or "- (none)"
    path.write_text(
        "\n".join(
            [
                "---",
                "id: abc123",
                f"date: {day}",
                f'query: "{query}"',
                "type: learning",
                "confidence: 0.7",
                "---",
                "",
                f"# Learning: {query}",
                "",
                "## Summary",
                f"Summary about {query}.",
                "",
                "## Key findings",
                "- Finding one is substantial enough",
                "",
                "## Open questions",
                qs,
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_find_changed_files_skips_digests_and_learnings(tmp_path: Path):
    docs = tmp_path / "documents"
    (docs / "notes").mkdir(parents=True)
    (docs / "memory" / "digests").mkdir(parents=True)
    (docs / "memory" / "learnings").mkdir(parents=True)
    (docs / "research").mkdir(parents=True)

    note = docs / "notes" / "alpha.md"
    note.write_text("# Alpha\n", encoding="utf-8")
    (docs / "memory" / "digests" / "2026-08-04.md").write_text("# d\n", encoding="utf-8")
    (docs / "memory" / "learnings" / "card.md").write_text("# c\n", encoding="utf-8")
    (docs / "research" / "report.md").write_text("# r\n", encoding="utf-8")

    since = datetime.now(timezone.utc) - timedelta(hours=1)
    found = find_changed_files(since=since, documents_dir=docs)
    names = {p.name for p in found}
    assert "alpha.md" in names
    assert "2026-08-04.md" not in names
    assert "card.md" not in names
    assert "report.md" in names

    topic = docs / "Citation"
    (topic / "briefs").mkdir(parents=True)
    (topic / "briefs" / "2026-08-17.md").write_text("# Morning Brief\n", encoding="utf-8")
    (topic / "instruction.md").write_text("# Watch\n", encoding="utf-8")
    (topic / "memory" / "claims").mkdir(parents=True)
    (topic / "memory" / "claims" / "c.md").write_text("# claim\n", encoding="utf-8")
    found2 = find_changed_files(since=since, documents_dir=docs)
    names2 = {p.name for p in found2}
    assert "2026-08-17.md" not in names2
    assert "instruction.md" not in names2
    assert "c.md" not in names2


def test_plan_daily_review_from_new_notes(tmp_path: Path, monkeypatch):
    docs = tmp_path / "documents"
    (docs / "notes").mkdir(parents=True)
    note = docs / "notes" / "quantum-notes.md"
    note.write_text("# Quantum\nSome ideas.\n", encoding="utf-8")

    import second_brain.agent.daily_review as dr
    import second_brain.memory.digest as digest_mod
    import second_brain.memory.learning as learning_mod

    monkeypatch.setattr(dr, "DOCUMENTS_DIR", docs)
    monkeypatch.setattr(digest_mod, "DOCUMENTS_DIR", docs)
    monkeypatch.setattr(learning_mod, "DOCUMENTS_DIR", docs)

    plan = plan_daily_review(
        documents_dir=docs,
        state={"last_run_date": None},
        max_goals=2,
    )
    assert plan.skip_reason is None
    assert plan.goals
    assert plan.goals[0].kind == "vault_changes"
    assert "quantum" in plan.goals[0].goal.lower()


def test_plan_daily_review_open_questions(tmp_path: Path, monkeypatch):
    docs = tmp_path / "documents"
    project = docs / "dlm"
    learnings = project / "memory" / "learnings"
    learnings.mkdir(parents=True)
    today = date.today().isoformat()
    _write_learning_card(
        learnings / f"{today}-prior.md",
        query="Prior topic",
        questions=["How does memory compound across sessions over long horizons?"],
        day=today,
    )

    import second_brain.agent.daily_review as dr
    import second_brain.memory.digest as digest_mod
    import second_brain.memory.learning as learning_mod

    monkeypatch.setattr(dr, "DOCUMENTS_DIR", docs)
    monkeypatch.setattr(digest_mod, "DOCUMENTS_DIR", docs)
    monkeypatch.setattr(learning_mod, "DOCUMENTS_DIR", docs)

    qs = collect_open_questions(project_path=str(project), limit=5)
    assert qs
    plan = plan_daily_review(
        project_path=str(project),
        documents_dir=docs,
        state={"last_run_date": today},
        max_goals=2,
    )
    assert any(g.kind == "open_question" for g in plan.goals)


def test_write_and_get_digest(tmp_path: Path, monkeypatch):
    docs = tmp_path / "documents"
    digests = docs / "memory" / "digests"
    digests.mkdir(parents=True)

    import second_brain.memory.digest as digest_mod

    monkeypatch.setattr(digest_mod, "DOCUMENTS_DIR", docs)
    monkeypatch.setattr(digest_mod, "digests_dir", lambda project_path=None: digests)

    path = write_daily_digest(
        digest_date=date(2026, 8, 4),
        cards=[
            {
                "query": "Agents",
                "summary": "Agents specialize well.",
                "key_findings": ["Specialization reduces errors"],
                "open_questions": ["How to evaluate long-horizon goals?"],
                "date": "2026-08-04",
            }
        ],
        goals_run=[{"goal": "Review agents", "confidence": 0.8}],
        new_files=["/tmp/note.md"],
        ingest=False,
    )
    assert path.is_file()
    assert "Daily brief" in path.read_text(encoding="utf-8")

    loaded = get_digest(date(2026, 8, 4))
    assert loaded is not None
    assert loaded["date"] == "2026-08-04"
    assert list_digests(limit=5)


def test_parse_learning_card(tmp_path: Path):
    path = tmp_path / "card.md"
    _write_learning_card(
        path,
        query="Test query",
        questions=["What remains unknown about X?"],
        day="2026-08-04",
    )
    card = parse_learning_card(path)
    assert card is not None
    assert card["query"] == "Test query"
    assert card["open_questions"]


def test_list_learning_cards_includes_agent_scoped(tmp_path: Path):
    topic = tmp_path / "Coffee"
    legacy = topic / "memory" / "learnings"
    agent = topic / "memory" / "agents" / "sess-abc" / "learnings"
    legacy.mkdir(parents=True)
    agent.mkdir(parents=True)
    _write_learning_card(
        legacy / "legacy.md",
        query="Legacy card",
        questions=["What about legacy learnings still?"],
        day="2026-08-04",
    )
    _write_learning_card(
        agent / "agent.md",
        query="Agent card",
        questions=["What about agent-scoped learnings still?"],
        day="2026-08-05",
    )
    cards = list_learning_cards(project_path=str(topic), limit=10)
    queries = {c["query"] for c in cards}
    assert "Legacy card" in queries
    assert "Agent card" in queries


def test_run_daily_review_with_stub(tmp_path: Path, monkeypatch):
    docs = tmp_path / "documents"
    (docs / "notes").mkdir(parents=True)
    (docs / "notes" / "idea.md").write_text("# Idea\nContent here.\n", encoding="utf-8")
    state_path = tmp_path / "digest_state.json"

    import second_brain.agent.daily_review as dr
    import second_brain.memory.digest as digest_mod
    import second_brain.memory.learning as learning_mod

    monkeypatch.setattr(dr, "DOCUMENTS_DIR", docs)
    monkeypatch.setattr(dr, "DAILY_REVIEW_ENABLED", True)
    monkeypatch.setattr(digest_mod, "DOCUMENTS_DIR", docs)
    monkeypatch.setattr(learning_mod, "DOCUMENTS_DIR", docs)

    def fake_research(query, retrieval_scope="local", project_path=None, persist_memory=True):
        # Simulate persist by writing a learning card
        learnings = docs / "memory" / "learnings"
        learnings.mkdir(parents=True)
        day = datetime.now(timezone.utc).date().isoformat()
        card_path = learnings / f"{day}-stub.md"
        _write_learning_card(
            card_path,
            query=query[:40],
            questions=["Follow-up gap?"],
            day=day,
        )
        return {
            "query": query,
            "confidence": 0.72,
            "open_questions": ["Follow-up gap?"],
            "learning_path": str(card_path),
            "report_path": None,
            "report": "## Executive Summary\nStub.\n",
        }

    result = run_daily_review(
        reason="test",
        force=True,
        state_path=state_path,
        run_research_fn=fake_research,
    )
    assert result["last_run_status"] == "completed"
    assert result["digest_path"]
    assert Path(result["digest_path"]).is_file()
    assert load_review_state(state_path)["last_run_status"] == "completed"

    # Second run same day without force → skip
    again = run_daily_review(
        reason="test",
        force=False,
        state_path=state_path,
        run_research_fn=fake_research,
    )
    assert again.get("skipped_reason") == "already_ran_today"


def test_run_daily_review_watch_does_not_inject_research(tmp_path: Path, monkeypatch):
    """Scheduled Watch uses run_watch/harness — not the single-pass research stub."""
    docs = tmp_path / "documents"
    topic = docs / "Citation"
    topic.mkdir(parents=True)
    state_path = tmp_path / "digest_state.json"

    import second_brain.agent.daily_review as dr
    import second_brain.memory.digest as digest_mod
    import second_brain.memory.learning as learning_mod
    from second_brain.agent.daily_review import ReviewGoal, ReviewPlan

    monkeypatch.setattr(dr, "DOCUMENTS_DIR", docs)
    monkeypatch.setattr(dr, "DAILY_REVIEW_ENABLED", True)
    monkeypatch.setattr(digest_mod, "DOCUMENTS_DIR", docs)
    monkeypatch.setattr(learning_mod, "DOCUMENTS_DIR", docs)
    monkeypatch.setattr(
        dr,
        "plan_daily_review",
        lambda **kwargs: ReviewPlan(
            goals=[
                ReviewGoal(
                    goal="Watch citation metrics",
                    kind="watch",
                    source=str(topic),
                    watch_id="",
                )
            ],
            new_files=[],
            open_questions=[],
            skip_reason=None,
        ),
    )
    monkeypatch.setattr(dr, "write_daily_digest", lambda **kwargs: tmp_path / "d.md")

    called: dict = {}

    def fake_watch(project_path, **kwargs):
        called["kwargs"] = kwargs
        called["path"] = str(project_path)
        return {
            "query": "Watch citation metrics",
            "confidence": 0.8,
            "open_questions": [],
            "learning_path": None,
            "report_path": None,
        }

    def must_not_run(*_args, **_kwargs):
        raise AssertionError("Watch goals must not use run_research_fn")

    monkeypatch.setattr("second_brain.agent.watch.run_watch", fake_watch)

    result = run_daily_review(
        reason="test",
        force=True,
        state_path=state_path,
        run_research_fn=must_not_run,
    )
    assert result["last_run_status"] == "completed"
    assert "run_research_fn" not in called.get("kwargs", {})
    assert called.get("kwargs", {}).get("require_enabled") is True


def test_needs_catch_up_and_seconds(monkeypatch):
    state = {
        "last_run_date": None,
        "last_run_status": "idle",
    }
    monkeypatch.setattr("sidecar.scheduler.DAILY_REVIEW_ENABLED", True)
    monkeypatch.setattr("sidecar.scheduler.DAILY_REVIEW_CATCH_UP", True)
    assert needs_catch_up(state) is True

    state["last_run_date"] = date.today().isoformat()
    state["last_run_status"] = "completed"
    assert needs_catch_up(state) is False

    state["last_run_status"] = "running"
    assert needs_catch_up(state) is True

    now = datetime(2026, 8, 4, 8, 0, 0).astimezone()
    secs = seconds_until_hour(9, now=now)
    assert 3500 < secs < 3700

    # Before scheduled hour — no auto catch-up even if pending
    pending = {"last_run_date": None, "last_run_status": "idle"}
    assert past_scheduled_hour(9, now=now) is False
    assert should_auto_catch_up(pending, now=now, hour=9) is False

    after = datetime(2026, 8, 4, 10, 0, 0).astimezone()
    assert past_scheduled_hour(9, now=after) is True
    assert should_auto_catch_up(pending, now=after, hour=9) is True

    monkeypatch.setattr("sidecar.scheduler.DAILY_REVIEW_CATCH_UP", False)
    assert should_auto_catch_up(pending, now=after, hour=9) is False


def test_start_async_returns_immediately(tmp_path: Path, monkeypatch):
    """Async start must not block on the research run."""
    import time

    from sidecar.scheduler import DailyReviewScheduler
    from second_brain.agent import daily_review as dr

    state_path = tmp_path / "digest_state.json"
    monkeypatch.setattr(dr, "DIGEST_STATE_PATH", state_path)
    monkeypatch.setattr(dr, "DAILY_REVIEW_ENABLED", True)

    held = threading.Event()
    released = threading.Event()
    started = threading.Event()

    def fake_research(query, **kwargs):
        started.set()
        held.wait(timeout=5)
        return {
            "query": query,
            "final_report": "ok",
            "confidence": 0.9,
            "open_questions": [],
            "learning_path": None,
            "report_path": None,
        }

    monkeypatch.setattr(
        "second_brain.graph.run_research",
        fake_research,
    )

    # Plan will find nothing unless we seed docs — force a goal via stub plan
    from second_brain.agent.daily_review import ReviewGoal, ReviewPlan

    monkeypatch.setattr(
        dr,
        "plan_daily_review",
        lambda **kwargs: ReviewPlan(
            goals=[ReviewGoal(goal="Test goal", kind="consolidate", source="test")],
            new_files=[],
            open_questions=[],
            skip_reason=None,
        ),
    )
    monkeypatch.setattr(dr, "write_daily_digest", lambda **kwargs: tmp_path / "d.md")

    locks = {"held": False}

    def acquire():
        if locks["held"]:
            return "busy-run"
        locks["held"] = True
        return None

    def release():
        locks["held"] = False
        released.set()

    sched = DailyReviewScheduler(acquire_lock=acquire, release_lock=release, enabled=True)
    t0 = time.monotonic()
    payload, code = sched.start_async(reason="manual", force=True)
    elapsed = time.monotonic() - t0
    assert elapsed < 1.0
    assert code == 202
    assert payload["running"] is True or payload["last_run_status"] == "running"

    assert started.wait(timeout=3)
    held.set()
    assert released.wait(timeout=3)


def test_save_load_state(tmp_path: Path):
    path = tmp_path / "state.json"
    save_review_state(
        {
            "last_run_date": "2026-08-04",
            "last_run_status": "completed",
            "goals_run": [],
        },
        path,
    )
    loaded = load_review_state(path)
    assert loaded["last_run_date"] == "2026-08-04"
    assert loaded["last_run_status"] == "completed"
