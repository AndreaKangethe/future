from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from app.services.intelligence.common import IntelligenceLoadError, LoadResult

DEFAULT_MITRE_URL = (
    "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/"
    "enterprise-attack/enterprise-attack.json"
)
DEFAULT_SNAPSHOT_PATH = Path(__file__).parents[2] / "seed" / "attack_snapshot.json"
FALLBACK_TECHNIQUES = [
    {
        "type": "attack-pattern",
        "id": "attack-pattern--fallback",
        "name": "Fallback technique",
        "external_references": [{"source_name": "mitre-attack", "external_id": "T0000"}],
    }
]


class MITREAttackLoader:
    """Load ATT&CK STIX bundles without requiring the optional stix2 package."""

    def __init__(
        self,
        *,
        url: str = DEFAULT_MITRE_URL,
        timeout: float = 15.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.url = url
        self.timeout = timeout
        self.client = client

    @staticmethod
    def records_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
        objects = payload.get("objects") if isinstance(payload, dict) else None
        if not isinstance(objects, list):
            raise IntelligenceLoadError("ATT&CK payload has no STIX objects list")
        return [
            item
            for item in objects
            if isinstance(item, dict) and item.get("type") == "attack-pattern"
        ]

    async def fetch_records(self) -> list[dict[str, Any]]:
        own_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=self.timeout)
        try:
            try:
                response = await client.get(self.url)
                response.raise_for_status()
                return self.records_from_payload(response.json())
            except httpx.TimeoutException as exc:
                raise IntelligenceLoadError("MITRE ATT&CK request timed out") from exc
            except (httpx.HTTPError, ValueError) as exc:
                raise IntelligenceLoadError("MITRE ATT&CK request failed") from exc
        finally:
            if own_client:
                await client.aclose()

    def fallback_records(self, snapshot_path: str | Path = DEFAULT_SNAPSHOT_PATH) -> list[dict]:
        try:
            path = Path(snapshot_path)
            if path.exists():
                return self.records_from_payload(json.loads(path.read_text()))
            return FALLBACK_TECHNIQUES.copy()
        except (OSError, ValueError, TypeError) as exc:
            raise IntelligenceLoadError("MITRE ATT&CK fallback snapshot is invalid") from exc

    async def load(self, snapshot_path: str | Path = DEFAULT_SNAPSHOT_PATH) -> LoadResult:
        try:
            return LoadResult("mitre-attack", await self.fetch_records())
        except IntelligenceLoadError as exc:
            try:
                return LoadResult(
                    "mitre-attack", self.fallback_records(snapshot_path), True, str(exc)
                )
            except IntelligenceLoadError as fallback_exc:
                return LoadResult("mitre-attack", [], True, f"{exc}; {fallback_exc}")
