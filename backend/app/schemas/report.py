from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReportCreate(BaseModel):
    report_type: str = Field(min_length=1, max_length=50)
    status: str = Field(default="generated", min_length=1, max_length=30)
    scope: dict[str, object] = Field(default_factory=dict)
    generated_at: datetime | None = None
    evidence_sources: list[object] = Field(default_factory=list)
    limitations: str | None = None
    object_ref: str | None = Field(default=None, max_length=1000)


class ReportUpdate(BaseModel):
    report_type: str | None = Field(default=None, min_length=1, max_length=50)
    status: str | None = Field(default=None, min_length=1, max_length=30)
    scope: dict[str, object] | None = None
    generated_at: datetime | None = None
    evidence_sources: list[object] | None = None
    limitations: str | None = None
    object_ref: str | None = Field(default=None, max_length=1000)


class ReportResponse(ReportCreate):
    id: UUID
    generated_at: datetime
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
