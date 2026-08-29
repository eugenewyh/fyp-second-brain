"""LLM manager voice — template fallback and polish hook."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from second_brain.agent.router.decision import RouteDecision  # noqa: E402
from second_brain.agent.router.voice import apply_voice, generate_voice  # noqa: E402


def test_apply_voice_keeps_template_when_generate_returns_none(monkeypatch):
    monkeypatch.setattr("second_brain.agent.router.voice.generate_voice", lambda *_a, **_k: None)
    decision = RouteDecision(
        kind="meta",
        text="Template line.",
        route_tier="meta",
        topic="Coffee",
    )
    out = apply_voice(decision, user_message="hi")
    assert out.text == "Template line."


def test_apply_voice_polishes_when_generate_returns_line(monkeypatch):
    monkeypatch.setattr(
        "second_brain.agent.router.voice.generate_voice",
        lambda *_a, **_k: "Hey — I can Teach, Ask from notes, or Research with sources.",
    )
    decision = RouteDecision(
        kind="meta",
        text="Template line.",
        route_tier="meta",
        topic="Coffee",
    )
    out = apply_voice(decision, user_message="hello")
    assert "Teach" in out.text
    assert "+voice" in out.reason


def test_refuse_voice_updates_refuse_message(monkeypatch):
    monkeypatch.setattr(
        "second_brain.agent.router.voice.generate_voice",
        lambda *_a, **_k: "Nothing saved on this yet — Teach a note first.",
    )
    decision = RouteDecision(
        kind="dispatch",
        text="old",
        job="refuse",
        route_tier="rule",
        refuse_message="old",
        topic="dlm",
    )
    out = apply_voice(decision, user_message="What is diffusion?")
    assert out.refuse_message == out.text


def test_skips_topic_ops():
    decision = RouteDecision(
        kind="dispatch",
        text="I'll combine A into B.",
        job="merge",
        route_tier="topic",
        merge_source="A",
        merge_dest="B",
    )
    assert generate_voice(decision, user_message="combine A into B") is None
