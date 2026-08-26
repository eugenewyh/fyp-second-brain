"""Watch instruction parse, brief formatter, planner preference."""

import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from second_brain.agent.daily_review import plan_daily_review
from second_brain.agent.watch import (
    WatchError,
    append_steer,
    ensure_instruction,
    format_watch_brief,
    load_watch,
    parse_instruction,
    prepare_watch_run,
    retrieval_is_thin,
    run_watch,
    today_brief_exists,
    validate_watch,
    write_brief,
)


COMPLETE = """---
enabled: true
cadence: weekdays
hour: 6
---

# Watch

## Who
FYP student working on RAG hallucination.

## Focus
Citation metrics for grounded-but-incomplete RAG answers.

## Include
New citation metrics, arXiv papers, eval datasets.

## Exclude
Generic AI hype posts.

## Trusted sources
arxiv.org, ACL anthology.

## Steer log
"""


def test_parse_and_validate():
    w = parse_instruction(COMPLETE, project_path="/tmp/t")
    assert w.enabled is True
    assert w.hour == 6
    assert "Citation metrics" in w.focus
    validate_watch(w)


def test_parse_who_slash_focus_heading():
    text = """---
enabled: true
---

# Watch

## Who / focus
Track text diffusion LMs vs autoregressive decoding.

## Include
DiffusionGemma, papers on block diffusion.
"""
    w = parse_instruction(text, project_path="/tmp/t")
    assert "diffusion" in w.focus.lower()
    validate_watch(w)


def test_refuse_incomplete_instruction(tmp_path: Path):
    p = tmp_path / "Inbox"
    p.mkdir()
    ensure_instruction(p)
    w = load_watch(p)
    assert w is not None
    assert w.enabled is False
    with pytest.raises(WatchError, match="Focus"):
        validate_watch(w)
    text = (p / "instruction.md").read_text(encoding="utf-8")
    assert "hour:" not in text
    assert "Weekday mornings" in text


def test_parse_keeps_hour_on_legacy_files():
    w = parse_instruction(COMPLETE, project_path="/tmp/T")
    assert w.hour == 6


def test_slow_day_brief_when_thin():
    assert retrieval_is_thin({"personal": 1})
    md = format_watch_brief(report="", stats={"personal": 0}, slow_day=True, day=date(2026, 8, 17))
    assert "Slow day" in md
    assert "2026-08-17" in md


def test_brief_from_report_sections():
    report = """## Executive Summary
The one development is a new citation metric.

## Key Findings
- Faithfulness is not completeness.
- Grounded-but-incomplete answers need their own score.

## Identified Gaps
- No shared benchmark yet
"""
    md = format_watch_brief(report=report, stats={"web": 4, "arxiv": 2}, slow_day=False)
    assert "The one thing" in md
    assert "Faithfulness" in md
    assert "What happened" in md


def test_same_day_brief_no_op(tmp_path: Path):
    p = tmp_path / "Topic"
    p.mkdir()
    (p / "instruction.md").write_text(COMPLETE, encoding="utf-8")
    write_brief(p, "# Morning Brief — already\n\nHello brief.\n", day=date.today())
    assert today_brief_exists(p)
    with pytest.raises(WatchError, match="already exists"):
        prepare_watch_run(p)


def test_run_watch_writes_brief(tmp_path: Path, monkeypatch):
    p = tmp_path / "Topic"
    p.mkdir()
    (p / "instruction.md").write_text(COMPLETE, encoding="utf-8")

    def fake_research(goal, **kwargs):
        assert kwargs.get("claim_origin") == "watch"
        assert "do not rehash" in goal.lower() or "Do not rehash" in goal
        return {
            "report": "## Executive Summary\nNew metric shipped.\n\n## Key Findings\n- New metric shipped for grounded-but-incomplete answers.\n",
            "retrieval_stats": {"web": 5, "arxiv": 2},
            "report_path": str(p / "research" / "r.md"),
            "claim_count": 1,
            "query": goal,
        }

    out = run_watch(p, run_research_fn=fake_research)
    assert Path(out["brief_path"]).is_file()
    text = Path(out["brief_path"]).read_text(encoding="utf-8")
    assert "The one thing" in text
    with pytest.raises(WatchError, match="already exists"):
        run_watch(p, run_research_fn=fake_research)


