from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InvestigationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    status: str = Field(default="open", min_length=1, max_length=30)
    owner_id: UUID | None = None
    conclusions: str | None = None


class InvestigationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    status: str | None = Field(default=None, min_length=1, max_length=30)
    owner_id: UUID | None = None
    conclusions: str | None = None


class InvestigationResponse(InvestigationCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class InvestigationNoteCreate(BaseModel):
    body: str = Field(min_length=1)
    author_id: UUID | None = None


class InvestigationNoteResponse(InvestigationNoteCreate):
    id: UUID
    investigation_id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class InvestigationTimelineCreate(BaseModel):
    event_type: str = Field(default="update", min_length=1, max_length=50)
    summary: str = Field(min_length=1, max_length=500)
    details: dict[str, object] = Field(default_factory=dict)
    actor_id: UUID | None = None
    occurred_at: datetime | None = None


class InvestigationTimelineResponse(InvestigationTimelineCreate):
    id: UUID
    investigation_id: UUID
    occurred_at: datetime
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
