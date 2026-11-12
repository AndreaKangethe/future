from collections.abc import Sequence
from math import log
from statistics import mean


def population_stability_index(
    expected: Sequence[float], actual: Sequence[float], bins: int = 10
) -> float:
    if not expected or not actual:
        raise ValueError("Both expected and actual samples are required")
    if bins < 2:
        raise ValueError("At least two bins are required")
    lower = min(min(expected), min(actual))
    upper = max(max(expected), max(actual))
    width = max((upper - lower) / bins, 1e-12)

    def distribution(values: Sequence[float]) -> list[float]:
        counts = [0] * bins
        for value in values:
            index = min(bins - 1, int((value - lower) / width))
            counts[index] += 1
        total = len(values)
        return [max(count / total, 1e-6) for count in counts]

    baseline = distribution(expected)
    current = distribution(actual)
    return round(sum((c - b) * log(c / b) for b, c in zip(baseline, current)), 6)


def drift_summary(expected: Sequence[float], actual: Sequence[float]) -> dict:
    psi = population_stability_index(expected, actual)
    return {
        "psi": psi,
        "mean_expected": round(mean(expected), 6),
        "mean_actual": round(mean(actual), 6),
        "status": "drift" if psi >= 0.2 else "stable",
        "limitations": ["PSI is a screening signal, not proof of model degradation."],
    }
