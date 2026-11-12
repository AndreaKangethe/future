import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")
UUID_TYPE = String(36)


def now() -> datetime:
    return datetime.now(UTC)


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(150), index=True)
    version: Mapped[str] = mapped_column(String(50))
    model_type: Mapped[str] = mapped_column(String(50), default="anomaly")
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    artifact_uri: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    model_metadata: Mapped[dict] = mapped_column(JSON_TYPE, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

    inferences: Mapped[list["ModelInference"]] = relationship(
        back_populates="model", cascade="all, delete-orphan"
    )


class ModelInference(Base):
    __tablename__ = "model_inferences"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    model_id: Mapped[str] = mapped_column(
        UUID_TYPE, ForeignKey("model_registry.id", ondelete="RESTRICT"), index=True
    )
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    input_data: Mapped[dict] = mapped_column(JSON_TYPE, default=dict)
    output_data: Mapped[dict] = mapped_column(JSON_TYPE, default=dict)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_anomaly: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    explanation: Mapped[dict] = mapped_column(JSON_TYPE, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    model: Mapped[ModelRegistry] = relationship(back_populates="inferences")
