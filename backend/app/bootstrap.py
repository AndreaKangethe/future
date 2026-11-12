import asyncio

from sqlalchemy import select

import app.models.audit
import app.models.investigation
import app.models.ml
import app.models.observation
import app.models.report
import app.models.risk_assessment
import app.models.vulnerability  # noqa: F401
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.core import User
from app.models.ml import ModelRegistry
from app.services.vulnerability_intel import load_offline_snapshot


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    settings = get_settings()
    async with SessionLocal() as db:
        await load_offline_snapshot(db)
        if not await db.scalar(
            select(ModelRegistry).where(ModelRegistry.name == "deterministic-anomaly")
        ):
            db.add(
                ModelRegistry(
                    name="deterministic-anomaly",
                    version="1.0.0",
                    model_type="anomaly",
                    status="active",
                    model_metadata={
                        "limitations": "Transparent cold-start baseline; not a trained production model."
                    },
                )
            )
            await db.commit()
        existing = await db.scalar(
            select(User).where(User.email == settings.bootstrap_admin_email.lower())
        )
        if not existing:
            db.add(
                User(
                    email=settings.bootstrap_admin_email.lower(),
                    password_hash=hash_password(settings.bootstrap_admin_password),
                    role="admin",
                )
            )
            await db.commit()


if __name__ == "__main__":
    asyncio.run(main())
