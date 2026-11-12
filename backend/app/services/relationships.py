from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.relationship import Relationship


async def create_relationship(db: AsyncSession, **values: Any) -> Relationship:
    relationship = Relationship(**values)
    db.add(relationship)
    await db.flush()
    return relationship


async def update_relationship(
    db: AsyncSession, relationship: Relationship | str, **values: Any
) -> Relationship:
    if isinstance(relationship, str):
        relationship = await db.scalar(select(Relationship).where(Relationship.id == relationship))
        if relationship is None:
            raise ValueError("Relationship not found")
    allowed = {
        "relationship_type",
        "direction",
        "confidence",
        "evidence",
        "relationship_metadata",
    }
    for key, value in values.items():
        if key in allowed:
            setattr(relationship, key, value)
    await db.flush()
    return relationship
