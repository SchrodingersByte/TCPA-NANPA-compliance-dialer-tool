# CLAUDE.md - Developer Execution Manual
## Project Framework: SovereignShield Local Compliance Engine[cite: 1]

This document provides system structure, implementation conventions, commands, and architecture rules for building and managing the SovereignShield local compliance engine[cite: 1].

---

## 1. Local Architecture Directory Tree
Ensure your workspace remains organized according to this clean structure[cite: 1]:
```text
sovereign_shield/
│
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI Application Entrypoint
│   │
│   ├── core/
│   │   ├── config.py           # Environment Variables & App Constants
│   │   ├── security.py         # SHA-256 Ledger Hashing Algorithms
│   │   └── timezone_maps.py   # Fixed Area Code to State / TZ Matrix
│   │
│   ├── database/
│   │   ├── connection.py       # Async SQLAlchemy Session Engine
│   │   └── models.py           # SQLAlchemy Declarative Database Schemas
│   │
│   ├── services/
│   │   ├── compliance_engine.py# Core Execution Validation Orchestrator
│   │   ├── local_llm.py        # Ollama SDK Integration Layer
│   │   └── mock_registry.py    # RND Failure-Simulation Sandbox
│   │
│   └── schemas/
│       └── validation.py       # Pydantic v2 Ingestion Verification Schemas
│
├── data/
│   └── mock_dnc_list.csv       # 100k Row Seed Dataset File
│
├── tests/
│   ├── __init__.py
│   ├── test_gateway.py        # Pipeline Verification Integration Suite
│   └── test_nlp_engine.py     # AI NLP Opt-out Verification Target Unit Tests
│
├── requirements.txt            # System Dependencies Blueprint
└── README.md

```

---

## 2. Technical Stack Operations Command Sheet



### Setting Up Environment & Dependencies



```bash
# Create local virtual environment
python3 -m venv venv
source venv/bin/activate

# Install required dependencies
pip install fastapi uvicorn sqlalchemy aiomysql aiofiles pydantic ollama pytest httpx

```

### Starting the Local AI Engine (Ollama)



Ensure Ollama is actively running on your host system before initiating execution:

```bash
# Verify Ollama service is reachable
ollama --version

# Download the baseline lightweight model
ollama pull llama3:8b

```

### Running the Application Engine



```bash
# Run FastAPI server locally with real-time reload enabled
uvicorn app.main:app --reload --port 8000

```

### Running the Test Infrastructure Suites



```bash
# Run complete validation integration and system suites
pytest -v

```

---

## 3. Mandatory Development Rules & Code Styling Guidelines



### Asynchronous Execution Standards



* All database operations, external file readings (`aiofiles`), and local AI modeling tasks **MUST** utilize explicit `async/await` syntax.


* Never use synchronous blocking code (`time.sleep()`, native `open()`, or synchronous `requests`) inside processing pathways. Use `asyncio.sleep()` or `httpx.AsyncClient` if external requests are added.



### Type Hints & Verification



* All functional definitions must declare complete input type hints and precise return values (e.g., `async def evaluate_dial(payload: DialIngestion) -> dict:`).


* Strictly implement Pydantic v2 structures for managing input data validation layers.



### Fail-Safe Defensive Design Principles



* **Data Isolation:** All compliance checks must run within an enterprise `try/except` perimeter block.


* **Fail-Closed Architecture Strategy:** If an unhandled exception or connection error occurs inside a validation subroutine (such as a timeout mock), the engine **must intercept the fault and return a `BLOCK` outcome**. Giving a compliance waiver on a system fault is fundamentally forbidden.



### Database Operations Constraint



* Maintain a highly efficient footprint: instantiate database schemas locally via SQLite inside memory storage or a single local transactional file layout (`sovereign_shield.db`).


* Seed state tables with baseline parameters (`FL`, `CT`, `Federal`) automatically upon server execution initialization inside `main.py`.



```

```