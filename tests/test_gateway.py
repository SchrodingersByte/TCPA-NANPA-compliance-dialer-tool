"""
Pipeline Verification Integration Suite — POST /api/v1/dial-check

Covers every row in the PRD Section 5 execution-flow matrix plus input
validation, duplicate call_id handling, and the /health liveness probe.

Phone number key:
  +12125550020  NY 212, last digit 0 (even)  → VALID RND, ET window
  +12125550021  NY 212, last digit 1 (odd)   → REASSIGNED RND
  +12125550024  NY 212, last digit 4 (even)  → VALID RND (used for DNC test)
  +18505550020  FL 850, last digit 0 (even)  → VALID RND, but FL/CT timezone

Timestamp key:
  2026-05-22T14:30:00Z  =  10:30 EDT  →  inside all state windows
  2026-05-22T01:30:00Z  =  20:30 CDT  →  past FL panhandle 20:00 cutoff
"""

import pytest
from httpx import AsyncClient

from tests.conftest import make_payload

# ── PRD execution-flow matrix ──────────────────────────────────────────────────

async def test_allow_pewc_valid_time_valid_rnd(client: AsyncClient, call_id: str) -> None:
    """PEWC consent + even last digit + 10:30 EDT → ALLOW."""
    resp = await client.post("/api/v1/dial-check", json=make_payload(call_id))
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "ALLOW"
    assert body["block_reason"] is None
    assert body["evaluated_state"] == "NY"
    assert "EDT" in body["local_call_time"] or "EST" in body["local_call_time"]
    assert body["processing_ms"] >= 0


