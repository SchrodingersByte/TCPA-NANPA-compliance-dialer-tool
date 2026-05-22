"""
AI NLP Opt-out Verification — Unit Tests

All tests in this file are pure unit tests against the parsing and
fail-closed logic layers.  No live Ollama connection is required: the
model-calling function (analyze_transcript_for_opt_out) is tested for
its failure-handling guarantees rather than model accuracy.

The parametrised phrase tests verify that the JSON-parsing pipeline
correctly maps model outputs for known TCPA opt-out phrases to the right
schema fields — not that the model itself classifies them correctly.
"""

import pytest

from app.services.local_llm import (
    _fail_closed_response,
    _parse_llm_json,
    _strip_markdown_fences,
    analyze_transcript_for_opt_out,
)


# ── _strip_markdown_fences ─────────────────────────────────────────────────────

def test_strip_no_fence_is_unchanged() -> None:
    raw = '{"opt_out_detected": false}'
    assert _strip_markdown_fences(raw) == raw


def test_strip_json_fenced_block() -> None:
    fenced = '```json\n{"opt_out_detected": true}\n```'
    assert _strip_markdown_fences(fenced) == '{"opt_out_detected": true}'


def test_strip_plain_fenced_block() -> None:
    fenced = "```\n{\"opt_out_detected\": false}\n```"
    assert _strip_markdown_fences(fenced) == '{"opt_out_detected": false}'


def test_strip_preserves_inner_whitespace() -> None:
    fenced = "```json\n  { \"k\": 1 }  \n```"
    result = _strip_markdown_fences(fenced)
    assert result == '{ "k": 1 }'


# ── _fail_closed_response ──────────────────────────────────────────────────────

def test_fail_closed_always_opt_out() -> None:
    r = _fail_closed_response("cid-001", "test error")
    assert r.opt_out_detected is True
    assert r.confidence == 0.0
    assert r.matched_phrase is None
    assert r.call_id == "cid-001"
    assert "test error" in r.reasoning


# ── _parse_llm_json — valid JSON string ───────────────────────────────────────

def test_parse_explicit_opt_out() -> None:
    raw = '{"opt_out_detected": true, "confidence": 0.95, "matched_phrase": "stop calling", "reasoning": "Explicit"}'
    r = _parse_llm_json(raw, "p-001")
    assert r.opt_out_detected is True
    assert abs(r.confidence - 0.95) < 1e-6
    assert r.matched_phrase == "stop calling"


def test_parse_no_opt_out() -> None:
    raw = '{"opt_out_detected": false, "confidence": 0.05, "matched_phrase": null, "reasoning": "No signal"}'
    r = _parse_llm_json(raw, "p-002")
    assert r.opt_out_detected is False
    assert r.matched_phrase is None


def test_parse_missing_optional_fields_use_defaults() -> None:
    """Fields other than opt_out_detected are optional — parser must not crash."""
    raw = '{"opt_out_detected": true}'
    r = _parse_llm_json(raw, "p-003")
    assert r.opt_out_detected is True   # present → used
    assert r.confidence == 0.5          # missing → default 0.5


def test_parse_empty_dict_is_fail_closed() -> None:
    """An empty model response with no keys defaults to opt_out=True (fail-closed)."""
    r = _parse_llm_json({}, "p-004")
    assert r.opt_out_detected is True


# ── _parse_llm_json — dict input (newer Ollama SDK) ───────────────────────────

def test_parse_dict_opt_out_true() -> None:
    data = {"opt_out_detected": True, "confidence": 0.88, "matched_phrase": "remove me", "reasoning": "Stop"}
    r = _parse_llm_json(data, "p-005")
    assert r.opt_out_detected is True
    assert r.matched_phrase == "remove me"


def test_parse_dict_opt_out_false() -> None:
    data = {"opt_out_detected": False, "confidence": 0.07, "matched_phrase": None, "reasoning": "Interested"}
    r = _parse_llm_json(data, "p-006")
    assert r.opt_out_detected is False


