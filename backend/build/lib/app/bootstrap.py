import asyncio
from sqlalchemy import select
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.core import User
from app.core.config import get_settings
from app.core.security import hash_password


async def main():
    import app.models.core
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    settings = get_settings()
    async with SessionLocal() as db:
        existing = await db.scalar(select(User).where(User.email == settings.bootstrap_admin_email.lower()))
        if not existing:
            db.add(User(email=settings.bootstrap_admin_email.lower(), password_hash=hash_password(settings.bootstrap_admin_password), role="admin"))
            await db.commit()


if __name__ == "__main__":
    asyncio.run(main())
