from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.fallback import Evidence, summarize
from app.connectors.scan_import import import_scan
from app.core.config import get_settings
from app.core.security import create_token, verify_password
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.core import Asset, Finding, User
from app.models.observation import Observation, Source, observation_hash
from app.models.risk_assessment import RiskAssessment
from app.models.vulnerability import KEVEntry, Vulnerability
from app.pipeline.observation import (
    normalize_identifiers,
    normalize_timestamp,
    quality_flags,
    quality_score,
)
from app.schemas.core import (
    AssetCreate,
    AssetResponse,
    FindingResponse,
    LoginRequest,
    TokenResponse,
)
from app.schemas.observation import (
    ObservationCreate,
    ObservationResponse,
    SourceCreate,
    SourceResponse,
)
from app.schemas.vulnerability import KEVEntryResponse, VulnerabilityResponse

router = APIRouter(prefix="/api")
bearer = HTTPBearer(auto_error=False)


class AssistantQuery(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    asset_id: UUID | None = None


class RiskQuery(BaseModel):
    cvss: float | None = Field(default=None, ge=0, le=10)
    externally_exposed: bool = False
    exploited: bool = False
    evidence_confidence: float = Field(default=0.8, ge=0, le=1)


class ScanImportRequest(BaseModel):
    content: str = Field(min_length=1)
    format: str | None = None
    filename: str | None = None
    source_name: str = "scan-import"


async def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer), db: AsyncSession = Depends(get_db)
):
    if not credentials:
        raise HTTPException(401, "Authentication required")
    try:
        subject = jwt.decode(
            credentials.credentials, get_settings().jwt_secret, algorithms=["HS256"]
        ).get("sub")
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


@router.post("/observations/sources", response_model=SourceResponse)
async def create_source(
    payload: SourceCreate, _: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    source = Source(**payload.model_dump())
    db.add(source)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, "Source already exists") from exc
    await db.refresh(source)
    return source


@router.post("/observations", response_model=ObservationResponse, status_code=201)
async def submit_observation(
    payload: ObservationCreate,
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.source_id:
        source = await db.get(Source, str(payload.source_id))
        if not source:
            raise HTTPException(404, "Source not found")
    else:
        source_name = payload.source_name or "manual"
        source = await db.scalar(select(Source).where(Source.name == source_name))
        if not source:
            source = Source(name=source_name, source_type=payload.source_type, reliability=0.5)
            db.add(source)
            await db.flush()

    observed_at = normalize_timestamp(payload.observation_timestamp)
    identifiers = normalize_identifiers(payload.asset_identifiers)
    flags = quality_flags(
        identifiers,
        observed_at,
        source_verified=source.reliability > 0,
    )
    digest = observation_hash(
        str(source.id),
        payload.observation_category,
        identifiers,
        payload.observed_attributes,
        observed_at,
    )
    observation = Observation(
        source_id=str(source.id),
        source_type=source.source_type,
        observation_category=payload.observation_category,
        asset_identifiers=identifiers,
        observed_attributes=payload.observed_attributes,
        observation_timestamp=observed_at,
        collection_timestamp=datetime.now(UTC),
        raw_ref=payload.raw_ref,
        processing_status="validated",
        quality_flags=flags,
        quality_score=quality_score(flags),
        epistemic_class=payload.epistemic_class,
        dedup_hash=digest,
    )
    db.add(observation)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, "Duplicate observation") from exc
    await db.refresh(observation)
    return observation


