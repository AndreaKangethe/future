import json
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.fallback import Evidence
from app.assistant.provider import AssistantRequest, DeterministicFallbackProvider
from app.connectors.scan_import import import_scan
from app.core.config import get_settings
from app.core.security import create_token, verify_password
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.core import Asset, Finding, User
from app.models.integration import Integration
from app.models.investigation import Investigation, InvestigationNote, InvestigationTimeline
from app.models.ml import ModelRegistry
from app.models.observation import Observation, Source, observation_hash
from app.models.relationship import Relationship
from app.models.report import Report
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
from app.schemas.integration import IntegrationCreate, IntegrationResponse, IntegrationUpdate
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationNoteCreate,
    InvestigationNoteResponse,
    InvestigationResponse,
    InvestigationTimelineCreate,
    InvestigationTimelineResponse,
    InvestigationUpdate,
)
from app.schemas.observation import (
    ObservationCreate,
    ObservationResponse,
    SourceCreate,
    SourceResponse,
)
from app.schemas.relationship import RelationshipCreate, RelationshipResponse, RelationshipUpdate
from app.schemas.report import ReportCreate, ReportResponse, ReportUpdate
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


class AnomalyRequest(BaseModel):
    features: dict[str, float | int | str | bool]
    baseline: dict[str, dict[str, float]] = {}


class IdentityResolveRequest(BaseModel):
    observation_identifiers: dict[str, object]
    candidate_identifiers: dict[str, object]


