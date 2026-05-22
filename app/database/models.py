from datetime import datetime, time

from sqlalchemy import DateTime, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class StateDialingRule(Base):
    """
    Legal calling-window constraints per US state (or federal default).

    state_code 'US' represents the federal TCPA safe-harbor window and acts as
    the fallback when no state-specific row is found by the compliance engine.
    """

    __tablename__ = "state_dialing_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    state_code: Mapped[str] = mapped_column(
        String(2), unique=True, nullable=False, index=True
    )
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<StateDialingRule state={self.state_code!r} "
            f"window={self.start_time}-{self.end_time}>"
        )


class ComplianceAuditLedger(Base):
    """
    Append-only SHA-256 chained audit record for every evaluated dial request.

    record_hash binds call_id + destination + decision + created_at into a
    deterministic fingerprint; any post-hoc tampering breaks the hash chain.
    """

    __tablename__ = "compliance_audit_ledger"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    call_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    destination: Mapped[str] = mapped_column(String(15), nullable=False)
    decision: Mapped[str] = mapped_column(String(10), nullable=False)
    block_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLedger call_id={self.call_id!r} "
            f"decision={self.decision!r} hash={self.record_hash[:12]}…>"
        )
