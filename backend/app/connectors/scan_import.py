"""Best-effort parsers for common scan export formats."""

from __future__ import annotations

import csv
import io
import json
import os
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from typing import Any

from app.connectors.base import Observation, normalize_observation


def parse_nmap_xml(
    payload: str | bytes, *, source_name: str = "nmap", raw_ref: str | None = None
) -> list[Observation]:
    root = ET.fromstring(payload)
    observations: list[Observation] = []
    for host in root.findall(".//host"):
        identifiers: dict[str, Any] = {}
        addresses = host.findall("./address")
        for address in addresses:
            address_type = address.get("addrtype")
            value = address.get("addr")
            if not value:
                continue
            if address_type == "mac":
                identifiers["mac"] = value
            elif address_type in {"ipv4", "ipv6"}:
                identifiers["ip"] = value
            elif address_type:
                identifiers[address_type] = value
        hostname = host.find("./hostnames/hostname")
        if hostname is not None and hostname.get("name"):
            identifiers["hostname"] = hostname.get("name")

        attributes: dict[str, Any] = {}
        status = host.find("./status")
        if status is not None:
            attributes["state"] = status.get("state")
        ports: list[dict[str, Any]] = []
        for port in host.findall("./ports/port"):
            service = port.find("./service")
            item: dict[str, Any] = {
                key: value
                for key, value in (
                    ("port", port.get("portid")),
                    ("protocol", port.get("protocol")),
                    ("state", port.find("./state").get("state") if port.find("./state") is not None else None),
                )
                if value is not None
            }
            if service is not None:
                for key in ("name", "product", "version", "extrainfo"):
                    if service.get(key):
                        item[key] = service.get(key)
            if item:
                ports.append(item)
        if ports:
            attributes["ports"] = ports
        os_match = host.find("./os/osmatch")
        if os_match is not None and os_match.get("name"):
            attributes["os"] = os_match.get("name")
        observations.append(
            normalize_observation(
                {"asset_identifiers": identifiers, "observed_attributes": attributes},
                source_type="nmap",
                source_name=source_name,
                raw_ref=raw_ref,
            )
        )
    return observations


def parse_csv(
    payload: str | bytes, *, source_name: str = "csv", raw_ref: str | None = None
) -> list[Observation]:
    text = _text(payload)
    rows = csv.DictReader(io.StringIO(text))
    return [_row_observation(row, "csv", source_name, raw_ref) for row in rows]


def parse_nessus_csv(
    payload: str | bytes, *, source_name: str = "nessus", raw_ref: str | None = None
) -> list[Observation]:
    text = _text(payload)
    rows = csv.DictReader(io.StringIO(text))
    observations = []
    for row in rows:
        lowered = {_key(key): value for key, value in row.items() if key}
        identifiers = _identifiers(lowered)
        attributes = {
            key: value
            for key, value in row.items()
            if key and value not in (None, "") and _key(key) not in _IDENTIFIER_KEYS
        }
        attributes = {_key(key): value for key, value in attributes.items()}
        attributes["scanner"] = "nessus"
        observations.append(
            normalize_observation(
                {
                    "asset_identifiers": identifiers,
                    "observed_attributes": attributes,
                    "observation_category": "finding",
                    "observation_timestamp": lowered.get("scan_date")
                    or lowered.get("last_seen"),
                },
                source_type="nessus",
                source_name=source_name,
                raw_ref=raw_ref,
            )
        )
    return observations


def parse_json(
    payload: str | bytes | Mapping[str, Any] | list[Any],
    *,
    source_name: str = "json",
    raw_ref: str | None = None,
) -> list[Observation]:
    value = json.loads(_text(payload)) if isinstance(payload, (str, bytes)) else payload
    if isinstance(value, dict):
        value = value.get("observations", value.get("results", [value]))
    if not isinstance(value, list):
        raise TypeError("JSON import must contain an object or array")
    observations = []
    for item in value:
        if not isinstance(item, dict):
            continue
        if "asset_identifiers" in item or "observed_attributes" in item:
            candidate = item
        else:
            identifiers = _identifiers({_key(k): v for k, v in item.items()})
            candidate = {
                "asset_identifiers": identifiers,
                "observed_attributes": {
                    k: v for k, v in item.items() if _key(k) not in _IDENTIFIER_KEYS
                },
            }
        observations.append(
            normalize_observation(candidate, source_type="json", source_name=source_name, raw_ref=raw_ref)
        )
    return observations


def import_scan(
    payload: str | bytes,
    *,
    format: str | None = None,
    source_name: str | None = None,
    filename: str | None = None,
    raw_ref: str | None = None,
) -> list[Observation]:
    """Dispatch an import by explicit format or filename extension."""
    kind = (format or os.path.splitext(filename or "")[1].lstrip(".")).lower()
    if kind in {"xml", "nmap"}:
        return parse_nmap_xml(payload, source_name=source_name or "nmap", raw_ref=raw_ref)
    if kind in {"nessus", "nessus-csv"}:
        return parse_nessus_csv(payload, source_name=source_name or "nessus", raw_ref=raw_ref)
    if kind in {"json", "js"}:
        return parse_json(payload, source_name=source_name or "json", raw_ref=raw_ref)
    if kind in {"csv", "tsv", ""}:
        return parse_csv(payload, source_name=source_name or "csv", raw_ref=raw_ref)
    raise ValueError(f"unsupported scan format: {kind}")


_IDENTIFIER_KEYS = {"ip", "ip_address", "address", "hostname", "host", "fqdn", "mac", "mac_address"}


def _text(payload: str | bytes) -> str:
    return payload.decode("utf-8-sig") if isinstance(payload, bytes) else payload


def _key(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def _identifiers(row: Mapping[str, Any]) -> dict[str, Any]:
    identifiers = {}
    for key, value in row.items():
        normalized_key = _key(key)
        if normalized_key in _IDENTIFIER_KEYS and value not in (None, ""):
            identifiers[normalized_key] = value
    return identifiers


def _row_observation(
    row: dict[str, Any], source_type: str, source_name: str, raw_ref: str | None
) -> Observation:
    lowered = {_key(key): value for key, value in row.items() if key}
    return normalize_observation(
        {
            "asset_identifiers": _identifiers(lowered),
            "observed_attributes": {
                key: value for key, value in lowered.items() if key not in _IDENTIFIER_KEYS
            },
            "observation_timestamp": lowered.get("timestamp") or lowered.get("observed_at"),
        },
        source_type=source_type,
        source_name=source_name,
        raw_ref=raw_ref,
    )


# Descriptive aliases keep the public API convenient for callers that distinguish
# generic formats from source-specific parsers.
parse_generic_csv = parse_csv
parse_generic_json = parse_json
parse_nessus = parse_nessus_csv