async def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer), db: AsyncSession = Depends(get_db)
):
    if not credentials:
        raise HTTPException(401, "Authentication required")
    try:
        claims = jwt.decode(
            credentials.credentials, get_settings().jwt_secret, algorithms=["HS256"]
        )
        if claims.get("typ", "access") != "access":
            raise HTTPException(401, "Access token required")
        subject = claims.get("sub")
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
    return TokenResponse(
        access_token=create_token(user.email),
        refresh_token=create_token(user.email, token_type="refresh", hours=24 * 30),
    )


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        claims = jwt.decode(payload.refresh_token, get_settings().jwt_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(401, "Invalid refresh token") from exc
    if claims.get("typ") != "refresh":
        raise HTTPException(401, "Refresh token required")
    email = claims.get("sub")
    user = await db.scalar(select(User).where(User.email == email))
    if not user:
        raise HTTPException(401, "User not found")
    return TokenResponse(
        access_token=create_token(user.email),
        refresh_token=create_token(user.email, token_type="refresh", hours=24 * 30),
    )


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


@router.get("/ml/models")
async def list_ml_models(_: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return list((await db.scalars(select(ModelRegistry).order_by(ModelRegistry.name))).all())


@router.post("/anomalies/score")
async def score_anomaly(payload: AnomalyRequest, _: User = Depends(current_user)):
    from app.services.anomaly import score_anomaly

    return score_anomaly(payload.features, payload.baseline)


@router.post("/identity/resolve")
async def resolve_identity_endpoint(
    payload: IdentityResolveRequest, _: User = Depends(current_user)
):
    from app.services.identity import resolve_identity

    decision = resolve_identity(
        payload.observation_identifiers,
        payload.candidate_identifiers,
    )
    return {
        "outcome": decision.outcome,
        "score": decision.score,
        "evidence": decision.evidence,
        "reason": decision.reason,
        "epistemic_class": "inferred",
    }


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
    response = await DeterministicFallbackProvider().complete(
        AssistantRequest(question=payload.question, evidence=tuple(evidence))
    )
    return response.as_dict()


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


@router.get("/investigations", response_model=list[InvestigationResponse])
async def list_investigations(_: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return list(
        (await db.scalars(select(Investigation).order_by(Investigation.updated_at.desc()))).all()
    )


@router.post("/investigations", response_model=InvestigationResponse, status_code=201)
async def create_investigation(
    payload: InvestigationCreate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    investigation = Investigation(
        **payload.model_dump(exclude_none=True),
        owner_id=payload.owner_id or str(user.id),
    )
    db.add(investigation)
    await db.commit()
    await db.refresh(investigation)
    return investigation


@router.patch("/investigations/{investigation_id}", response_model=InvestigationResponse)
async def update_investigation(
    investigation_id: UUID,
    payload: InvestigationUpdate,
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    investigation = await db.get(Investigation, str(investigation_id))
    if not investigation:
        raise HTTPException(404, "Investigation not found")
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(investigation, key, str(value) if key == "owner_id" and value else value)
    await db.commit()
    await db.refresh(investigation)
    return investigation


@router.post(
    "/investigations/{investigation_id}/notes",
    response_model=InvestigationNoteResponse,
    status_code=201,
)
async def add_investigation_note(
    investigation_id: UUID,
    payload: InvestigationNoteCreate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await db.get(Investigation, str(investigation_id)):
        raise HTTPException(404, "Investigation not found")
    note = InvestigationNote(
        investigation_id=str(investigation_id),
        author_id=str(payload.author_id or user.id),
        body=payload.body,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


@router.get(
    "/investigations/{investigation_id}/timeline",
    response_model=list[InvestigationTimelineResponse],
)
async def investigation_timeline(
    investigation_id: UUID,
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await db.get(Investigation, str(investigation_id)):
        raise HTTPException(404, "Investigation not found")
    return list(
        (
            await db.scalars(
                select(InvestigationTimeline)
                .where(InvestigationTimeline.investigation_id == str(investigation_id))
                .order_by(InvestigationTimeline.occurred_at)
            )
        ).all()
    )


@router.post(
    "/investigations/{investigation_id}/timeline",
    response_model=InvestigationTimelineResponse,
    status_code=201,
)
async def add_investigation_timeline(
    investigation_id: UUID,
    payload: InvestigationTimelineCreate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await db.get(Investigation, str(investigation_id)):
        raise HTTPException(404, "Investigation not found")
    event = InvestigationTimeline(
        investigation_id=str(investigation_id),
        actor_id=str(payload.actor_id or user.id),
        **payload.model_dump(exclude={"actor_id"}),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.get("/reports", response_model=list[ReportResponse])
async def list_reports(_: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return list((await db.scalars(select(Report).order_by(Report.generated_at.desc()))).all())


@router.post("/reports", response_model=ReportResponse, status_code=201)
async def create_report(
    payload: ReportCreate, _: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    report = Report(**payload.model_dump(exclude_none=True))
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


@router.patch("/reports/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: UUID,
    payload: ReportUpdate,
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await db.get(Report, str(report_id))
    if not report:
        raise HTTPException(404, "Report not found")
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(report, key, value)
    await db.commit()
    await db.refresh(report)
    return report


@router.get("/reports/{report_id}/export")
async def export_report(
    report_id: UUID,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await db.get(Report, str(report_id))
    if not report:
        raise HTTPException(404, "Report not found")
    data = {
        "id": report.id,
        "report_type": report.report_type,
        "status": report.status,
        "scope": report.scope,
        "generated_at": report.generated_at.isoformat(),
        "evidence_sources": report.evidence_sources,
        "limitations": report.limitations,
        "object_ref": report.object_ref,
    }
    if format == "json":
        body = json.dumps(data, indent=2)
        media_type = "application/json"
    else:
        body = "field,value\n" + "\n".join(
            f"{key},{json.dumps(value)}" for key, value in data.items()
        )
        media_type = "text/csv"
    return StreamingResponse(iter([body]), media_type=media_type)


@router.get("/events/stream")
async def events_stream(_: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    assets = list(
        (await db.scalars(select(Asset).order_by(Asset.updated_at.desc()).limit(10))).all()
    )

    async def stream():
        for asset in assets:
            yield f"data: {json.dumps({'type': 'asset_activity', 'asset_id': str(asset.id), 'name': asset.name, 'epistemic_class': asset.epistemic_class})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/relationships", response_model=list[RelationshipResponse])
async def list_relationships(
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    asset_id: UUID | None = None,
):
    query = select(Relationship).order_by(Relationship.confidence.desc()).limit(1000)
    if asset_id:
        query = query.where(
            (Relationship.source_asset_id == str(asset_id))
            | (Relationship.target_asset_id == str(asset_id))
        )
    return list((await db.scalars(query)).all())


@router.post("/relationships", response_model=RelationshipResponse, status_code=201)
async def create_relationship(
    payload: RelationshipCreate,
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    for asset_id in (payload.source_asset_id, payload.target_asset_id):
        if not await db.get(Asset, str(asset_id)):
            raise HTTPException(404, "Relationship asset not found")
    relationship = Relationship(**payload.model_dump())
    relationship.source_asset_id = str(payload.source_asset_id)
    relationship.target_asset_id = str(payload.target_asset_id)
    db.add(relationship)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, "Relationship already exists") from exc
    await db.refresh(relationship)
    return relationship


@router.patch("/relationships/{relationship_id}", response_model=RelationshipResponse)
async def update_relationship(
    relationship_id: UUID,
    payload: RelationshipUpdate,
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    relationship = await db.get(Relationship, str(relationship_id))
    if not relationship:
        raise HTTPException(404, "Relationship not found")
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(relationship, key, value)
    await db.commit()
    await db.refresh(relationship)
    return relationship


@router.get("/integrations", response_model=list[IntegrationResponse])
async def list_integrations(_: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return list((await db.scalars(select(Integration).order_by(Integration.name))).all())


@router.post("/integrations", response_model=IntegrationResponse, status_code=201)
async def create_integration(
    payload: IntegrationCreate,
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump(exclude={"credentials_encrypted"})
    integration = Integration(
        **data,
        credentials_encrypted=None,
    )
    db.add(integration)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, "Integration already exists") from exc
    await db.refresh(integration)
    return integration


@router.patch("/integrations/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_id: UUID,
    payload: IntegrationUpdate,
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    integration = await db.get(Integration, str(integration_id))
    if not integration:
        raise HTTPException(404, "Integration not found")
    values = payload.model_dump(exclude_none=True, exclude={"credentials_encrypted"})
    for key, value in values.items():
        setattr(integration, key, value)
    await db.commit()
    await db.refresh(integration)
    return integration
