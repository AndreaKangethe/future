import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.ml import ModelInference, ModelRegistry
from app.services.anomaly import score_anomaly
from app.services.model_registry import (
    get_active_model,
    list_models,
    record_inference,
    register_model,
)


def test_anomaly_score_is_deterministic_and_explainable():
    features = {"z": 0, "normal": 10, "ignored": "not numeric", "flag": True}
    baseline = {"normal": {"mean": 10, "std": 2}, "z": {"mean": 0, "std": 1}}
    result = score_anomaly(features, baseline)

    assert result == score_anomaly(features, baseline)
    assert result["score"] == 0
    assert result["is_anomaly"] is False
    assert [factor["feature"] for factor in result["factors"]] == ["normal", "z"]


def test_anomaly_score_is_bounded_and_flags_outlier():
    result = score_anomaly({"latency": 100}, {"latency": {"mean": 10, "std": 2}})

    assert result["score"] == 1.0
    assert result["is_anomaly"] is True
    assert result["factors"][0]["z_score"] == 45.0


@pytest.mark.asyncio
async def test_model_registry_and_inference_are_persistable():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with sessions() as db:
        model = await register_model(db, name="baseline-anomaly", version="1")
        inference = await record_inference(
            db,
            model=model,
            input_data={"latency": 100},
            output_data={"score": 1.0},
            score=1.0,
            is_anomaly=True,
            explanation={"formula_version": "deterministic-zscore-1"},
        )
        await db.commit()
        active = await get_active_model(db, "baseline-anomaly")
        models = await list_models(db)

        assert active is not None
        assert active.id == model.id
        assert len(models) == 1
        assert await db.get(ModelRegistry, model.id) is not None
        assert await db.get(ModelInference, inference.id) is not None

    await engine.dispose()
