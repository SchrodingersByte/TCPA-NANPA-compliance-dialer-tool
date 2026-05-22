# SovereignShield

An AI-powered, local telemarketing compliance engine that acts as a real-time gatekeeper proxy for outbound dialing systems. Every call is evaluated against a multi-stage TCPA/TSR compliance pipeline before a SIP connection is placed.

The system runs **entirely on your local machine** — no external APIs, no cloud costs, no data leaving your environment.

---

## What It Does

A dialing system fires a request to `/api/v1/dial-check` before placing a call. SovereignShield runs the number through a sequential compliance pipeline and returns `ALLOW` or `BLOCK` within milliseconds, along with a cryptographically-signed audit record.

```
Dialing System
     |
     v
POST /api/v1/dial-check
     |
     +-- [Stage 1]  Consent Gate (synchronous, zero I/O)
     |               AI_VOICE_BOT requires PEWC consent.
     |               Any other consent type -> immediate BLOCK.
     |
     +-- [Stage 2]  asyncio.gather() — three concurrent checks
     |               |
     |               +-- National DNC   O(1) in-memory set  (100k entries at startup)
     |               +-- State window   async DB query + IANA local-time conversion
     |               +-- RND registry   async mock + asyncio.timeout() fail-safe
     |
     +-- [Stage 3]  First failure wins -> BLOCK
     |               All three pass     -> ALLOW
     |
     +-- SHA-256 audit record written to compliance_audit_ledger
     |
     v
DialCheckResponse  {decision, block_reason, evaluated_state, local_call_time, ...}
```

A second endpoint, `/api/v1/analyze-transcript`, submits post-call conversation text to a locally-running Ollama model for TCPA opt-out detection.

---

## Tech Stack

| Layer | Technology |
|---|---|
| API framework | FastAPI + uvicorn (async ASGI) |
| Database | SQLite in WAL mode via SQLAlchemy async + aiosqlite |
| Data validation | Pydantic v2 (`AwareDatetime`, `StringConstraints`) |
| Local AI | Ollama (`llama3:8b`) via the `ollama` Python SDK |
| Cryptography | `hashlib.sha256` (stdlib) |
| Timezone routing | `zoneinfo` (stdlib) + `tzdata` (334 NANPA area codes) |
| Testing | pytest + pytest-asyncio + httpx |

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | `zoneinfo` and `asyncio.timeout()` are used throughout |
| Ollama | Required only for `/api/v1/analyze-transcript`. The compliance pipeline runs without it. |
| `llama3:8b` model | Pull once with `ollama pull llama3:8b` |

---

## Quick Start

### 1. Create and activate a virtual environment

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Generate the mock DNC dataset

```bash
python data/generate_dnc.py
```

This writes `data/mock_dnc_list.csv` — 100,000 unique E.164 phone numbers seeded deterministically (seed = 42). The file is loaded into an in-memory `set` at startup for O(1) lookups.

### 4. Start the local AI engine (optional)

Skip this step if you only need the compliance pipeline. The transcript endpoint degrades gracefully to a fail-closed opt-out response when Ollama is unreachable.

```bash
ollama pull llama3:8b
ollama serve        # or start the Ollama desktop app
```

### 5. Run the server

```bash
uvicorn app.main:app --reload --port 8000
```

On first startup, the server automatically:
- Creates `sovereign_shield.db` (SQLite, WAL mode)
- Creates and seeds `state_dialing_rules` with federal, FL, and CT windows
- Loads the DNC CSV into the in-memory cache

Interactive API docs are available at `http://localhost:8000/docs`.

---

## Configuration

