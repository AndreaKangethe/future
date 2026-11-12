from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ml import ModelInference, ModelRegistry


async def register_model(
    db: AsyncSession,
    *,
    name: str,
    version: str,
    model_type: str = "anomaly",
    status: str = "active",
    artifact_uri: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ModelRegistry:
    model = ModelRegistry(
        name=name,
        version=version,
        model_type=model_type,
        status=status,
        artifact_uri=artifact_uri,
        model_metadata=metadata or {},
    )
    db.add(model)
    await db.flush()
    return model


async def get_model(db: AsyncSession, model_id: str) -> ModelRegistry | None:
    return await db.get(ModelRegistry, model_id)


async def get_active_model(
    db: AsyncSession, name: str, *, model_type: str = "anomaly"
) -> ModelRegistry | None:
    return await db.scalar(
        select(ModelRegistry)
        .where(
            ModelRegistry.name == name,
            ModelRegistry.model_type == model_type,
            ModelRegistry.status == "active",
        )
        .order_by(ModelRegistry.created_at.desc())
    )


async def list_models(
    db: AsyncSession, *, name: str | None = None, model_type: str | None = None
) -> Sequence[ModelRegistry]:
    query = select(ModelRegistry).order_by(ModelRegistry.name, ModelRegistry.created_at.desc())
    if name is not None:
        query = query.where(ModelRegistry.name == name)
    if model_type is not None:
        query = query.where(ModelRegistry.model_type == model_type)
    return (await db.scalars(query)).all()


async def record_inference(
    db: AsyncSession,
    *,
    model: ModelRegistry | str,
    input_data: dict[str, Any],
    output_data: dict[str, Any],
    score: float | None = None,
    is_anomaly: bool | None = None,
    explanation: dict[str, Any] | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> ModelInference:
    model_id = model.id if isinstance(model, ModelRegistry) else model
    inference = ModelInference(
        model_id=model_id,
        input_data=input_data,
        output_data=output_data,
        score=score,
        is_anomaly=is_anomaly,
        explanation=explanation or {},
        entity_type=entity_type,
        entity_id=entity_id,
    )
    db.add(inference)
    await db.flush()
    return inference
