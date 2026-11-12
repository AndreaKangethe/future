from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RelationshipCreate(BaseModel):
    source_asset_id: UUID
    target_asset_id: UUID
    relationship_type: str = Field(min_length=1, max_length=50)
    direction: str = Field(default="directed", min_length=1, max_length=20)
    confidence: float = Field(default=0.5, ge=0, le=1)
    evidence: dict[str, object] = Field(default_factory=dict)
    relationship_metadata: dict[str, object] = Field(default_factory=dict)


class RelationshipUpdate(BaseModel):
    relationship_type: str | None = Field(default=None, min_length=1, max_length=50)
    direction: str | None = Field(default=None, min_length=1, max_length=20)
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence: dict[str, object] | None = None
    relationship_metadata: dict[str, object] | None = None


class RelationshipResponse(RelationshipCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
