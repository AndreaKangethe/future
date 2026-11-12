import httpx
import pytest

from app.services.intelligence.cisa_kev import CISAKEVLoader
from app.services.intelligence.mitre_attack import MITREAttackLoader
from app.services.intelligence.nvd import NVDClient


@pytest.mark.asyncio
async def test_nvd_sends_incremental_parameters_and_api_key():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200, json={"totalResults": 1, "vulnerabilities": [{"cve": {"id": "CVE-1"}}]}
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    result = await NVDClient(api_key="secret", client=client).fetch(
        last_modified="2026-01-01T00:00:00Z", end_modified="2026-01-02T00:00:00Z"
    )
    await client.aclose()

    assert result.ok
    assert result.records[0]["cve"]["id"] == "CVE-1"
    assert requests[0].url.params["lastModStartDate"] == "2026-01-01T00:00:00Z"
    assert requests[0].url.params["lastModEndDate"] == "2026-01-02T00:00:00Z"
    assert requests[0].headers["apiKey"] == "secret"


@pytest.mark.asyncio
async def test_nvd_rate_limit_retries_then_succeeds():
    attempts = 0
    delays = []

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "0.25"})
        return httpx.Response(200, json={"vulnerabilities": []})

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    result = await NVDClient(client=client, sleep=record_sleep).fetch()
    await client.aclose()

    assert result.ok
    assert attempts == 2
    assert delays == [0.25]


@pytest.mark.asyncio
async def test_loaders_use_fallback_when_network_fails():
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    nvd = await NVDClient(client=client).load()
    kev = await CISAKEVLoader(client=client).load()
    attack = await MITREAttackLoader(client=client).load(
        snapshot_path="backend/app/services/intelligence/missing-attack.json"
    )
    await client.aclose()

    assert nvd.used_fallback and nvd.records
    assert kev.used_fallback and kev.records
    assert attack.used_fallback and attack.records[0]["type"] == "attack-pattern"
