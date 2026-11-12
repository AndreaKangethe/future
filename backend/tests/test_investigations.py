import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.investigation import Investigation
from app.models.report import Report
from app.services.investigations import (
    add_investigation_note,
    add_investigation_timeline,
    create_investigation,
    create_report,
    update_investigation,
    update_report_metadata,
)


@pytest.mark.asyncio
async def test_investigation_notes_timeline_and_report_metadata_persist_in_sqlite():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with sessions() as db:
        investigation = await create_investigation(db, title="Credential exposure")
        note = await add_investigation_note(
            db, investigation.id, body="Validated the affected host."
        )
        event = await add_investigation_timeline(
            db, investigation.id, summary="Evidence validated", details={"confidence": 0.9}
        )
        await update_investigation(db, investigation, status="closed", conclusions="Contained")
        report = await create_report(
            db, report_type="investigation", scope={"investigation_id": investigation.id}
        )
        await update_report_metadata(
            db, report, object_ref="reports/credential-exposure.pdf", status="published"
        )
        await db.commit()

        assert (await db.get(Investigation, investigation.id)).status == "closed"
        assert (await db.get(type(note), note.id)).body == "Validated the affected host."
        assert (await db.get(type(event), event.id)).details == {"confidence": 0.9}
        stored_report = await db.get(Report, report.id)
        assert stored_report.object_ref == "reports/credential-exposure.pdf"
        assert stored_report.status == "published"

    await engine.dispose()
