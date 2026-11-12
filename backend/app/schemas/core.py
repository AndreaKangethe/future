from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class AssetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    asset_type: str = "unknown"
    criticality: int = Field(default=3, ge=1, le=5)
    environment: str = "production"
    exposure_status: str = "unknown"


class AssetResponse(AssetCreate):
    id: UUID
    lifecycle_state: str
    identity_confidence: float
    epistemic_class: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class FindingResponse(BaseModel):
    id: UUID
    asset_id: UUID
    title: str
    severity: str
    cvss_score: float | None
    contextual_risk: float
    status: str
    epistemic_class: str
    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    id: UUID
    email: str
    role: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RoleAssignment(BaseModel):
    role: str = Field(min_length=1, max_length=50)
