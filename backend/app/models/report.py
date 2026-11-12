import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.core import UUID_TYPE

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


def now() -> datetime:
    return datetime.now(UTC)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    report_type: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(30), default="generated", index=True)
    scope: Mapped[dict] = mapped_column(JSON_TYPE, default=dict)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    evidence_sources: Mapped[list] = mapped_column(JSON_TYPE, default=list)
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)
    object_ref: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