def test_run_watch_clamps_web_off_to_local(tmp_path: Path, monkeypatch):
    p = tmp_path / "Topic"
    p.mkdir()
    (p / "instruction.md").write_text(COMPLETE, encoding="utf-8")
    monkeypatch.setenv("ENABLE_WEB_SEARCH", "false")
    seen: dict = {}

    def fake_research(goal, **kwargs):
        seen.update(kwargs)
        return {
            "report": "## Executive Summary\nLocal only.\n\n## Key Findings\n- Vault note.\n",
            "retrieval_stats": {"personal": 3},
            "report_path": str(p / "research" / "r.md"),
            "claim_count": 0,
            "query": goal,
        }

    run_watch(p, run_research_fn=fake_research, force=True)
    assert seen.get("retrieval_scope") == "local"
    assert seen.get("claim_origin") == "watch"


def test_steer_appends_log_only(tmp_path: Path):
    p = tmp_path / "Topic"
    p.mkdir()
    (p / "instruction.md").write_text(COMPLETE, encoding="utf-8")
    append_steer(p, "Ignore HN hype")
    w = load_watch(p)
    assert "Ignore HN hype" in (w.steer_log if w else "")
    assert "Ignore HN hype" not in (w.focus if w else "")


def test_update_watch_writes_focus_without_clobbering_steer(tmp_path: Path):
    from second_brain.agent.watch import default_include, update_watch, watch_is_complete

    p = tmp_path / "Citation-grounding"
    p.mkdir()
    (p / "instruction.md").write_text(COMPLETE, encoding="utf-8")
    append_steer(p, "Ignore HN hype")
    w = update_watch(
        p,
        focus="Citation metrics for grounded-but-incomplete RAG answers.",
        include=default_include(p),
        enabled=True,
    )
    assert w.enabled is True
    assert "Citation metrics" in w.focus
    assert "Ignore HN hype" in w.steer_log
    assert watch_is_complete(w)


def test_update_watch_trusted_sources_and_enabled_gate(tmp_path: Path):
    from second_brain.agent.watch import create_watch, update_watch, watch_is_complete

    p = tmp_path / "Topic"
    p.mkdir()
    w = create_watch(
        p,
        name="Papers",
        focus="New papers on citation metrics.",
        enabled=True,
    )
    assert watch_is_complete(w)
    assert w.enabled is True
    w2 = update_watch(
        p,
        watch_id=w.id,
        exclude="Generic AI hype.",
        trusted_sources="arxiv.org, ACL anthology.",
    )
    assert "hype" in w2.exclude.lower()
    assert "arxiv" in w2.trusted_sources.lower()
    incomplete = update_watch(
        p,
        watch_id=w.id,
        focus="[todo]",
        include="[todo]",
        enabled=True,
    )
    assert incomplete.enabled is False
    assert watch_is_complete(incomplete) is False


def test_plan_daily_review_prefers_enabled_watch(tmp_path: Path, monkeypatch):
    docs = tmp_path / "documents"
    topic = docs / "Citation-grounding"
    topic.mkdir(parents=True)
    (topic / "instruction.md").write_text(COMPLETE, encoding="utf-8")
    monkeypatch.setattr("second_brain.agent.daily_review.DOCUMENTS_DIR", docs)
    monkeypatch.setattr("second_brain.config.DOCUMENTS_DIR", docs)

    plan = plan_daily_review(
        project_path=str(topic),
        max_goals=3,
        now=datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc),
    )
    assert plan.goals
    assert plan.goals[0].kind == "watch"


def test_named_watch_update_persists_name_and_focus(tmp_path: Path):
    from second_brain.agent.watch import create_watch, load_watch, update_watch

    p = tmp_path / "dlm"
    p.mkdir()
    created = create_watch(p, name="Untitled")
    w = update_watch(
        p,
        watch_id=created.id,
        name="Morning papers",
        focus="Significant new developments related to dlm from the last 24 hours.",
        include="Papers, product changes, and eval results related to dlm.",
        enabled=True,
    )
    assert w.id == created.id
    assert w.name == "Morning papers"
    assert "Significant new developments" in w.focus
    again = load_watch(p, created.id)
    assert again is not None
    assert again.name == "Morning papers"
    assert again.enabled is True
    legacy = load_watch(p, "")
    assert legacy is None


