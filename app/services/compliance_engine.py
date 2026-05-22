"""
Core compliance validation orchestrator for SovereignShield.

Pipeline execution order
────────────────────────
  Stage 1 — Consent gate (sync, zero I/O)
      AI_VOICE_BOT calls require PEWC consent; any other consent type is an
      immediate BLOCK without touching the database or RND registry.

  Stage 2 — asyncio.gather() — three concurrent checks
      a. National DNC   — O(1) in-memory Python set lookup
      b. State time window — async DB query + IANA local-time computation
      c. RND registry   — async mock with asyncio.timeout() fail-safe

  Stage 3 — Verdict
      Checks are evaluated in order (DNC → time window → RND).
      First failure wins. All three must pass for ALLOW.

  Outer try/except
      Any unhandled exception at any stage defaults to BLOCK (fail-closed).
      Giving a compliance waiver on a system fault is categorically forbidden.
"""

import asyncio
import logging
from dataclasses import dataclass
from time import perf_counter
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import aiofiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.timezone_maps import FEDERAL_FALLBACK, resolve_phone
from app.database.models import StateDialingRule
from app.schemas.validation import DialCheckResponse, DialIngestion
from app.services.mock_registry import RNDStatus, check_rnd

logger = logging.getLogger(__name__)


# ── Block reason codes ─────────────────────────────────────────────────────────

class _BR:
    DNC              = "ERR_NATIONAL_DNC_MATCH"
    STATE_WINDOW     = "ERR_STATE_WINDOW_VIOLATION"
    AI_REQUIRES_PEWC = "ERR_AI_REQUIRES_PEWC_CONSENT"
    RND_REASSIGNED   = "ERR_RND_REASSIGNED"
    REGISTRY_TIMEOUT = "ERR_REGISTRY_TIMEOUT_FAIL_SAFE"
    SYSTEM_FAULT     = "ERR_SYSTEM_FAULT"


# ── National DNC in-memory cache ───────────────────────────────────────────────

_dnc_cache: set[str] = set()


def _normalize_for_dnc(phone: str) -> str:
    """Strip formatting; return 10-digit string (drop leading country code 1)."""
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        return digits[1:]
    return digits


async def load_dnc_cache(csv_path: str = settings.DNC_CSV_PATH) -> int:
    """
    Read the mock DNC CSV into the in-memory set at startup.

    Expected CSV format: single column `phone_number` with a header row.
    Numbers may be E.164 (+12025550100) or 10-digit bare format.
    A missing file is logged as a warning and the cache stays empty so the
    engine can still start — the CSV is generated in Phase 5.
    """
    global _dnc_cache
    new_cache: set[str] = set()

    try:
        async with aiofiles.open(csv_path, mode="r", encoding="utf-8") as fh:
            header_skipped = False
            async for raw_line in fh:
                if not header_skipped:
                    header_skipped = True
                    continue
                phone = raw_line.strip()
                if phone:
                    norm = _normalize_for_dnc(phone)
                    if norm:
                        new_cache.add(norm)

    except FileNotFoundError:
        logger.warning(
            "DNC CSV not found at '%s' — engine starting with empty cache. "
            "Run Phase 5 data generator to populate.",
            csv_path,
        )
    except Exception as exc:
        logger.error("DNC cache load failed — engine starting with empty cache: %s", exc, exc_info=True)

    _dnc_cache = new_cache
    logger.info("DNC cache loaded: %d entries", len(_dnc_cache))
    return len(_dnc_cache)


def dnc_cache_size() -> int:
    """Expose cache cardinality for the /health endpoint."""
    return len(_dnc_cache)


# ── Internal check result ──────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class _CheckResult:
    passed: bool
    block_reason: str | None = None
    state_code: str = FEDERAL_FALLBACK.state_code
    timezone: str = FEDERAL_FALLBACK.timezone
    local_time_str: str = ""


# ── Validation sub-tasks ───────────────────────────────────────────────────────

async def _check_dnc(destination: str) -> _CheckResult:
    """O(1) in-memory DNC lookup."""
    normalized = _normalize_for_dnc(destination)
    if normalized in _dnc_cache:
        return _CheckResult(passed=False, block_reason=_BR.DNC)
    return _CheckResult(passed=True)


