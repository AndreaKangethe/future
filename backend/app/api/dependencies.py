from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import current_user
from app.core.security import has_role
from app.db.session import get_db
from app.models.core import User


def require_role(*allowed_roles: str) -> Callable[..., Awaitable[User]]:
    """Build a FastAPI dependency that rejects authenticated users without a role."""
    if not allowed_roles:
        raise ValueError("at least one role is required")

    async def dependency(
        user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
    ) -> User:
        if not any(await has_role(db, user, role) for role in allowed_roles):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return dependency
