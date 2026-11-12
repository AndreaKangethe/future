"""Common contract and normalization helpers for connectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from app.pipeline.observation import normalize_identifiers, normalize_timestamp

Observation = dict[str, Any]


def normalize_observation(
    observation: dict[str, Any],
    *,
    source_type: str,
    source_name: str | None = None,
    raw_ref: str | None = None,
) -> Observation:
    """Return the stable dictionary shape consumed by the observation pipeline."""
    identifiers = observation.get("asset_identifiers") or {}
    attributes = observation.get("observed_attributes") or {}
    if not isinstance(identifiers, dict) or not isinstance(attributes, dict):
        raise TypeError("asset_identifiers and observed_attributes must be mappings")

    normalized: Observation = {
        "source_type": observation.get("source_type", source_type),
        "observation_category": observation.get("observation_category", "asset"),
        "asset_identifiers": normalize_identifiers(identifiers),
        "observed_attributes": attributes,
        "observation_timestamp": normalize_timestamp(
            _timestamp(observation.get("observation_timestamp"))
        ),
        "raw_ref": observation.get("raw_ref", raw_ref),
        "epistemic_class": observation.get("epistemic_class", "observed"),
    }
    if source_name is not None:
        normalized["source_name"] = source_name
    return normalized


def _timestamp(value: Any) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None
    return None


class Connector(ABC):
    """Minimal read-only connector interface."""

    source_type: str

    @abstractmethod
    def collect(self) -> Iterable[Observation]:
        """Collect normalized observations without mutating the target."""