async def _check_time_window(
    destination: str,
    timestamp_utc,      # datetime (must be timezone-aware)
    session: AsyncSession,
) -> _CheckResult:
    """
    Convert the call timestamp to the recipient's local time zone and compare
    against the applicable state (or federal) calling window from the DB.

    Lookup priority: state-specific rule → federal fallback ('US').
    """
    area_info = resolve_phone(destination)

    try:
        tz = ZoneInfo(area_info.timezone)
    except ZoneInfoNotFoundError:
        logger.error(
            "Unrecognised IANA timezone '%s' for area code in '%s' — BLOCK",
            area_info.timezone,
            destination,
        )
        return _CheckResult(
            passed=False,
            block_reason=_BR.SYSTEM_FAULT,
            state_code=area_info.state_code,
            timezone=area_info.timezone,
        )

    local_dt = timestamp_utc.astimezone(tz)
    local_time = local_dt.time()
    local_time_str = local_dt.strftime("%H:%M:%S %Z")

    # Try state-specific rule first, then federal 'US' row seeded at startup
    rule: StateDialingRule | None = None
    for state_code in (area_info.state_code, "US"):
        result = await session.execute(
            select(StateDialingRule).where(StateDialingRule.state_code == state_code)
        )
        rule = result.scalar_one_or_none()
        if rule is not None:
            break

    if rule is None:
        # DB seeding guarantees the 'US' row exists; reaching here means corruption
        logger.error("State dialing rules table is empty — fail-safe BLOCK")
        return _CheckResult(
            passed=False,
            block_reason=_BR.SYSTEM_FAULT,
            state_code=area_info.state_code,
            timezone=area_info.timezone,
            local_time_str=local_time_str,
        )

    # Window is [start_time, end_time) — end_time is exclusive
    in_window = rule.start_time <= local_time < rule.end_time

    logger.debug(
        "Time window check: state=%s tz=%s local=%s window=%s–%s → %s",
        area_info.state_code,
        area_info.timezone,
        local_time_str,
        rule.start_time,
        rule.end_time,
        "PASS" if in_window else "FAIL",
    )

    return _CheckResult(
        passed=in_window,
        block_reason=None if in_window else _BR.STATE_WINDOW,
        state_code=area_info.state_code,
        timezone=area_info.timezone,
        local_time_str=local_time_str,
    )


async def _check_rnd_safe(destination: str) -> _CheckResult:
    """
    Query the RND mock with a hard timeout budget.

    A timeout means the registry is unreachable; per fail-closed policy this
    produces ERR_REGISTRY_TIMEOUT_FAIL_SAFE rather than allowing the call through.
    """
    try:
        async with asyncio.timeout(settings.RND_REQUEST_TIMEOUT_SECONDS):
            status = await check_rnd(destination)

        if status == RNDStatus.REASSIGNED:
            return _CheckResult(passed=False, block_reason=_BR.RND_REASSIGNED)
        return _CheckResult(passed=True)

    except TimeoutError:
        logger.warning(
            "RND registry timed out after %.1f s for %s — fail-safe BLOCK",
            settings.RND_REQUEST_TIMEOUT_SECONDS,
            destination,
        )
        return _CheckResult(passed=False, block_reason=_BR.REGISTRY_TIMEOUT)

    except Exception as exc:
        logger.error("RND check raised unexpected error: %s", exc, exc_info=True)
        return _CheckResult(passed=False, block_reason=_BR.SYSTEM_FAULT)


# ── Response builder ───────────────────────────────────────────────────────────

def _build_response(
    payload: DialIngestion,
    decision: str,
    block_reason: str | None,
    t0: float,
    geo: _CheckResult,
) -> DialCheckResponse:
    return DialCheckResponse(
        call_id=payload.call_id,
        decision=decision,                          # type: ignore[arg-type]
        block_reason=block_reason,
        evaluated_state=geo.state_code,
        evaluated_timezone=geo.timezone,
        local_call_time=geo.local_time_str,
        processing_ms=round((perf_counter() - t0) * 1000, 3),
    )


# ── Public entry point ─────────────────────────────────────────────────────────

async def evaluate_dial(
    payload: DialIngestion,
    session: AsyncSession,
) -> DialCheckResponse:
    """
    Run the full compliance pipeline for one dial request.

    Always returns a DialCheckResponse — never raises. Any unhandled exception
    in the pipeline is caught here and converted to a fail-safe BLOCK.
    """
    t0 = perf_counter()

    try:
        # ── Stage 1: Consent gate (sync, no I/O) ──────────────────────────────
        if payload.call_type == "AI_VOICE_BOT" and payload.consent_type_held != "PEWC":
            logger.info(
                "call_id=%s BLOCK consent=%s call_type=%s",
                payload.call_id, payload.consent_type_held, payload.call_type,
            )
            geo = _CheckResult(passed=False, block_reason=_BR.AI_REQUIRES_PEWC)
            return _build_response(payload, "BLOCK", _BR.AI_REQUIRES_PEWC, t0, geo)

        # ── Stage 2: Parallel I/O checks ──────────────────────────────────────
        dnc_result, tw_result, rnd_result = await asyncio.gather(
            _check_dnc(payload.destination_number),
            _check_time_window(payload.destination_number, payload.timestamp, session),
            _check_rnd_safe(payload.destination_number),
        )

        # ── Stage 3: Verdict — first failure wins ─────────────────────────────
        for result in (dnc_result, tw_result, rnd_result):
            if not result.passed:
                logger.info(
                    "call_id=%s BLOCK reason=%s state=%s local=%s",
                    payload.call_id, result.block_reason,
                    tw_result.state_code, tw_result.local_time_str,
                )
                return _build_response(payload, "BLOCK", result.block_reason, t0, tw_result)

        logger.info(
            "call_id=%s ALLOW state=%s local=%s",
            payload.call_id, tw_result.state_code, tw_result.local_time_str,
        )
        return _build_response(payload, "ALLOW", None, t0, tw_result)

    except Exception as exc:
        logger.error(
            "Unhandled compliance engine fault [call_id=%s]: %s",
            payload.call_id, exc, exc_info=True,
        )
        fallback = _CheckResult(passed=False, block_reason=_BR.SYSTEM_FAULT)
        return _build_response(payload, "BLOCK", _BR.SYSTEM_FAULT, t0, fallback)
