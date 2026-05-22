Since I am an AI operating right here in your chat interface, I cannot generate an external hosting hyperlink or a direct server download button. However, I have packaged the **entire finalized PRD** into a single, clean, copyable code block below.

### How to Save Your File:

1. Hover over the top-right corner of the block below and click **Copy**.
2. Open your favorite text editor (VS Code, Notepad, Cursor, etc.).
3. Paste the contents and save the file as **PRD.md** directly in your project root folder.

---

```markdown
# Product Requirement Document (PRD)
## Project Name: SovereignShield (AI-Powered Telemarketing Compliance Engine)

---

## 1. Executive Summary & Objective
SovereignShield is a localized, high-performance, asynchronous API gateway designed to act as a compliance firewall for outbound telemarketing systems. Operating under the structural logic of the North American Numbering Plan (NANPA) but focusing primarily on TCPA (Telephone Consumer Protection Act) and TSR (Telemarketing Sales Rule) boundaries, this system evaluates dialing compliance in milliseconds. 

As a portfolio project, this application is designed to run **completely locally** without external API costs or external cloud infrastructure dependencies. It demonstrates cutting-edge engineering paradigms: asynchronous request lifecycle orchestration, algorithmic data scrubbing optimization (O(1) lookups), local deployment of Small Language Models (SLMs) for non-trivial Natural Language Processing (NLP) tasks, and data integrity verification via cryptographic ledgers.

---

## 2. Technical Architecture & System Overview
The system exposes an asynchronous proxy endpoint that checks every dial request against a sequential multi-stage validation pipeline before returning an approval code (`ALLOW`) or an error block (`BLOCK`).

### Core System Stack
* **Framework:** FastAPI (Python 3.11+) utilizing `asyncio` for non-blocking I/O execution.
* **Database Layer:** SQLite (configured for WAL mode to simulate high-throughput performance) utilizing SQLAlchemy Async Engine.
* **AI Core:** Ollama running `llama3:8b` or `mistral` locally via the `ollama` or `langchain-ollama` SDK.
* **Cryptography:** Standard library `hashlib` implementing SHA-256 block architectures.

---

## 3. Detailed Component Specifications

### Module 1: Async Ingestion Proxy Layer
* **Endpoint:** `POST /api/v1/dial-check`
* **Purpose:** Serve as a gatekeeper proxy. A dialing system fires a request here prior to placing a SIP connection.
* **Request Payload Verification (Pydantic v2 BaseModel):**
  
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

* **Validation Execution Flow:**
1. Parse international formatting to isolate the 3-digit NANPA Area Code.
2. Fork validation tracks: run simultaneous Async DB queries (DNC lookup, state-hour checking) and API mock conditions via `asyncio.gather()`.



### Module 2: Compliance Rules & Time-Zone Mapping Engine

* **Area Code Resolution:** Map the incoming destination area code to its standardized US state and default timezone.
* **Dynamic Local Time Computation:**
* Read incoming ISO timestamp (`timestamp`).
* Convert this timestamp into the *recipient's local time zone*.
* Compare the computed local time against the specific legal calling window dictated by that state's unique "mini-TCPA" legislation.


* **State Constraint Rules Ruleset Data:**
* *Federal Standard:* 08:00:00 to 21:00:00.
* *Florida (FL) & Connecticut (CT):* 08:00:00 to 20:00:00.


* **DNC Memory-Mapped Buffer:** Load a mock CSV dataset containing 100,000 blacklisted numbers into an in-memory Python `set` structure during application startup to maximize evaluation speeds (O(1) index time complexity).

### Module 3: Local AI NLP Revocation Parser

* **Endpoint:** `POST /api/v1/analyze-transcript`
* **Purpose:** Process live conversation strings or post-call text fragments to intercept informal consent revocations.
* **Local Model Driver:** Interface directly with a local instance of Ollama (`llama3:8b`).
* **Structured JSON Output Protocol:** Utilize strict JSON prompting or Pydantic output parsing where the local model must return a standardized analysis schema.
* **Target Edge Cases to Flag:**
* "Take me off this list." (Standard)
* "I'm broke, stop texting me." (Financial context revocation)
* "Don't ever call this line again." (Explicit categorical withdrawal)



### Module 4: Decoupled Registry Mocking Framework

To demonstrate architectural decouple rules without active paid connections, build an explicit simulation abstraction layer:

* **Reassigned Numbers Database (RND) Mock:** Simulates the FCC’s real-time portal.
* *Deterministic Rule Logic:* If the final digit of the `destination_number` is odd, evaluate as `REASSIGNED` (triggering an automatic `BLOCK`). If even, evaluate as `VALID`.


* **Fault Tolerance Testing Hooks:** Implement an environment variable switch (`SIMULATE_RND_TIMEOUT=True`) which forces the mock registry to sleep for 4.0 seconds, allowing testing of the system's "Fail-Safe Block" logic (timeouts must automatically default to blocking a call to prevent liability).

### Module 5: Append-Only Cryptographic Ledger

* **Purpose:** Generate an unalterable audit trial of all machine evaluations.
* **Data Chaining Method:**
* Combine: `call_id` + `destination_number` + `final_decision` + `timestamp`.
* Calculate a deterministic cryptographic hash of the combined string using `hashlib.sha256()`.
* Save the calculated hash along with the decision parameters into a dedicated row inside the `compliance_audit_ledger` table.



---

## 4. Database Schema Specifications

### Table 1: `state_dialing_rules`

| Column Name | Data Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique row identifier |
| `state_code` | VARCHAR(2) | UNIQUE, NOT NULL | Standard postal abbreviation (e.g., 'FL') |
| `start_time` | TIME | NOT NULL | Daily legal dial window opening hour |
| `end_time` | TIME | NOT NULL | Daily legal dial window closing hour |

### Table 2: `compliance_audit_ledger`

| Column Name | Data Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Sequential ID |
| `call_id` | VARCHAR(36) | NOT NULL, UNIQUE | Input tracking UUID |
| `destination` | VARCHAR(15) | NOT NULL | Dialed phone number |
| `decision` | VARCHAR(10) | NOT NULL | Result outcome (`ALLOW` or `BLOCK`) |
| `block_reason` | VARCHAR(100) | NULLABLE | Reason code if blocked |
| `record_hash` | VARCHAR(64) | NOT NULL | SHA-256 checksum value |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Database insert record time |

---

## 5. System Execution Flow Matrix

| Call Type | Context Conditions | Target Timezone Time | Expected API Status | Reason Code Output |
| --- | --- | --- | --- | --- |
| `AI_VOICE_BOT` | PEWC Consent Present | 14:30:00 (Valid) | `ALLOW` | `NULL` |
| `TELEMARKETING` | DNC Record Match | 10:15:00 (Valid) | `BLOCK` | `ERR_NATIONAL_DNC_MATCH` |
| `AI_VOICE_BOT` | Standard Express Consent Only | 11:00:00 (Valid) | `BLOCK` | `ERR_AI_REQUIRES_PEWC_CONSENT` |
| `TELEMARKETING` | Destination State: FL | 20:15:00 (Late Night) | `BLOCK` | `ERR_STATE_WINDOW_VIOLATION` |
| `TELEMARKETING` | RND Endpoint Simulates Failure | 12:00:00 (Valid) | `BLOCK` | `ERR_REGISTRY_TIMEOUT_FAIL_SAFE` |

---

## 6. Success Metrics & Demonstration Targets

* **Internal Processing Latency:** Pipeline calculations (excluding active local AI transcript execution) must resolve under **15ms**.
* **Deterministic Edge Handling:** Fail-safe mechanics must maintain a 100% block-on-fault execution posture during network simulation failures.

```

```