All settings are read from environment variables or a `.env` file in the project root. Every value has a working default — no `.env` is required for local development.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./sovereign_shield.db` | SQLAlchemy async connection string |
| `DB_ECHO` | `false` | Log all SQL statements (useful for debugging) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server address |
| `OLLAMA_MODEL` | `llama3:8b` | Model used for transcript analysis |
| `OLLAMA_TIMEOUT_SECONDS` | `30.0` | Hard timeout for LLM inference |
| `SIMULATE_RND_TIMEOUT` | `false` | Set `true` to force the RND mock to sleep 4 s, triggering the fail-safe BLOCK path |
| `RND_REQUEST_TIMEOUT_SECONDS` | `2.0` | Budget for each RND registry check |
| `DNC_CSV_PATH` | `data/mock_dnc_list.csv` | Path to the DNC seed file (relative to project root) |

Example `.env`:

```dotenv
DEBUG=true
DB_ECHO=false
SIMULATE_RND_TIMEOUT=false
OLLAMA_MODEL=llama3:8b
```

---

## API Reference

### POST /api/v1/dial-check

Evaluates a single dial request against the full compliance pipeline.

**Request**

```json
{
  "call_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "source_number": "+12025550143",
  "destination_number": "+14155552671",
  "consent_type_held": "PEWC",
  "call_type": "AI_VOICE_BOT",
  "timestamp": "2026-05-22T20:15:00Z"
}
```

| Field | Type | Values |
|---|---|---|
| `call_id` | `string` | Any UUID or unique identifier |
| `source_number` | `string` | E.164 NANPA (`+1` + 10 digits) |
| `destination_number` | `string` | E.164 NANPA (`+1` + 10 digits) |
| `consent_type_held` | `enum` | `PEWC` · `EXPRESS_WRITTEN` · `VERBAL` · `NONE` |
| `call_type` | `enum` | `AI_VOICE_BOT` · `TELEMARKETING` · `INFORMATIONAL` |
| `timestamp` | `datetime` | ISO 8601 with timezone (`Z` or offset) |

**Response**

```json
{
  "call_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "decision": "BLOCK",
  "block_reason": "ERR_STATE_WINDOW_VIOLATION",
  "evaluated_state": "FL",
  "evaluated_timezone": "America/New_York",
  "local_call_time": "16:15:00 EDT",
  "processing_ms": 4.812
}
```

| Field | Description |
|---|---|
| `decision` | `ALLOW` or `BLOCK` |
| `block_reason` | `null` on `ALLOW`; error code string on `BLOCK` |
| `evaluated_state` | 2-letter state code resolved from the destination area code |
| `evaluated_timezone` | IANA timezone used for local-time conversion |
| `local_call_time` | Recipient's local time at the moment of the call |
| `processing_ms` | End-to-end pipeline latency in milliseconds |

**Block reason codes**

| Code | Trigger |
|---|---|
| `ERR_NATIONAL_DNC_MATCH` | Destination number found in the DNC cache |
| `ERR_STATE_WINDOW_VIOLATION` | Call time falls outside the state's legal calling window |
| `ERR_AI_REQUIRES_PEWC_CONSENT` | `AI_VOICE_BOT` call without `PEWC` consent |
| `ERR_RND_REASSIGNED` | RND registry reports the number has been reassigned |
| `ERR_REGISTRY_TIMEOUT_FAIL_SAFE` | RND check exceeded its timeout budget |
| `ERR_SYSTEM_FAULT` | Unhandled internal exception — fail-closed default |

---

### POST /api/v1/analyze-transcript

Submits a call transcript to the local Ollama model for opt-out detection.

**Request**

```json
{
  "call_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "transcript": "I'm not interested. Take me off this list and don't call again."
}
```

**Response**

```json
{
  "call_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "opt_out_detected": true,
  "confidence": 0.97,
  "matched_phrase": "Take me off this list",
  "reasoning": "Consumer issued an explicit request to stop contact."
}
```

The model is instructed to default to `opt_out_detected: true` when the signal is ambiguous. If Ollama is unreachable or returns malformed output, the endpoint returns `opt_out_detected: true` with `confidence: 0.0` — consumer protection is never sacrificed for uptime.

**Edge cases the model is prompted to flag**

- *Standard:* "Take me off this list."
- *Financial context:* "I'm broke, stop texting me."
- *Categorical withdrawal:* "Don't ever call this line again."

---

### GET /health

Returns server status and DNC cache cardinality.

```json
{
  "status": "ok",
  "version": "1.0.0",
  "dnc_cache_entries": "100000"
}
```

---

## Execution Flow Matrix

| Call Type | Context | Local Time | Decision | Block Reason |
|---|---|---|---|---|
| `AI_VOICE_BOT` | PEWC consent held | 14:30 (valid) | `ALLOW` | — |
| `TELEMARKETING` | Number on DNC list | 10:15 (valid) | `BLOCK` | `ERR_NATIONAL_DNC_MATCH` |
| `AI_VOICE_BOT` | Express consent only | 11:00 (valid) | `BLOCK` | `ERR_AI_REQUIRES_PEWC_CONSENT` |
| `TELEMARKETING` | Destination state FL | 20:15 (after cutoff) | `BLOCK` | `ERR_STATE_WINDOW_VIOLATION` |
| `TELEMARKETING` | RND registry unreachable | 12:00 (valid) | `BLOCK` | `ERR_REGISTRY_TIMEOUT_FAIL_SAFE` |

**State calling windows seeded at startup**

| State | Window | Notes |
|---|---|---|
| Federal (all unlisted states) | 08:00 – 21:00 local | TCPA safe-harbor |
| Florida | 08:00 – 20:00 local | Mini-TCPA stricter cutoff |
| Connecticut | 08:00 – 20:00 local | Mini-TCPA stricter cutoff |

Times are always evaluated in the **recipient's local timezone**, resolved by area code. Area code 850 (FL panhandle), for example, maps to `state=FL` but `timezone=America/Chicago` — the 20:00 FL cutoff is enforced in Central Time.

---

## Running Tests

```bash
pytest -v
```

The test database (`test_sovereign_shield.db`) is created automatically and cleaned up after the session. Ollama is not required — all async tests that call `analyze_transcript_for_opt_out` verify the fail-closed guarantee rather than model accuracy.

```
collected 40 items

