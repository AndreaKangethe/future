import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.core import UUID_TYPE

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id: Mapped[str] = mapped_column(UUID_TYPE, index=True)
    contextual_score: Mapped[float] = mapped_column(Float)
    level: Mapped[str] = mapped_column(String(30))
    contributing_factors: Mapped[list] = mapped_column(JSON_TYPE, default=list)
    confidence: Mapped[float] = mapped_column(Float)
    assessment_version: Mapped[str] = mapped_column(String(50), default="baseline-1")
    epistemic_class: Mapped[str] = mapped_column(String(30), default="assessed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    recommended_context: Mapped[str | None] = mapped_column(Text, nullable=True)
