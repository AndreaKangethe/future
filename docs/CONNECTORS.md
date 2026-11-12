# Connectors

Connectors are read-only adapters that validate connectivity, collect observations, report health, and preserve source metadata. Scan imports and cloud/host adapters belong behind this boundary; no connector may exploit or mutate a target.

## Scan import slice

`app.connectors.scan_import` converts common exports into normalized observation
dictionaries. Each dictionary contains `source_type`, `source_name`,
`observation_category`, `asset_identifiers`, `observed_attributes`,
`observation_timestamp`, `raw_ref`, and `epistemic_class`. Identifiers use the
same canonicalization as the observation pipeline (lowercase hostnames, canonical
IP addresses, and colon-separated MAC addresses).

Supported entry points are:

- `parse_nmap_xml(payload)` — one asset observation per Nmap host, including
  status, operating system, and discovered services.
- `parse_csv(payload)` — generic CSV; common host/IP/MAC columns become
  identifiers and remaining columns become attributes.
- `parse_json(payload)` — an object, an array, or an `observations`/`results`
  array. Explicit `asset_identifiers` and `observed_attributes` are preserved.
- `parse_nessus_csv(payload)` — best-effort Nessus CSV finding observations.
- `import_scan(payload, format=..., filename=...)` — dispatches to a parser.

Parsing is deliberately best-effort: source-specific columns are retained rather
than discarded, and raw payload storage is left to the ingestion service. Parsers
do not make network calls or modify database records.
