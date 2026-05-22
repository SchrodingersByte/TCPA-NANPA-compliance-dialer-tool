"""
SHA-256 cryptographic audit ledger for SovereignShield.

Every compliance evaluation produces a deterministic hash that binds the four
immutable fields of the decision together:

    hash = SHA-256( call_id | destination | decision | request_timestamp_iso )

The pipe-delimiter prevents cross-field boundary collisions (e.g., a call_id
ending in "ALLOW" cannot be made to collide with a different field combination).

The hash is stored alongside the record in `compliance_audit_ledger`. Any
post-hoc modification to call_id, destination, or decision will produce a
different hash when recomputed, making tampering detectable.

Note: `created_at` (the DB insert timestamp) is intentionally excluded from the
hash so that the fingerprint can be computed before the INSERT executes and
verified later using only the original request payload — no DB round-trip needed.
"""

import hashlib
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ComplianceAuditLedger

logger = logging.getLogger(__name__)

_FIELD_SEPARATOR = "|"


# ── Hash primitives ────────────────────────────────────────────────────────────

def compute_record_hash(
    call_id: str,
    destination: str,
    decision: str,
    request_timestamp_iso: str,
) -> str:
    """
    Produce a deterministic 64-character hex SHA-256 fingerprint.

    All four inputs are required. The resulting hash is stored in
    compliance_audit_ledger.record_hash.
    """
    raw = _FIELD_SEPARATOR.join([call_id, destination, decision, request_timestamp_iso])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_record_hash(
    record: ComplianceAuditLedger,
    request_timestamp_iso: str,
) -> bool:
    """
    Recompute the expected hash for a ledger row and compare to the stored value.

    Returns True if the record is intact, False if any field was altered after
    insertion. The caller must supply the original request timestamp ISO string
    (e.g. payload.timestamp.isoformat()) since it is not persisted in the DB.
    """
    expected = compute_record_hash(
        record.call_id,
        record.destination,
        record.decision,
        request_timestamp_iso,
    )
    match = record.record_hash == expected
    if not match:
        logger.warning(
            "Hash mismatch for call_id=%s — stored=%s expected=%s",
            record.call_id,
            record.record_hash[:16],
            expected[:16],
        )
    return match


# ── Ledger writer ──────────────────────────────────────────────────────────────

async def append_audit_record(
    session: AsyncSession,
    *,
    call_id: str,
    destination: str,
    decision: str,
    block_reason: str | None,
    request_timestamp: datetime,
) -> ComplianceAuditLedger:
    """
    Hash and stage one compliance decision into the append-only audit ledger.

    Flushes the new row so the generated primary key is available on the returned
    object, but does NOT commit — the route handler owns the transaction boundary
    and commits after this returns.
    """
    try:
        record_hash = compute_record_hash(
            call_id,
            destination,
            decision,
            request_timestamp.isoformat(),
        )

        record = ComplianceAuditLedger(
            call_id=call_id,
            destination=destination,
            decision=decision,
            block_reason=block_reason,
            record_hash=record_hash,
        )
        session.add(record)
        await session.flush()

        logger.debug(
            "Audit record staged: call_id=%s decision=%s hash=%s...",
            call_id, decision, record_hash[:16],
        )
        return record

    except Exception as exc:
        logger.error(
            "Failed to stage audit record for call_id=%s: %s",
            call_id, exc, exc_info=True,
        )
        raise
