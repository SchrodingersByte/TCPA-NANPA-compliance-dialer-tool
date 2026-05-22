from collections.abc import AsyncGenerator
from datetime import time as dt_time

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# ── Declarative base shared by all ORM models ─────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── Engine ────────────────────────────────────────────────────────────────────

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, connection_record) -> None:
    """Enable WAL journal mode and recommended SQLite performance settings."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA cache_size=-64000")   # 64 MB page cache
    cursor.close()


# ── Session factory ───────────────────────────────────────────────────────────

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── FastAPI dependency ─────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# ── Startup: table creation + seed data ──────────────────────────────────────

_SEED_STATE_RULES: list[dict] = [
    # Federal TCPA safe-harbor (used as fallback for all unlisted states)
    {"state_code": "US", "start_time": dt_time(8, 0, 0), "end_time": dt_time(21, 0, 0)},
    # Florida mini-TCPA — 1-hour earlier cutoff
    {"state_code": "FL", "start_time": dt_time(8, 0, 0), "end_time": dt_time(20, 0, 0)},
    # Connecticut mini-TCPA — 1-hour earlier cutoff
    {"state_code": "CT", "start_time": dt_time(8, 0, 0), "end_time": dt_time(20, 0, 0)},
]


async def init_db() -> None:
    """
    Create all tables (idempotent) and seed baseline state dialing rules.

    The lazy import of `app.database.models` is intentional — it registers all
    ORM model classes with Base.metadata before `create_all` is called, without
    creating a circular import at module load time.
    """
    import app.database.models as _models  # noqa: F401
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        for row in _SEED_STATE_RULES:
            stmt = (
                sqlite_insert(_models.StateDialingRule)
                .values(**row)
                .on_conflict_do_nothing()   # skip silently if state_code already exists
            )
            await session.execute(stmt)
        await session.commit()
