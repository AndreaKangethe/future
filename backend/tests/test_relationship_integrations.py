import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.core import Asset
from app.models.integration import Integration
from app.models.relationship import Relationship
from app.services.integrations import create_integration, update_integration
from app.services.relationships import create_relationship, update_relationship


@pytest.mark.asyncio
async def test_relationship_and_integration_persist_json_in_sqlite():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with sessions() as db:
        source = Asset(name="web-01")
        target = Asset(name="db-01")
        db.add_all([source, target])
        await db.flush()
        relationship = await create_relationship(
            db,
            source_asset_id=source.id,
            target_asset_id=target.id,
            relationship_type="depends_on",
            evidence={"source": "inventory", "port": 5432},
        )
        integration = await create_integration(
            db,
            name="CMDB",
            provider="example-cmdb",
            config={"base_url": "https://cmdb.example.test", "timeout": 10},
            credentials_masked={"token": "********"},
            credentials_encrypted="secret-ref://cmdb-token",
        )
        await update_relationship(db, relationship.id, confidence=0.9)
        await update_integration(db, integration, status="enabled")
        await db.commit()

        stored_relationship = await db.get(Relationship, relationship.id)
        assert stored_relationship.evidence == {"source": "inventory", "port": 5432}
        assert stored_relationship.confidence == 0.9
        stored_integration = await db.get(Integration, integration.id)
        assert stored_integration.config["timeout"] == 10
        assert stored_integration.credentials_masked == {"token": "********"}
        assert stored_integration.credentials_encrypted == "secret-ref://cmdb-token"
        assert "token-value" not in repr(stored_integration)

    await engine.dispose()
