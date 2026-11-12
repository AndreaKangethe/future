from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    source_type: str = Field(default="manual", min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=1000)
    reliability: float = Field(default=0.5, ge=0, le=1)


class SourceResponse(SourceCreate):
    id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ObservationCreate(BaseModel):
    source_id: UUID | None = None
    source_name: str | None = Field(default=None, min_length=1, max_length=255)
    source_type: str = Field(default="manual", min_length=1, max_length=50)
    observation_category: str = Field(default="asset", min_length=1, max_length=100)
    asset_identifiers: dict[str, object] = Field(default_factory=dict)
    observed_attributes: dict[str, object] = Field(default_factory=dict)
    observation_timestamp: datetime | None = None
    raw_ref: str | None = Field(default=None, max_length=1000)
    epistemic_class: str = Field(default="observed", min_length=1, max_length=30)


class ObservationResponse(BaseModel):
    id: UUID
    source_id: UUID
    source_type: str
    observation_category: str
    asset_identifiers: dict[str, object]
    observed_attributes: dict[str, object]
    observation_timestamp: datetime
    collection_timestamp: datetime
    raw_ref: str | None
    processing_status: str
    quality_flags: list[str]
    quality_score: float
    epistemic_class: str
    dedup_hash: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
