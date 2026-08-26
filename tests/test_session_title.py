"""Tests for session title sanitization (no live Gemini calls)."""

from second_brain.memory.session_title import sanitize_session_title


def test_sanitize_strips_quotes_and_labels():
    assert sanitize_session_title('"Espresso Grinders Under $500"') == (
        "Espresso Grinders Under $500"
    )
    assert sanitize_session_title("Title: Single-Dose Grinders") == "Single-Dose Grinders"


def test_sanitize_rejects_junk():
    assert sanitize_session_title("") is None
    assert sanitize_session_title("New Chat") is None
    assert sanitize_session_title("n/a") is None
    assert sanitize_session_title("x") is None


def test_sanitize_clips_length_and_words():
    long = "One Two Three Four Five Six Seven Eight Nine Ten"
    out = sanitize_session_title(long)
    assert out is not None
    assert len(out.split()) <= 6
    assert len(out) <= 36
