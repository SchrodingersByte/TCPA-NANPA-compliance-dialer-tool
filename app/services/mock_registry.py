"""
Reassigned Numbers Database (RND) mock registry.

Simulates the FCC's real-time reassignment portal without a live API connection.

Deterministic assignment rule (per PRD spec):
  - Final digit of destination number is ODD  → REASSIGNED (automatic BLOCK)
  - Final digit of destination number is EVEN → VALID

Fault-injection hook:
  Set SIMULATE_RND_TIMEOUT=true in the environment to force a 4-second sleep,
  which exceeds RND_REQUEST_TIMEOUT_SECONDS (2 s) in the compliance engine and
  triggers the fail-safe BLOCK path, proving the system's fail-closed posture.
"""

import asyncio
import logging
from enum import StrEnum

from app.core.config import settings

logger = logging.getLogger(__name__)


class RNDStatus(StrEnum):
    VALID = "VALID"
    REASSIGNED = "REASSIGNED"


async def check_rnd(destination_number: str) -> RNDStatus:
    """
    Query the mock RND registry for the given destination number.

    When SIMULATE_RND_TIMEOUT is enabled this call will sleep longer than the
    engine's asyncio.timeout() budget, causing a TimeoutError that the engine
    catches and converts to ERR_REGISTRY_TIMEOUT_FAIL_SAFE.
    """
    if settings.SIMULATE_RND_TIMEOUT:
        logger.debug(
            "RND fault-injection active — sleeping %.1f s",
            settings.RND_TIMEOUT_DURATION_SECONDS,
        )
        await asyncio.sleep(settings.RND_TIMEOUT_DURATION_SECONDS)

    digits = "".join(ch for ch in destination_number if ch.isdigit())

    if not digits:
        # Unparseable number — fail-closed
        logger.warning("RND received unparseable number '%s' — REASSIGNED", destination_number)
        return RNDStatus.REASSIGNED

    last_digit = int(digits[-1])
    status = RNDStatus.REASSIGNED if last_digit % 2 != 0 else RNDStatus.VALID

    logger.debug("RND check %s → last_digit=%d → %s", destination_number, last_digit, status)
    return status
