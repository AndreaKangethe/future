from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import Integration


async def create_integration(db: AsyncSession, **values: Any) -> Integration:
    integration = Integration(**values)
    db.add(integration)
    await db.flush()
    return integration


async def update_integration(
    db: AsyncSession, integration: Integration | str, **values: Any
) -> Integration:
    if isinstance(integration, str):
        integration = await db.scalar(select(Integration).where(Integration.id == integration))
        if integration is None:
            raise ValueError("Integration not found")
    allowed = {
        "name",
        "provider",
        "status",
        "config",
        "credentials_masked",
        "credentials_encrypted",
        "last_sync_at",
    }
    for key, value in values.items():
        if key in allowed:
            setattr(integration, key, value)
    await db.flush()
    return integration
