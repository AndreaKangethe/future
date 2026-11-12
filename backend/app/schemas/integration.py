from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IntegrationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    provider: str = Field(min_length=1, max_length=100)
    status: str = Field(default="disabled", min_length=1, max_length=30)
    config: dict[str, object] = Field(default_factory=dict)
    credentials_masked: dict[str, object] | None = None
    credentials_encrypted: str | None = None


class IntegrationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    provider: str | None = Field(default=None, min_length=1, max_length=100)
    status: str | None = Field(default=None, min_length=1, max_length=30)
    config: dict[str, object] | None = None
    credentials_masked: dict[str, object] | None = None
    credentials_encrypted: str | None = None


class IntegrationResponse(IntegrationCreate):
    id: UUID
    last_sync_at: datetime | None
    created_at: datetime
    updated_at: datetime
    credentials_encrypted: None = None
    model_config = ConfigDict(from_attributes=True)
