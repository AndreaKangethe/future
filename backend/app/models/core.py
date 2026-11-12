import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

JSON = JSONB().with_variant(Text, "sqlite")
UUID_TYPE = String(36)


def now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="admin")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), index=True)
    asset_type: Mapped[str] = mapped_column(String(50), default="unknown")
    criticality: Mapped[int] = mapped_column(Integer, default=3)
    environment: Mapped[str] = mapped_column(String(50), default="production")
    lifecycle_state: Mapped[str] = mapped_column(String(50), default="active")
    exposure_status: Mapped[str] = mapped_column(String(50), default="unknown")
    identity_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    epistemic_class: Mapped[str] = mapped_column(String(30), default="normalized")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id: Mapped[str] = mapped_column(UUID_TYPE, index=True)
    title: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    cvss_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    contextual_risk: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(30), default="open")
    epistemic_class: Mapped[str] = mapped_column(String(30), default="assessed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
