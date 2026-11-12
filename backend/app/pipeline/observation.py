import ipaddress
import re
from datetime import UTC, datetime, timedelta

MAC_KEYS = {"mac", "mac_address", "macaddress"}
HOST_KEYS = {"hostname", "host", "fqdn", "domain"}


def normalize_identifier(key: str, value: object) -> object:
    if not isinstance(value, str):
        return value
    value = value.strip()
    key_lower = key.lower()
    if key_lower in MAC_KEYS:
        compact = re.sub(r"[^0-9a-fA-F]", "", value)
        if len(compact) == 12:
            return ":".join(compact[i : i + 2].lower() for i in range(0, 12, 2))
    if key_lower in HOST_KEYS:
        return value.rstrip(".").lower()
    if key_lower in {"ip", "ip_address", "address"}:
        try:
            return str(ipaddress.ip_address(value))
        except ValueError:
            return value
    return value


def normalize_identifiers(identifiers: dict[str, object]) -> dict[str, object]:
    return {key: normalize_identifier(key, value) for key, value in identifiers.items()}


def normalize_timestamp(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def quality_flags(
    identifiers: dict[str, object],
    observed_at: datetime,
    *,
    source_verified: bool = True,
    now: datetime | None = None,
) -> list[str]:
    flags: list[str] = []
    if not identifiers:
        flags.append("missing_identifiers")
    if any(value in (None, "") for value in identifiers.values()):
        flags.append("invalid_values")
    current = now or datetime.now(UTC)
    if observed_at < current - timedelta(days=30):
        flags.append("stale")
    if abs((observed_at - current).total_seconds()) > 86400:
        flags.append("timestamp_skew")
    if not source_verified:
        flags.append("unverified_source")
    return flags


def quality_score(flags: list[str]) -> float:
    return max(0.0, round(1.0 - 0.2 * len(set(flags)), 3))
