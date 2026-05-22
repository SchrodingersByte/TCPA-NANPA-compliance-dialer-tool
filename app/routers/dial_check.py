import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import append_audit_record
from app.database.connection import get_db
from app.schemas.validation import (
    DialCheckResponse,
    DialIngestion,
    TranscriptAnalysisRequest,
    TranscriptAnalysisResponse,
)
from app.services.compliance_engine import evaluate_dial
from app.services.local_llm import analyze_transcript_for_opt_out

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["compliance"])


@router.post(
    "/dial-check",
    response_model=DialCheckResponse,
    summary="Evaluate a dial request for TCPA compliance",
    description=(
        "Runs the full compliance pipeline: consent gate → concurrent DNC / "
        "time-window / RND checks → SHA-256 audit ledger write. "
        "Always returns a decision; never raises on compliance logic errors."
    ),
)
async def dial_check(
    payload: DialIngestion,
    session: AsyncSession = Depends(get_db),
) -> DialCheckResponse:
    result = await evaluate_dial(payload, session)

    # Write to the append-only audit ledger; duplicate call_id is silently skipped.
    try:
        await append_audit_record(
            session,
            call_id=payload.call_id,
            destination=payload.destination_number,
            decision=result.decision,
            block_reason=result.block_reason,
            request_timestamp=payload.timestamp,
        )
        await session.commit()
    except IntegrityError:
        await session.rollback()
        logger.warning(
            "Duplicate call_id=%s — audit write skipped, decision returned as-is",
            payload.call_id,
        )
    except Exception as exc:
        await session.rollback()
        logger.error(
            "Audit ledger write failed for call_id=%s: %s",
            payload.call_id, exc, exc_info=True,
        )
        # Decision is still returned — the compliance verdict was already made.

    return result


@router.post(
    "/analyze-transcript",
    response_model=TranscriptAnalysisResponse,
    summary="Detect opt-out signals in a call transcript using local AI",
    description=(
        "Submits transcript text to the local Ollama model for TCPA opt-out "
        "classification. Fail-closed: if the model is offline or returns malformed "
        "output, opt_out_detected=True is assumed to protect the consumer."
    ),
)
async def analyze_transcript(
    payload: TranscriptAnalysisRequest,
) -> TranscriptAnalysisResponse:
    return await analyze_transcript_for_opt_out(payload.transcript, payload.call_id)