@router.get("/observations", response_model=list[ObservationResponse])
async def list_observations(
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    source_id: str | None = Query(None),
    processing_status: str | None = Query(None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    query = select(Observation).order_by(Observation.observation_timestamp.desc())
    if source_id:
        query = query.where(Observation.source_id == source_id)
    if processing_status:
        query = query.where(Observation.processing_status == processing_status)
    return list((await db.scalars(query.offset(offset).limit(limit))).all())


@router.post("/observations/import")
async def import_observations(
    payload: ScanImportRequest,
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        imported = import_scan(
            payload.content,
            format=payload.format,
            filename=payload.filename,
            source_name=payload.source_name,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    source = await db.scalar(select(Source).where(Source.name == payload.source_name))
    if not source:
        source = Source(name=payload.source_name, source_type="scan", reliability=0.7)
        db.add(source)
        await db.flush()
    created = 0
    for item in imported:
        observed_at = normalize_timestamp(item["observation_timestamp"])
        identifiers = item["asset_identifiers"]
        flags = quality_flags(identifiers, observed_at, source_verified=True)
        observation = Observation(
            source_id=str(source.id),
            source_type=item["source_type"],
            observation_category=item["observation_category"],
            asset_identifiers=identifiers,
            observed_attributes=item["observed_attributes"],
            observation_timestamp=observed_at,
            collection_timestamp=datetime.now(UTC),
            raw_ref=item.get("raw_ref"),
            processing_status="validated",
            quality_flags=flags,
            quality_score=quality_score(flags),
            epistemic_class=item["epistemic_class"],
            dedup_hash=observation_hash(
                str(source.id),
                item["observation_category"],
                identifiers,
                item["observed_attributes"],
                observed_at,
            ),
        )
        db.add(observation)
        created += 1
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, "One or more imported observations already exist") from exc
    return {"imported": created, "format": payload.format or payload.filename or "csv"}


@router.get("/assets", response_model=list[AssetResponse])
async def list_assets(
    _: User = Depends(current_user), db: AsyncSession = Depends(get_db), q: str | None = Query(None)
):
    query = select(Asset).order_by(Asset.name).limit(500)
    if q:
        query = query.where(Asset.name.ilike(f"%{q}%"))
    return list((await db.scalars(query)).all())


@router.post("/assets", response_model=AssetResponse)
async def create_asset(
    payload: AssetCreate, _: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    asset = Asset(**payload.model_dump(), identity_confidence=0.5, epistemic_class="observed")
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    db.add(
        AuditLog(
            user_id=str(_.id),
            action="create",
            resource_type="asset",
            resource_id=str(asset.id),
            after=payload.model_dump(),
        )
    )
    await db.commit()
    return asset


@router.get("/findings", response_model=list[FindingResponse])
async def list_findings(_: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return list(
        (
            await db.scalars(select(Finding).order_by(Finding.contextual_risk.desc()).limit(500))
        ).all()
    )


@router.get("/vulnerabilities", response_model=list[VulnerabilityResponse])
async def list_vulnerabilities(
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(None),
    kev_only: bool = False,
):
    query = select(Vulnerability).order_by(Vulnerability.cvss_score.desc()).limit(500)
    if q:
        query = query.where(
            Vulnerability.cve_id.ilike(f"%{q}%")
            | Vulnerability.product.ilike(f"%{q}%")
            | Vulnerability.description.ilike(f"%{q}%")
        )
    if kev_only:
        query = query.join(KEVEntry)
    return list((await db.scalars(query)).all())


@router.get("/intelligence/kev", response_model=list[KEVEntryResponse])
async def list_kev(
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    return list((await db.scalars(select(KEVEntry).order_by(KEVEntry.due_date))).all())


@router.post("/assistant/query")
async def assistant_query(
    payload: AssistantQuery,
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Asset).order_by(Asset.updated_at.desc()).limit(5)
    if payload.asset_id:
        query = query.where(Asset.id == str(payload.asset_id))
    assets = list((await db.scalars(query)).all())
    evidence = [
        Evidence(
            record_type="asset",
            record_id=str(asset.id),
            statement=f"{asset.name} is a {asset.asset_type} with {asset.exposure_status} exposure.",
            epistemic_class=asset.epistemic_class,
        )
        for asset in assets
    ]
    return summarize(payload.question, evidence)


@router.post("/risk-assessments/preview")
async def preview_risk(
    payload: RiskQuery,
    asset_id: UUID,
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.risk import baseline_risk

    asset = await db.get(Asset, str(asset_id))
    if not asset:
        raise HTTPException(404, "Asset not found")
    return baseline_risk(
        criticality=asset.criticality,
        cvss=payload.cvss,
        externally_exposed=payload.externally_exposed,
        exploited=payload.exploited,
        evidence_confidence=payload.evidence_confidence,
    )


@router.post("/assets/{asset_id}/risk-assessments")
async def create_risk_assessment(
    payload: RiskQuery,
    asset_id: UUID,
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.risk import baseline_risk

    asset = await db.get(Asset, str(asset_id))
    if not asset:
        raise HTTPException(404, "Asset not found")
    result = baseline_risk(
        criticality=asset.criticality,
        cvss=payload.cvss,
        externally_exposed=payload.externally_exposed,
        exploited=payload.exploited,
        evidence_confidence=payload.evidence_confidence,
    )
    assessment = RiskAssessment(
        asset_id=str(asset.id),
        contextual_score=result["contextual_score"],
        level=result["level"],
        contributing_factors=result["factors"],
        confidence=result["confidence"],
        assessment_version=result["formula_version"],
        recommended_context="Review evidence links before remediation.",
    )
    db.add(assessment)
    await db.commit()
    await db.refresh(assessment)
    return {
        "id": assessment.id,
        "asset_id": assessment.asset_id,
        **result,
        "epistemic_class": assessment.epistemic_class,
        "created_at": assessment.created_at,
    }


@router.get("/assets/{asset_id}/risk-assessments")
async def list_risk_assessments(
    asset_id: UUID,
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    return list(
        (
            await db.scalars(
                select(RiskAssessment)
                .where(RiskAssessment.asset_id == str(asset_id))
                .order_by(RiskAssessment.created_at.desc())
            )
        ).all()
    )


@router.get("/dashboard/summary")
async def dashboard_summary(_: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    assets = await db.scalar(select(func.count()).select_from(Asset)) or 0
    findings = (
        await db.scalar(select(func.count()).select_from(Finding).where(Finding.status == "open"))
        or 0
    )
    critical = (
        await db.scalar(
            select(func.count())
            .select_from(Finding)
            .where(Finding.severity == "critical", Finding.status == "open")
        )
        or 0
    )
    return {
        "assets": assets,
        "open_findings": findings,
        "critical_findings": critical,
        "anomalies": 0,
        "unresolved_identities": 0,
    }


@router.get("/assets/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: UUID, _: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    asset = await db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    return asset


@router.get("/audit")
async def list_audit(
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
):
    return list(
        (await db.scalars(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit))).all()
    )
