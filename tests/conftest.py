"""
pytest configuration for SovereignShield.

Environment variables MUST be set before any app module is imported so that
pydantic-settings reads the test values on first construction.  The module-level
os.environ calls below run during pytest collection, before test files are
imported, which guarantees correct ordering.
"""

import asyncio
import os
import uuid

# ── Override production settings for the test run ─────────────────────────────
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_sovereign_shield.db")
os.environ.setdefault("SIMULATE_RND_TIMEOUT", "false")
os.environ.setdefault("DNC_CSV_PATH", "data/mock_dnc_list.csv")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


# ── Session-level DB init (sync wrapper avoids event-loop scope issues) ────────

@pytest.fixture(scope="session", autouse=True)
def _init_test_db():
    """
    Create tables and seed state rules once before any test runs.
    Uses asyncio.run() so it is independent of the per-function event loop
    that pytest-asyncio manages for each test.
    """
    async def _setup() -> None:
        from app.database.connection import init_db
        from app.services.compliance_engine import load_dnc_cache
        await init_db()
        await load_dnc_cache()   # CSV absent → empty cache, warning logged

    asyncio.run(_setup())
    yield
    # Tear down: remove the test DB file.
    # On Windows, aiosqlite may still hold a file lock at session teardown;
    # PermissionError is suppressed — the file is small and OS-cleaned on next run.
    import gc
    gc.collect()
    try:
        os.remove("test_sovereign_shield.db")
    except (FileNotFoundError, PermissionError):
        pass


# ── Per-test fixtures ──────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Lightweight async HTTP client wired to the FastAPI app (no lifespan)."""
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def call_id() -> str:
    """Unique call UUID for each test to satisfy the audit ledger UNIQUE constraint."""
    return f"test-{uuid.uuid4().hex[:10]}"


# ── Shared payload factory ─────────────────────────────────────────────────────

def make_payload(call_id: str, **overrides) -> dict:
    """
    Return a base-valid DialIngestion dict that can be selectively overridden.

    Defaults:
      - destination: +12125550020  (NY 212, last digit 0=even → VALID RND)
      - timestamp:   2026-05-22T14:30:00Z  (10:30 EDT — within all federal windows)
      - consent:     PEWC
      - call_type:   TELEMARKETING
    """
    base = {
        "call_id": call_id,
        "source_number": "+12025550143",
        "destination_number": "+12125550020",
        "consent_type_held": "PEWC",
        "call_type": "TELEMARKETING",
        "timestamp": "2026-05-22T14:30:00Z",
    }
    base.update(overrides)
    return base