async def test_block_ai_voice_bot_requires_pewc(client: AsyncClient, call_id: str) -> None:
    """AI_VOICE_BOT with EXPRESS_WRITTEN consent (not PEWC) → BLOCK."""
    resp = await client.post(
        "/api/v1/dial-check",
        json=make_payload(
            call_id,
            call_type="AI_VOICE_BOT",
            consent_type_held="EXPRESS_WRITTEN",
        ),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "BLOCK"
    assert body["block_reason"] == "ERR_AI_REQUIRES_PEWC_CONSENT"


async def test_block_state_window_fl_panhandle(client: AsyncClient, call_id: str) -> None:
    """
    FL panhandle (850) at 01:30 UTC = 20:30 CDT.
    FL rule: end_time 20:00 → out-of-window BLOCK.
    """
    resp = await client.post(
        "/api/v1/dial-check",
        json=make_payload(
            call_id,
            destination_number="+18505550020",   # 850 FL/CT, even last digit
            timestamp="2026-05-22T01:30:00Z",    # 20:30 CDT
        ),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "BLOCK"
    assert body["block_reason"] == "ERR_STATE_WINDOW_VIOLATION"
    assert body["evaluated_state"] == "FL"
    assert body["evaluated_timezone"] == "America/Chicago"
    assert "20:30" in body["local_call_time"]


async def test_block_rnd_reassigned_odd_digit(client: AsyncClient, call_id: str) -> None:
    """Last digit 1 (odd) → mock RND returns REASSIGNED → BLOCK."""
    resp = await client.post(
        "/api/v1/dial-check",
        json=make_payload(call_id, destination_number="+12125550021"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "BLOCK"
    assert body["block_reason"] == "ERR_RND_REASSIGNED"


async def test_block_national_dnc_match(client: AsyncClient, call_id: str) -> None:
    """Number present in the in-memory DNC cache → BLOCK."""
    import app.services.compliance_engine as eng

    dnc_target = "+12125550024"      # 212 NY, even digit → VALID RND but on DNC
    normalized = "2125550024"
    eng._dnc_cache.add(normalized)
    try:
        resp = await client.post(
            "/api/v1/dial-check",
            json=make_payload(call_id, destination_number=dnc_target),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["decision"] == "BLOCK"
        assert body["block_reason"] == "ERR_NATIONAL_DNC_MATCH"
    finally:
        eng._dnc_cache.discard(normalized)


async def test_block_rnd_registry_timeout(
    client: AsyncClient, call_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Patch check_rnd to raise TimeoutError (simulates RND registry unreachable).
    asyncio.timeout() in _check_rnd_safe converts this to ERR_REGISTRY_TIMEOUT_FAIL_SAFE.
    """
    import app.services.compliance_engine as eng

    async def _always_timeout(destination: str) -> None:
        raise TimeoutError("simulated registry timeout")

    monkeypatch.setattr(eng, "check_rnd", _always_timeout)

    resp = await client.post("/api/v1/dial-check", json=make_payload(call_id))
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "BLOCK"
    assert body["block_reason"] == "ERR_REGISTRY_TIMEOUT_FAIL_SAFE"


# ── Audit ledger: duplicate call_id handling ───────────────────────────────────

async def test_duplicate_call_id_returns_fresh_decision(
    client: AsyncClient, call_id: str
) -> None:
    """
    A second request with the same call_id should still return a compliance
    decision (audit write is silently skipped, no 4xx error returned).
    """
    payload = make_payload(call_id)
    r1 = await client.post("/api/v1/dial-check", json=payload)
    r2 = await client.post("/api/v1/dial-check", json=payload)

    assert r1.status_code == 200
    assert r2.status_code == 200
    # Both should produce the same decision for identical inputs
    assert r1.json()["decision"] == r2.json()["decision"]


# ── Input validation (FastAPI / Pydantic layer) ────────────────────────────────

async def test_missing_required_field_returns_422(client: AsyncClient) -> None:
    """Omitting destination_number must return HTTP 422."""
    bad = {
        "call_id": "bad-001",
        "source_number": "+12025550143",
        # destination_number intentionally omitted
        "consent_type_held": "PEWC",
        "call_type": "TELEMARKETING",
        "timestamp": "2026-05-22T14:30:00Z",
    }
    resp = await client.post("/api/v1/dial-check", json=bad)
    assert resp.status_code == 422


async def test_invalid_phone_format_returns_422(client: AsyncClient, call_id: str) -> None:
    """Phone number not matching E.164 NANPA (+1XXXXXXXXXX) must return HTTP 422."""
    resp = await client.post(
        "/api/v1/dial-check",
        json=make_payload(call_id, destination_number="555-1234"),
    )
    assert resp.status_code == 422


async def test_naive_timestamp_returns_422(client: AsyncClient, call_id: str) -> None:
    """Timestamp without timezone info must be rejected (AwareDatetime enforced)."""
    resp = await client.post(
        "/api/v1/dial-check",
        json=make_payload(call_id, timestamp="2026-05-22T14:30:00"),  # no tz
    )
    assert resp.status_code == 422


async def test_invalid_consent_type_returns_422(client: AsyncClient, call_id: str) -> None:
    """Consent type outside the allowed Literal set must return 422."""
    resp = await client.post(
        "/api/v1/dial-check",
        json=make_payload(call_id, consent_type_held="HANDSHAKE"),
    )
    assert resp.status_code == 422


# ── Health probe ───────────────────────────────────────────────────────────────

async def test_health_endpoint(client: AsyncClient) -> None:
    """/health returns 200 with status=ok and version string."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "dnc_cache_entries" in body


# ── Transcript endpoint: basic routing check ───────────────────────────────────

async def test_analyze_transcript_returns_structured_response(
    client: AsyncClient, call_id: str
) -> None:
    """
    POST /api/v1/analyze-transcript must return a TranscriptAnalysisResponse shape.
    Ollama may or may not be running; fail-closed guarantees a valid schema either way.
    """
    resp = await client.post(
        "/api/v1/analyze-transcript",
        json={"call_id": call_id, "transcript": "Take me off this list."},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "opt_out_detected" in body
    assert "confidence" in body
    assert "reasoning" in body
    assert isinstance(body["opt_out_detected"], bool)
    assert 0.0 <= body["confidence"] <= 1.0
