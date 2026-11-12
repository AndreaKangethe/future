from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.routes import current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.core import User
from app.pipeline.observation import normalize_identifiers, quality_flags


def test_normalizes_identifiers_and_flags_stale_data():
    identifiers = normalize_identifiers(
        {"hostname": " Web-01.EXAMPLE.COM. ", "mac": "AABB.CCDD.EEFF"}
    )
    assert identifiers == {"hostname": "web-01.example.com", "mac": "aa:bb:cc:dd:ee:ff"}
    flags = quality_flags(identifiers, datetime.now(UTC) - timedelta(days=31), source_verified=True)
    assert "stale" in flags


@pytest.mark.asyncio
async def test_manual_observation_submission_and_listing():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_db():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: User(
        email="test@example.com", password_hash="unused"
    )
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/observations",
                json={
                    "source_name": "manual-test",
                    "asset_identifiers": {"hostname": "WEB-01.EXAMPLE.COM."},
                    "observed_attributes": {"port": 443},
                },
            )
            assert response.status_code == 201
            assert response.json()["asset_identifiers"]["hostname"] == "web-01.example.com"
            listed = await client.get("/api/observations")
            assert listed.status_code == 200
            assert len(listed.json()) == 1
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
