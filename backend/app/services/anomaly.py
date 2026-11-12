from collections.abc import Mapping
from numbers import Real
from typing import Any


def score_anomaly(
    features: Mapping[str, Any],
    baseline: Mapping[str, Mapping[str, Real]] | None = None,
    *,
    threshold: float = 3.0,
) -> dict[str, Any]:
    """Score numeric features with a deterministic, baseline-relative z-score.

    This is a transparent foundation, not a trained model. Non-numeric values are
    ignored and each feature's contribution is returned for explainability.
    """
    if threshold <= 0:
        raise ValueError("threshold must be positive")

    factors: list[dict[str, Any]] = []
    for name in sorted(features):
        value = features[name]
        if isinstance(value, bool) or not isinstance(value, Real):
            continue
        stats = (baseline or {}).get(name, {})
        mean = float(stats.get("mean", 0.0))
        standard_deviation = max(abs(float(stats.get("std", 1.0))), 1e-12)
        z_score = abs(float(value) - mean) / standard_deviation
        contribution = round(min(1.0, z_score / threshold), 6)
        factors.append(
            {
                "feature": name,
                "value": float(value),
                "z_score": round(z_score, 6),
                "contribution": contribution,
            }
        )

    score = round(max((factor["contribution"] for factor in factors), default=0.0), 6)
    return {
        "score": score,
        "is_anomaly": score >= 1.0,
        "factors": factors,
        "formula_version": "deterministic-zscore-1",
    }


deterministic_anomaly_score = score_anomaly
