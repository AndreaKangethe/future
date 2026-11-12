import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.security import assign_role, get_user_roles, has_role, hash_password, verify_password
from app.db.base import Base
from app.models.core import User


@pytest.mark.asyncio
async def test_password_helpers_and_role_assignments():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        async with sessions() as db:
            user = User(email="admin@example.com", password_hash=hash_password("correct"))
            db.add(user)
            await db.flush()
            await assign_role(db, user, "admin")
            await db.commit()

            assert verify_password("correct", user.password_hash)
            assert not verify_password("wrong", user.password_hash)
            assert await has_role(db, user, "admin")
            assert await get_user_roles(db, user) == {"admin"}
    finally:
        await engine.dispose()
