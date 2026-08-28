"""Local job router model."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from second_brain.agent.job_router import model_loaded, route_job  # noqa: E402


@pytest.fixture
def require_model():
    if not model_loaded():
        pytest.skip("job router model.json missing — run scripts/train_job_router.py")


def test_model_is_bundled(require_model):
    assert model_loaded()


def test_routes_explicit_research(require_model):
    job, reason, conf = route_job(
        "Research indoor plant care for beginners — watering and soil",
        matching_claim_count=0,
    )
    assert job == "research"
    assert conf >= 0.42
    assert "router" in reason


def test_routes_lookup(require_model):
    job, _, conf = route_job("Find papers on JustGRPO", matching_claim_count=0)
    assert job == "research"
    assert conf >= 0.42


def test_routes_empty_ask_to_refuse(require_model):
    job, _, _ = route_job(
        "What is the best espresso machine for a small kitchen?",
        matching_claim_count=0,
    )
    assert job == "refuse"


def test_routes_notes_recall(require_model):
    job, _, _ = route_job(
        "According to my notes, what grind size do I prefer?",
        matching_claim_count=3,
    )
    assert job == "answer"


def test_attachments_bias_file(require_model):
    job, _, _ = route_job("What is this?", matching_claim_count=0, has_attachments=True)
    assert job == "file"
