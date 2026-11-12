from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from app.services.intelligence.common import IntelligenceLoadError, LoadResult

DEFAULT_CISA_KEV_URL = (
    "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
)
DEFAULT_SNAPSHOT_PATH = Path(__file__).parents[2] / "seed" / "vulnerability_snapshot.json"


class CISAKEVLoader:
    def __init__(
        self,
        *,
        url: str = DEFAULT_CISA_KEV_URL,
        timeout: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.url = url
        self.timeout = timeout
        self.client = client

    async def fetch_records(self) -> list[dict[str, Any]]:
        own_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=self.timeout)
        try:
            try:
                response = await client.get(self.url)
                response.raise_for_status()
                payload = response.json()
            except httpx.TimeoutException as exc:
                raise IntelligenceLoadError("CISA KEV request timed out") from exc
            except (httpx.HTTPError, ValueError) as exc:
                raise IntelligenceLoadError("CISA KEV request failed") from exc
            records = payload.get("vulnerabilities") if isinstance(payload, dict) else None
            if not isinstance(records, list):
                raise IntelligenceLoadError("CISA KEV response has no vulnerabilities list")
            return records
        finally:
            if own_client:
                await client.aclose()

    def fallback_records(self, snapshot_path: str | Path = DEFAULT_SNAPSHOT_PATH) -> list[dict]:
        try:
            payload = json.loads(Path(snapshot_path).read_text())
            return payload.get("kev_entries", [])
        except (OSError, ValueError, TypeError) as exc:
            raise IntelligenceLoadError("CISA KEV fallback snapshot unavailable") from exc

    async def load(self, snapshot_path: str | Path = DEFAULT_SNAPSHOT_PATH) -> LoadResult:
        try:
            return LoadResult("cisa-kev", await self.fetch_records())
        except IntelligenceLoadError as exc:
            try:
                return LoadResult("cisa-kev", self.fallback_records(snapshot_path), True, str(exc))
            except IntelligenceLoadError as fallback_exc:
                return LoadResult("cisa-kev", [], True, f"{exc}; {fallback_exc}")
