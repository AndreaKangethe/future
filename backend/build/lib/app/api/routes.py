from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from jose import JWTError, jwt
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.config import get_settings
from app.core.security import create_token, verify_password
from app.db.session import get_db
from app.models.core import Asset, Finding, User
from app.schemas.core import AssetCreate, AssetResponse, FindingResponse, LoginRequest, TokenResponse

router = APIRouter(prefix="/api")
bearer = HTTPBearer(auto_error=False)


async def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: AsyncSession = Depends(get_db)):
    if not credentials:
        raise HTTPException(401, "Authentication required")
    try:
        subject = jwt.decode(credentials.credentials, get_settings().jwt_secret, algorithms=["HS256"]).get("sub")
    except JWTError as exc:
        raise HTTPException(401, "Invalid token") from exc
    user = await db.scalar(select(User).where(User.email == subject))
    if not user:
        raise HTTPException(401, "User not found")
    return user


@router.post("/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    return TokenResponse(access_token=create_token(user.email))


@router.get("/assets", response_model=list[AssetResponse])
async def list_assets(_: User = Depends(current_user), db: AsyncSession = Depends(get_db), q: str | None = Query(None)):
    query = select(Asset).order_by(Asset.name).limit(500)
    if q:
        query = query.where(Asset.name.ilike(f"%{q}%"))
    return list((await db.scalars(query)).all())


@router.post("/assets", response_model=AssetResponse)
async def create_asset(payload: AssetCreate, _: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    asset = Asset(**payload.model_dump(), identity_confidence=0.5, epistemic_class="observed")
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


@router.get("/findings", response_model=list[FindingResponse])
async def list_findings(_: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return list((await db.scalars(select(Finding).order_by(Finding.contextual_risk.desc()).limit(500))).all())


@router.get("/dashboard/summary")
async def dashboard_summary(_: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    assets = await db.scalar(select(func.count()).select_from(Asset)) or 0
    findings = await db.scalar(select(func.count()).select_from(Finding).where(Finding.status == "open")) or 0
    critical = await db.scalar(select(func.count()).select_from(Finding).where(Finding.severity == "critical", Finding.status == "open")) or 0
    return {"assets": assets, "open_findings": findings, "critical_findings": critical, "anomalies": 0, "unresolved_identities": 0}


@router.get("/assets/{asset_id}", response_model=AssetResponse)
async def get_asset(asset_id: UUID, _: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    asset = await db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    return asset
