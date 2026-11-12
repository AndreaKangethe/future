from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from app.services.intelligence.common import IntelligenceLoadError, LoadResult

DEFAULT_NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
DEFAULT_SNAPSHOT_PATH = Path(__file__).parents[2] / "seed" / "vulnerability_snapshot.json"


def _nvd_datetime(value: datetime | str) -> str:
    if isinstance(value, datetime):
        value = value.isoformat()
    return value.replace("+00:00", "Z")


class NVDClient:
    """Small NVD API 2.0 client with pagination and incremental updates."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_NVD_URL,
        timeout: float = 10.0,
        max_retries: int = 2,
        client: httpx.AsyncClient | None = None,
        sleep: Any = asyncio.sleep,
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = client
        self.sleep = sleep

    async def fetch(
        self,
        *,
        last_modified: datetime | str | None = None,
        end_modified: datetime | str | None = None,
    ) -> LoadResult:
        try:
            records = await self.fetch_records(
                last_modified=last_modified, end_modified=end_modified
            )
            return LoadResult("nvd", records)
        except IntelligenceLoadError as exc:
            return LoadResult("nvd", [], error=str(exc))

    async def fetch_records(
        self,
        *,
        last_modified: datetime | str | None = None,
        end_modified: datetime | str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"startIndex": 0}
        if last_modified is not None:
            params["lastModStartDate"] = _nvd_datetime(last_modified)
        if end_modified is not None:
            params["lastModEndDate"] = _nvd_datetime(end_modified)
        headers = {"apiKey": self.api_key} if self.api_key else {}
        own_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=self.timeout)
        records: list[dict[str, Any]] = []
        try:
            while True:
                payload = await self._request(client, params, headers)
                batch = payload.get("vulnerabilities", [])
                if not isinstance(batch, list):
                    raise IntelligenceLoadError("NVD response has invalid vulnerabilities")
                records.extend(batch)
                total = int(payload.get("totalResults", len(records)))
                if not batch or len(records) >= total:
                    return records
                params["startIndex"] = len(records)
        finally:
            if own_client:
                await client.aclose()

    async def _request(
        self, client: httpx.AsyncClient, params: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        for attempt in range(self.max_retries + 1):
            try:
                response = await client.get(self.base_url, params=params, headers=headers)
            except httpx.TimeoutException as exc:
                if attempt < self.max_retries:
                    continue
                raise IntelligenceLoadError("NVD request timed out") from exc
            except httpx.HTTPError as exc:
                raise IntelligenceLoadError("NVD request failed") from exc
            if response.status_code == 429:
                if attempt >= self.max_retries:
                    raise IntelligenceLoadError("NVD rate limit exhausted")
                retry_after = response.headers.get("Retry-After", "1")
                try:
                    delay = max(0.0, float(retry_after))
                except ValueError:
                    delay = 1.0
                await self.sleep(delay)
                continue
            if response.is_error:
                raise IntelligenceLoadError(f"NVD returned HTTP {response.status_code}")
            try:
                payload = response.json()
            except (ValueError, json.JSONDecodeError) as exc:
                raise IntelligenceLoadError("NVD returned invalid JSON") from exc
            if not isinstance(payload, dict):
                raise IntelligenceLoadError("NVD response must be an object")
            return payload
        raise IntelligenceLoadError("NVD request failed")

    def fallback_records(self, snapshot_path: str | Path = DEFAULT_SNAPSHOT_PATH) -> list[dict]:
        try:
            payload = json.loads(Path(snapshot_path).read_text())
            return [{"cve": item} for item in payload.get("vulnerabilities", [])]
        except (OSError, ValueError, TypeError) as exc:
            raise IntelligenceLoadError("NVD fallback snapshot unavailable") from exc

    async def load(
        self,
        *,
        last_modified: datetime | str | None = None,
        end_modified: datetime | str | None = None,
        snapshot_path: str | Path = DEFAULT_SNAPSHOT_PATH,
    ) -> LoadResult:
        result = await self.fetch(last_modified=last_modified, end_modified=end_modified)
        if result.ok:
            return result
        try:
            return LoadResult("nvd", self.fallback_records(snapshot_path), True, result.error)
        except IntelligenceLoadError as exc:
            return LoadResult("nvd", [], True, f"{result.error}; {exc}")
