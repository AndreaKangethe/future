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

## Inventory connectors

The optional inventory adapters expose `collect()` and return the same
normalized dictionaries. They are read-only by design:

- `DockerConnector` reads containers and images through the Docker Engine API.
- `KubernetesConnector` reads nodes, pods, services, namespaces, and deployments.
- `AWSConnector` reads EC2, VPCs, security groups, RDS, S3 bucket metadata, and ELB metadata.
- `DemoConnector` emits two deterministic synthetic assets without network access.

Each class declares a `capabilities` set and provides `validate_connectivity()`
and `health()`. Docker, Kubernetes, and AWS SDKs are optional dependencies:
constructing a connector without its SDK or required configuration raises a
clear `ConnectorDependencyError` or `ConnectorConfigurationError`. Pass mocked
clients/sessions to constructors in tests. Credentials are never returned by
`health()` or included in observations.