def test_move_named_watch_to_other_topic(tmp_path: Path):
    from second_brain.agent.watch import create_watch, load_watch, move_watch

    src = tmp_path / "dlm"
    dest = tmp_path / "TEST"
    src.mkdir()
    dest.mkdir()
    created = create_watch(
        src,
        name="Morning brief",
        focus="Significant new developments related to dlm from the last 24 hours.",
        include="Papers, product changes, and eval results related to dlm.",
    )
    moved = move_watch(src, dest, watch_id=created.id)
    assert Path(moved.project_path).name == "TEST"
    assert load_watch(src, created.id) is None
    assert load_watch(dest, moved.id) is not None
    assert "Significant new developments" in (moved.focus or "")


def test_delete_named_watch_removes_folder(tmp_path: Path):
    from second_brain.agent.watch import create_watch, delete_watch, load_watch

    p = tmp_path / "dlm"
    p.mkdir()
    created = create_watch(p, name="Untitled")
    delete_watch(p, watch_id=created.id)
    assert load_watch(p, created.id) is None
    assert not (p / "watches" / created.id).exists()


def test_named_watch_isolated_from_legacy(tmp_path: Path):
    from second_brain.agent.watch import create_watch, list_watches_in_topic, write_brief

    p = tmp_path / "dlm"
    p.mkdir()
    (p / "instruction.md").write_text(COMPLETE, encoding="utf-8")
    named = create_watch(
        p,
        name="Morning papers",
        focus="Diffusion language model papers and evals this week.",
        include="arXiv, lab blogs, open-weight releases.",
        enabled=True,
    )
    assert named.id == "morning-papers"
    assert (p / "watches" / "morning-papers" / "instruction.md").is_file()
    assert not (p / "watches" / "morning-papers" / "instruction.md").samefile(p / "instruction.md")

    write_brief(p, "# Morning Brief\n\nLegacy brief.\n", watch_id="")
    write_brief(p, "# Morning Brief\n\nNamed brief.\n", watch_id=named.id)
    assert (p / "briefs" / f"{date.today().isoformat()}.md").is_file()
    assert (p / "watches" / "morning-papers" / "briefs" / f"{date.today().isoformat()}.md").is_file()

    ids = {w.id: w for w in list_watches_in_topic(p)}
    assert "" in ids
    assert "morning-papers" in ids
    assert ids["morning-papers"].name == "Morning papers"
    assert today_brief_exists(p, watch_id="")
    assert today_brief_exists(p, watch_id=named.id)


def test_named_watch_run_does_not_block_legacy(tmp_path: Path):
    from second_brain.agent.watch import create_watch

    p = tmp_path / "Topic"
    p.mkdir()
    (p / "instruction.md").write_text(COMPLETE, encoding="utf-8")
    named = create_watch(
        p,
        name="Side scan",
        focus="Citation metrics for grounded-but-incomplete RAG answers.",
        include="New citation metrics, arXiv papers, eval datasets.",
        enabled=True,
    )

    def fake_research(goal, **kwargs):
        return {
            "report": "## Executive Summary\nNew metric shipped.\n\n## Key Findings\n- New metric shipped for grounded-but-incomplete answers.\n",
            "retrieval_stats": {"web": 5, "arxiv": 2},
            "report_path": str(p / "research" / "r.md"),
            "claim_count": 1,
            "query": goal,
        }

    out = run_watch(p, watch_id=named.id, run_research_fn=fake_research)
    assert "watches" in out["brief_path"]
    run_watch(p, watch_id="", run_research_fn=fake_research)
    with pytest.raises(WatchError, match="already exists"):
        run_watch(p, watch_id=named.id, run_research_fn=fake_research)


