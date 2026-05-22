from datetime import datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, StringConstraints

# E.164 NANPA: +1 followed by exactly 10 digits
E164USPhone = Annotated[str, StringConstraints(pattern=r"^\+1\d{10}$")]

ConsentType = Literal["PEWC", "EXPRESS_WRITTEN", "VERBAL", "NONE"]
CallType = Literal["AI_VOICE_BOT", "TELEMARKETING", "INFORMATIONAL"]
Decision = Literal["ALLOW", "BLOCK"]


class DialIngestion(BaseModel):
    """Inbound payload schema for POST /api/v1/dial-check."""

    call_id: str
    source_number: E164USPhone
    destination_number: E164USPhone
    consent_type_held: ConsentType
    call_type: CallType
    timestamp: AwareDatetime  # must be timezone-aware for local-time conversion


class DialCheckResponse(BaseModel):
    """Outbound compliance verdict returned to the dialing system."""

    call_id: str
    decision: Decision
    block_reason: str | None = None
    evaluated_state: str
    evaluated_timezone: str
    local_call_time: str
    processing_ms: float


class TranscriptAnalysisRequest(BaseModel):
    """Inbound payload schema for POST /api/v1/analyze-transcript."""

    call_id: str
    transcript: str


class TranscriptAnalysisResponse(BaseModel):
    """Structured NLP result returned by the local Ollama model."""

    call_id: str
    opt_out_detected: bool
    confidence: float
    matched_phrase: str | None = None
    reasoning: str