tests/test_gateway.py::test_allow_pewc_valid_time_valid_rnd          PASSED
tests/test_gateway.py::test_block_ai_voice_bot_requires_pewc          PASSED
tests/test_gateway.py::test_block_state_window_fl_panhandle           PASSED
tests/test_gateway.py::test_block_rnd_reassigned_odd_digit            PASSED
tests/test_gateway.py::test_block_national_dnc_match                  PASSED
tests/test_gateway.py::test_block_rnd_registry_timeout                PASSED
... (34 more)

40 passed in 8.11s
```

### Fault injection

To verify the fail-safe BLOCK behaviour end-to-end, set the environment variable before starting the server:

```bash
SIMULATE_RND_TIMEOUT=true uvicorn app.main:app --port 8000
```

Every call to `/api/v1/dial-check` will force the RND mock to sleep for 4 seconds (exceeding the 2-second budget), producing `ERR_REGISTRY_TIMEOUT_FAIL_SAFE` for all requests regardless of number parity.

---

## Project Structure

```
.
├── app/
│   ├── core/
│   │   ├── config.py           # Pydantic Settings — all tuneable constants
│   │   ├── security.py         # SHA-256 ledger hashing + audit writer
│   │   └── timezone_maps.py    # 334 NANPA area codes -> state + IANA timezone
│   │
│   ├── database/
│   │   ├── connection.py       # Async engine, WAL pragmas, session factory, init_db()
│   │   └── models.py           # StateDialingRule, ComplianceAuditLedger ORM models
│   │
│   ├── routers/
│   │   └── dial_check.py       # POST /api/v1/dial-check, /api/v1/analyze-transcript
│   │
│   ├── schemas/
│   │   └── validation.py       # Pydantic v2 request/response models
│   │
│   ├── services/
│   │   ├── compliance_engine.py# 3-stage pipeline orchestrator + DNC cache loader
│   │   ├── local_llm.py        # Ollama SDK integration + fail-closed NLP parser
│   │   └── mock_registry.py    # Deterministic RND mock with timeout injection
│   │
│   └── main.py                 # FastAPI app, lifespan, router registration
│
├── data/
│   ├── generate_dnc.py         # Reproducible 100k DNC CSV generator (seed=42)
│   └── mock_dnc_list.csv       # Generated DNC seed file
│
├── tests/
│   ├── conftest.py             # Test DB init, async client fixture, payload factory
│   ├── test_gateway.py         # 13 HTTP integration tests
│   └── test_nlp_engine.py      # 27 NLP parsing unit tests
│
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## Design Notes

### Fail-closed architecture

No compliance check is ever skipped on error. If any validation subroutine raises an unhandled exception, the outer `try/except` in `evaluate_dial()` intercepts it and returns `BLOCK` with `ERR_SYSTEM_FAULT`. Giving a compliance waiver on a system fault is categorically forbidden.

The same principle applies to the NLP endpoint: if Ollama is offline, times out, or returns malformed JSON, `opt_out_detected` is set to `True`. A false positive (unnecessary call suppression) is always preferable to a false negative (calling a consumer who has withdrawn consent).

### Async-first execution

All database operations, file reads, and AI model calls use `async/await`. The DNC check, state time-window query, and RND registry call run concurrently via `asyncio.gather()`, keeping pipeline latency well within the 15 ms SLA (AI inference excluded).

### Cryptographic audit trail

Every evaluated call produces a SHA-256 record bound to `call_id | destination | decision | request_timestamp`. The hash is stored in `compliance_audit_ledger` alongside the decision. Any post-hoc modification to any of those fields produces a different hash when recomputed, making tampering detectable.

### DNC lookup performance

The 100,000-entry DNC list is normalised to 10-digit strings and loaded into a Python `set` at startup. Lookup is O(1) regardless of list size, with no database round-trip on the hot path.

### Timezone edge cases

Area codes that cross state time-zone boundaries are resolved to the timezone that covers the majority of the population for that code (e.g., South Dakota 605 maps to `America/Chicago`). The FL panhandle area code 850 is a documented exception: `state_code=FL` (for applying Florida's 20:00 cutoff) but `timezone=America/Chicago` (the physical timezone of the Pensacola/Panama City region).