def test_plan_queues_multiple_enabled_watches(tmp_path: Path):
    from second_brain.agent.watch import create_watch

    topic = tmp_path / "T"
    topic.mkdir()
    (topic / "instruction.md").write_text(COMPLETE, encoding="utf-8")
    create_watch(
        topic,
        name="Papers",
        focus="Citation metrics for grounded-but-incomplete RAG answers.",
        include="New citation metrics, arXiv papers, eval datasets.",
        enabled=True,
    )
    plan = plan_daily_review(
        project_path=str(topic),
        max_goals=3,
        now=datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc),
    )
    watch_goals = [g for g in plan.goals if g.kind == "watch"]
    assert len(watch_goals) == 2
    assert {g.watch_id for g in watch_goals} == {"", "papers"}


def test_plan_queues_all_watches_beyond_max_goals(tmp_path: Path):
    from second_brain.agent.watch import create_watch

    topic = tmp_path / "T"
    topic.mkdir()
    (topic / "instruction.md").write_text(COMPLETE, encoding="utf-8")
    create_watch(
        topic,
        name="Papers",
        focus="Citation metrics for grounded-but-incomplete RAG answers.",
        include="New citation metrics, arXiv papers, eval datasets.",
        enabled=True,
    )
    create_watch(
        topic,
        name="Product",
        focus="Citation metrics for grounded-but-incomplete RAG answers.",
        include="New citation metrics, arXiv papers, eval datasets.",
        enabled=True,
    )
    monday = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)
    plan = plan_daily_review(project_path=str(topic), max_goals=1, now=monday)
    watch_goals = [g for g in plan.goals if g.kind == "watch"]
    assert len(watch_goals) == 3


def test_plan_skips_weekday_watches_on_weekend(tmp_path: Path):
    topic = tmp_path / "T"
    topic.mkdir()
    (topic / "instruction.md").write_text(COMPLETE, encoding="utf-8")
    saturday = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
    plan = plan_daily_review(project_path=str(topic), max_goals=3, now=saturday)
    assert all(g.kind != "watch" for g in plan.goals)


def test_plan_skips_disabled_and_existing_brief(tmp_path: Path):
    topic = tmp_path / "T"
    topic.mkdir()
    (topic / "instruction.md").write_text(
        COMPLETE.replace("enabled: true", "enabled: false"), encoding="utf-8"
    )
    plan = plan_daily_review(
        project_path=str(topic),
        max_goals=3,
        now=datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc),
    )
    assert all(g.kind != "watch" for g in plan.goals)

    (topic / "instruction.md").write_text(COMPLETE, encoding="utf-8")
    write_brief(topic, "# Morning Brief\n\nAlready filed today.\n")
    plan2 = plan_daily_review(
        project_path=str(topic),
        max_goals=3,
        now=datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc),
    )
    assert all(g.kind != "watch" for g in plan2.goals)


def test_promote_legacy_watch_moves_file_and_briefs(tmp_path: Path):
    from second_brain.agent.watch import promote_legacy_watch

    p = tmp_path / "dlm"
    p.mkdir()
    (p / "instruction.md").write_text(COMPLETE, encoding="utf-8")
    write_brief(p, "# Morning Brief\n\nHello brief.\n")
    w = promote_legacy_watch(p, name="Morning papers")
    assert w.id
    assert not (p / "instruction.md").exists()
    assert (p / "watches" / w.id / "instruction.md").is_file()
    assert "Citation metrics" in (p / "watches" / w.id / "instruction.md").read_text(encoding="utf-8")
    briefs = list((p / "watches" / w.id / "briefs").glob("*.md"))
    assert briefs


def test_plan_records_watch_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    topic = tmp_path / "T"
    topic.mkdir()

    def boom(*_a, **_k):
        raise RuntimeError("watch.py exploded")

    monkeypatch.setattr("second_brain.agent.watch.list_watches_in_topic", boom)
    plan = plan_daily_review(
        project_path=str(topic),
        max_goals=1,
        now=datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc),
    )
    assert plan.watch_error
    assert "exploded" in plan.watch_error


def test_update_watch_missing_file_does_not_create_legacy(tmp_path: Path):
    from second_brain.agent.watch import update_watch

    p = tmp_path / "Bare"
    p.mkdir()
    with pytest.raises(WatchError, match="not found"):
        update_watch(p, focus="Should not create instruction.md")
    assert not (p / "instruction.md").exists()
