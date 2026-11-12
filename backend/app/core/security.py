from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.core import Role, User, UserRole

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except Exception:
        return False


async def get_user_roles(db: AsyncSession, user: User | str) -> set[str]:
    user_id = user.id if isinstance(user, User) else user
    result = await db.scalars(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    )
    roles = set(result.all())
    if not roles and isinstance(user, User) and user.role:
        roles.add(user.role)
    return roles


async def has_role(db: AsyncSession, user: User | str, role: str) -> bool:
    return role in await get_user_roles(db, user)


async def assign_role(
    db: AsyncSession, user: User, role_name: str, description: str | None = None
) -> Role:
    role = await db.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        role = Role(name=role_name, description=description)
        db.add(role)
        await db.flush()
    assignment = await db.scalar(
        select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
    )
    if assignment is None:
        db.add(UserRole(user_id=user.id, role_id=role.id))
    return role


def create_token(subject: str, *, token_type: str = "access", hours: int = 8) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {"sub": subject, "typ": token_type, "iat": now, "exp": now + timedelta(hours=hours)},
        get_settings().jwt_secret,
        algorithm="HS256",
    )
