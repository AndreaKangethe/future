from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investigation import Investigation, InvestigationNote, InvestigationTimeline
from app.models.report import Report


async def create_investigation(
    db: AsyncSession,
    *,
    title: str,
    owner_id: str | None = None,
    status: str = "open",
    conclusions: str | None = None,
) -> Investigation:
    investigation = Investigation(
        title=title, owner_id=owner_id, status=status, conclusions=conclusions
    )
    db.add(investigation)
    await db.flush()
    return investigation


async def update_investigation(
    db: AsyncSession, investigation: Investigation | str, **values: Any
) -> Investigation:
    if isinstance(investigation, str):
        investigation = await db.scalar(
            select(Investigation).where(Investigation.id == investigation)
        )
        if investigation is None:
            raise ValueError("Investigation not found")
    allowed = {"title", "owner_id", "status", "conclusions"}
    for key, value in values.items():
        if key in allowed:
            setattr(investigation, key, value)
    await db.flush()
    return investigation


async def add_investigation_note(
    db: AsyncSession, investigation_id: str, *, body: str, author_id: str | None = None
) -> InvestigationNote:
    note = InvestigationNote(investigation_id=investigation_id, body=body, author_id=author_id)
    db.add(note)
    await db.flush()
    return note


async def add_investigation_timeline(
    db: AsyncSession,
    investigation_id: str,
    *,
    summary: str,
    event_type: str = "update",
    details: Mapping[str, Any] | None = None,
    actor_id: str | None = None,
) -> InvestigationTimeline:
    event = InvestigationTimeline(
        investigation_id=investigation_id,
        summary=summary,
        event_type=event_type,
        details=dict(details or {}),
        actor_id=actor_id,
    )
    db.add(event)
    await db.flush()
    return event


async def create_report(
    db: AsyncSession,
    *,
    report_type: str,
    scope: Mapping[str, Any] | None = None,
    generated_at: datetime | None = None,
    evidence_sources: list[Any] | None = None,
    limitations: str | None = None,
    object_ref: str | None = None,
    status: str = "generated",
) -> Report:
    report = Report(
        report_type=report_type,
        status=status,
        scope=dict(scope or {}),
        generated_at=generated_at,
        evidence_sources=list(evidence_sources or []),
        limitations=limitations,
        object_ref=object_ref,
    )
    db.add(report)
    await db.flush()
    return report


async def update_report_metadata(db: AsyncSession, report: Report | str, **metadata: Any) -> Report:
    if isinstance(report, str):
        report = await db.scalar(select(Report).where(Report.id == report))
        if report is None:
            raise ValueError("Report not found")
    allowed = {
        "report_type",
        "status",
        "scope",
        "generated_at",
        "evidence_sources",
        "limitations",
        "object_ref",
    }
    for key, value in metadata.items():
        if key in allowed:
            if key == "scope" and value is not None:
                value = dict(value)
            elif key == "evidence_sources" and value is not None:
                value = list(value)
            setattr(report, key, value)
    await db.flush()
    return report


async def update_report(db: AsyncSession, report: Report | str, **metadata: Any) -> Report:
    return await update_report_metadata(db, report, **metadata)