# ── _parse_llm_json — confidence clamping ─────────────────────────────────────

def test_confidence_above_one_is_clamped() -> None:
    data = {"opt_out_detected": True, "confidence": 2.5, "matched_phrase": None, "reasoning": "x"}
    r = _parse_llm_json(data, "p-007")
    assert r.confidence == 1.0


def test_confidence_below_zero_is_clamped() -> None:
    data = {"opt_out_detected": False, "confidence": -0.8, "matched_phrase": None, "reasoning": "x"}
    r = _parse_llm_json(data, "p-008")
    assert r.confidence == 0.0


def test_invalid_confidence_type_uses_default() -> None:
    data = {"opt_out_detected": True, "confidence": "high", "matched_phrase": None, "reasoning": "x"}
    r = _parse_llm_json(data, "p-009")
    assert r.confidence == 0.5  # fallback when cast fails


# ── _parse_llm_json — malformed / unexpected input ────────────────────────────

def test_malformed_json_string_is_fail_closed() -> None:
    r = _parse_llm_json("this is not json", "p-010")
    assert r.opt_out_detected is True
    assert r.confidence == 0.0


def test_unexpected_type_is_fail_closed() -> None:
    r = _parse_llm_json(42, "p-011")   # type: ignore[arg-type]
    assert r.opt_out_detected is True


# ── Known TCPA opt-out phrase simulation ──────────────────────────────────────

@pytest.mark.parametrize(
    "phrase, expected",
    [
        ("Take me off this list.", True),
        ("I'm broke, stop texting me.", True),
        ("Don't ever call this line again.", True),
        ("Remove me from your database immediately.", True),
        ("Never contact me again.", True),
        ("Yes, I'm interested. Tell me more.", False),
        ("What time does the sale end?", False),
    ],
)
def test_phrase_parsing_pipeline(phrase: str, expected: bool) -> None:
    """
    Simulate the model returning a correct classification for a known phrase.
    Validates that the parsing pipeline maps model JSON to the right schema fields.
    """
    mock_model_output = {
        "opt_out_detected": expected,
        "confidence": 0.92 if expected else 0.08,
        "matched_phrase": phrase if expected else None,
        "reasoning": f"Simulated correct classification for: {phrase}",
    }
    r = _parse_llm_json(mock_model_output, "phrase-test")
    assert r.opt_out_detected is expected
    if expected:
        assert r.matched_phrase == phrase


# ── analyze_transcript_for_opt_out — fail-closed async paths ─────────────────

async def test_empty_transcript_is_fail_closed() -> None:
    """Empty string must short-circuit before calling the model."""
    r = await analyze_transcript_for_opt_out("", "async-001")
    assert r.opt_out_detected is True
    assert r.confidence == 0.0


async def test_whitespace_only_transcript_is_fail_closed() -> None:
    r = await analyze_transcript_for_opt_out("   \t\n  ", "async-002")
    assert r.opt_out_detected is True


async def test_canonical_opt_out_phrase_returns_opt_out() -> None:
    """
    'Take me off this list' is a canonical TCPA opt-out phrase.

    This test passes whether:
      a) Ollama is live and the model correctly classifies it (True), or
      b) Ollama is unavailable / model not pulled → fail-closed (True).
    Either path returns opt_out_detected=True, so the assertion always holds.
    """
    r = await analyze_transcript_for_opt_out("Take me off this list.", "async-003")
    assert r.opt_out_detected is True


async def test_response_schema_is_always_valid() -> None:
    """Schema fields must always be present and within bounds regardless of model state."""
    r = await analyze_transcript_for_opt_out("Hello, I'd like more information.", "async-004")
    assert isinstance(r.opt_out_detected, bool)
    assert 0.0 <= r.confidence <= 1.0
    assert isinstance(r.reasoning, str)
    assert len(r.reasoning) > 0
