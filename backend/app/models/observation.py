import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")
UUID_TYPE = String(36)


def now() -> datetime:
    return datetime.now(UTC)


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    source_type: Mapped[str] = mapped_column(String(50), default="manual")
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    reliability: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    observations: Mapped[list["Observation"]] = relationship(back_populates="source")


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id: Mapped[str] = mapped_column(
        UUID_TYPE, ForeignKey("sources.id", ondelete="RESTRICT"), index=True
    )
    source_type: Mapped[str] = mapped_column(String(50), default="manual")
    observation_category: Mapped[str] = mapped_column(String(100), default="asset")
    asset_identifiers: Mapped[dict] = mapped_column(JSON_TYPE, default=dict)
    observed_attributes: Mapped[dict] = mapped_column(JSON_TYPE, default=dict)
    observation_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    collection_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    raw_ref: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    processing_status: Mapped[str] = mapped_column(String(30), default="received", index=True)
    quality_flags: Mapped[list] = mapped_column(JSON_TYPE, default=list)
    quality_score: Mapped[float] = mapped_column(Float, default=1.0)
    epistemic_class: Mapped[str] = mapped_column(String(30), default="observed")
    dedup_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    source: Mapped[Source] = relationship(back_populates="observations")


@event.listens_for(Observation, "before_update")
def prevent_observation_update(_mapper, _connection, _target):
    raise ValueError("Observations are immutable")


@event.listens_for(Observation, "before_delete")
def prevent_observation_delete(_mapper, _connection, _target):
    raise ValueError("Observations are immutable")


def observation_hash(
    source_id: str,
    category: str,
    identifiers: dict,
    attributes: dict,
    observation_timestamp: datetime,
) -> str:
    import json

    value = {
        "source_id": source_id,
        "category": category,
        "identifiers": identifiers,
        "attributes": attributes,
        "observation_timestamp": observation_timestamp.astimezone(UTC).isoformat(),
    }
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
