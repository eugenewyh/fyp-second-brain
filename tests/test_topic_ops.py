"""Explicit topic routing phrases: retarget, merge, split, also-retrieve."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from second_brain.agent.topic_ops import TopicRef, parse_topic_op


FYP = TopicRef(name="FYP", path="/vault/FYP")
JUST = TopicRef(name="JustGRPO", path="/vault/JustGRPO")
DLM = TopicRef(name="DLM", path="/vault/DLM")
THESIS = TopicRef(name="thesis", path="/vault/thesis")
TOPICS = [FYP, JUST, DLM, THESIS]


def test_this_is_part_of_fyp_is_retarget():
    op = parse_topic_op("this is part of FYP", bound_path="/vault/JustGRPO", available=TOPICS)
    assert op is not None
    assert op.kind == "retarget"
    assert op.target == "FYP"
    assert op.target_path == "/vault/FYP"


def test_file_this_under_is_retarget():
    op = parse_topic_op("file this under DLM", bound_path="/vault/JustGRPO", available=TOPICS)
    assert op is not None
    assert op.kind == "retarget"
    assert op.target == "DLM"


def test_same_folder_retarget_is_ignored():
    op = parse_topic_op("this is part of FYP", bound_path="/vault/FYP", available=TOPICS)
    assert op is None


def test_combine_justgrpo_into_dlm_is_merge():
    op = parse_topic_op("combine JustGRPO into DLM", available=TOPICS)
    assert op is not None
    assert op.kind == "merge"
    assert op.source == "JustGRPO"
    assert op.dest == "DLM"
    assert op.source_path == "/vault/JustGRPO"
    assert op.dest_path == "/vault/DLM"


def test_merge_same_name_is_ignored():
    assert parse_topic_op("combine DLM into DLM", available=TOPICS) is None


def test_forget_and_switch_subject_is_split():
    op = parse_topic_op(
        "forget JustGRPO, let's do thesis structure",
        bound_path="/vault/JustGRPO",
        available=TOPICS,
    )
    assert op is not None
    assert op.kind == "split"
    assert "thesis" in op.target.lower()


def test_switch_to_existing_folder_is_retarget():
    op = parse_topic_op("switch to FYP", bound_path="/vault/JustGRPO", available=TOPICS)
    assert op is not None
    assert op.kind == "retarget"
    assert op.target == "FYP"


def test_switch_to_unknown_name_is_split():
    op = parse_topic_op("switch to kitchen renovation", bound_path="/vault/JustGRPO", available=TOPICS)
    assert op is not None
    assert op.kind == "split"
    assert op.target == "kitchen renovation"


def test_also_check_notes_is_retrieve_union():
    op = parse_topic_op(
        "What is the status of GRPO, also check my thesis notes",
        bound_path="/vault/JustGRPO",
        available=TOPICS,
    )
    assert op is not None
    assert op.kind == "also"
    assert op.also_topics == ["thesis"]
    assert op.also_paths == ["/vault/thesis"]
    assert "GRPO" in op.remainder
    assert "also check" not in op.remainder.lower()


def test_and_what_i_buy_next_cite_notes_is_not_also():
    """Sentence tails must not invent also-topics from 'and … notes'."""
    op = parse_topic_op(
        "Synthesise my stance on home espresso: grind vs dose, milk steaming, "
        "and what I'd buy next. Cite my notes.",
        bound_path="/vault/Coffee",
        available=TOPICS,
    )
    assert op is None


def test_ordinary_question_is_not_a_topic_op():
    assert parse_topic_op("Find papers on JustGRPO", bound_path="/vault/dlm", available=TOPICS) is None
