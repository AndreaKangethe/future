"""Synthetic read-only connector used for demos and local development."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.connectors.base import Connector, Observation, normalize_observation


class DemoConnector(Connector):
    source_type = "demo"
    capabilities = frozenset({"api", "scheduled", "read"})

    def __init__(self, observations: Iterable[dict[str, Any]] | None = None) -> None:
        self._observations = list(observations) if observations is not None else [
            {
                "asset_identifiers": {"hostname": "demo-web-01.example.test", "ip": "192.0.2.10"},
                "observed_attributes": {"role": "web", "environment": "demo"},
            },
            {
                "asset_identifiers": {"hostname": "demo-db-01.example.test", "ip": "192.0.2.20"},
                "observed_attributes": {"role": "database", "environment": "demo"},
            },
        ]

    def validate_connectivity(self) -> None:
        return None

    def collect(self) -> Iterable[Observation]:
        for observation in self._observations:
            yield normalize_observation(observation, source_type=self.source_type, source_name="demo")
