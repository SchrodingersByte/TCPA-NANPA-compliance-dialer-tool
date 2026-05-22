"""
Ollama local-model integration for TCPA opt-out NLP analysis.

This module drives a locally-running Ollama instance (llama3:8b by default) to
classify whether a conversation transcript contains an informal consent revocation
or opt-out request under the TCPA.

Fail-closed posture
───────────────────
If the Ollama service is unreachable, times out, or returns malformed JSON, the
function returns opt_out_detected=True with confidence=0.0 rather than assuming
the consumer did NOT opt out. This is intentional: a false positive (unnecessary
suppression of a call) is always preferable to a false negative (continuing to
contact a consumer who withdrew consent).

Structured output
─────────────────
The prompt instructs the model to return ONLY a JSON object matching
TranscriptAnalysisResponse. The `format="json"` parameter to ollama.chat()
enforces valid JSON at the token-sampling level. The parser then validates the
fields and applies defaults for any missing keys.
"""

import asyncio
import json
import logging
from typing import Any

from ollama import AsyncClient, ResponseError

from app.core.config import settings
from app.schemas.validation import TranscriptAnalysisResponse

logger = logging.getLogger(__name__)

# ── Module-level Ollama client (no connection opened until first request) ──────
_ollama_client: AsyncClient = AsyncClient(host=settings.OLLAMA_BASE_URL)


# ── System prompt ──────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a strict TCPA compliance analyst AI. \
Your only task is to classify whether a call transcript contains a consumer \
opt-out or consent revocation signal under the Telephone Consumer Protection Act.

Respond ONLY with a valid JSON object — no markdown, no explanation, nothing else.

Required JSON schema:
{
  "opt_out_detected": <true or false>,
  "confidence": <float 0.0–1.0>,
  "matched_phrase": <exact phrase that triggered detection, or null if none>,
  "reasoning": <one concise sentence explaining the classification>
}

Classification rules:
- opt_out_detected = true for ANY of:
    * Explicit stop requests ("remove me", "stop calling", "take me off your list")
    * Categorical withdrawal ("don't ever call this line again", "never contact me")
    * Informal revocation with stop intent ("I'm broke, stop texting me")
    * Future-tense opt-outs ("don't call me anymore", "I don't want these calls")
    * Partial or ambiguous stop signals (when in doubt → true)
- opt_out_detected = false ONLY when no stop/revocation signal is present
- When uncertain, always default to opt_out_detected = true (consumer protection)
- confidence reflects how clearly the signal appears in the transcript (0.0–1.0)"""


# ── Internal helpers ───────────────────────────────────────────────────────────

def _fail_closed_response(call_id: str, reason: str) -> TranscriptAnalysisResponse:
    """Return a conservative opt-out=True result when the LLM is unavailable."""
    logger.warning("Returning fail-closed opt-out response for call_id=%s: %s", call_id, reason)
    return TranscriptAnalysisResponse(
        call_id=call_id,
        opt_out_detected=True,
        confidence=0.0,
        matched_phrase=None,
        reasoning=f"NLP analysis unavailable ({reason}) — opt-out assumed for consumer protection.",
    )


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers that some models add despite format=json."""
    text = text.strip()
    if text.startswith("```"):
        newline_pos = text.find("\n")
        text = text[newline_pos + 1:] if newline_pos != -1 else text[3:]
        fence_pos = text.rfind("```")
        if fence_pos != -1:
            text = text[:fence_pos]
    return text.strip()


def _parse_llm_json(raw: Any, call_id: str) -> TranscriptAnalysisResponse:
    """
    Convert the model's raw output into a validated TranscriptAnalysisResponse.
    Applies safe defaults for any missing or malformed keys.
    """
    if isinstance(raw, str):
        raw = _strip_markdown_fences(raw)
        try:
            data: dict = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error("JSON parse failed for call_id=%s: %s | raw=%r", call_id, exc, raw[:200])
            return _fail_closed_response(call_id, "model returned invalid JSON")
    elif isinstance(raw, dict):
        data = raw
    else:
        return _fail_closed_response(call_id, f"unexpected response type {type(raw).__name__}")

    try:
        confidence = float(data.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))  # clamp to [0, 1]
    except (TypeError, ValueError):
        confidence = 0.5

    return TranscriptAnalysisResponse(
        call_id=call_id,
        opt_out_detected=bool(data.get("opt_out_detected", True)),
        confidence=confidence,
        matched_phrase=data.get("matched_phrase") or None,
        reasoning=str(data.get("reasoning", "No reasoning provided by model.")),
    )


# ── Public entry point ─────────────────────────────────────────────────────────

async def analyze_transcript_for_opt_out(
    transcript: str,
    call_id: str,
) -> TranscriptAnalysisResponse:
    """
    Submit a call transcript to the local Ollama model and return a structured
    opt-out classification.

    Always returns a TranscriptAnalysisResponse — never raises. Any failure
    (model offline, timeout, bad JSON) triggers the fail-closed opt_out=True path.
    """
    if not transcript or not transcript.strip():
        return _fail_closed_response(call_id, "empty transcript supplied")

    user_message = f"Analyze this call transcript for opt-out signals:\n\n{transcript.strip()}"

    try:
        async with asyncio.timeout(settings.OLLAMA_TIMEOUT_SECONDS):
            response = await _ollama_client.chat(
                model=settings.OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user",   "content": user_message},
                ],
                format="json",
            )

        # Normalise across SDK versions: message.content may be str or dict
        content = response.message.content

        result = _parse_llm_json(content, call_id)

        logger.info(
            "NLP analysis call_id=%s opt_out=%s confidence=%.2f phrase=%r",
            call_id,
            result.opt_out_detected,
            result.confidence,
            result.matched_phrase,
        )
        return result

    except TimeoutError:
        return _fail_closed_response(
            call_id,
            f"Ollama timed out after {settings.OLLAMA_TIMEOUT_SECONDS}s",
        )
    except ConnectionError as exc:
        return _fail_closed_response(call_id, f"Ollama unreachable: {exc}")
    except ResponseError as exc:
        # Ollama is running but returned an HTTP error (e.g. model not pulled yet)
        logger.warning("Ollama ResponseError for call_id=%s: %s", call_id, exc)
        return _fail_closed_response(call_id, f"Ollama error: {exc}")
    except Exception as exc:
        logger.error(
            "Unexpected LLM error for call_id=%s: %s",
            call_id, exc, exc_info=True,
        )
        return _fail_closed_response(call_id, f"unexpected error: {type(exc).__name__}")
