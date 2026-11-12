# Deepsight architecture

Deepsight is a modular monolith: FastAPI exposes versioned APIs, SQLAlchemy persists evidence and history in PostgreSQL/TimescaleDB, Celery handles isolated background work through Redis, and MinIO stores raw payloads and reports. Nginx serves the React SPA and proxies `/api`.

The platform separates observed, normalized, inferred, predicted, and assessed data. The current foundation exposes authenticated assets, findings, dashboard summaries, and health/metrics endpoints; subsequent modules extend the same boundaries for ingestion, identity, intelligence, risk, ML, investigations, and grounded assistant tools.

ASIVM is retained only as the technical designation used by the source design documents.

## Intelligence loaders

`app.services.intelligence` provides offline-first loaders for NVD CVEs, the CISA
Known Exploited Vulnerabilities catalog, and MITRE ATT&CK STIX bundles. NVD
requests accept `last_modified`/`end_modified` values and send the corresponding
API 2.0 `lastModStartDate`/`lastModEndDate` parameters. Timeouts, HTTP errors,
and rate-limit exhaustion are represented explicitly in `LoadResult.error`; a
bundled snapshot is returned when available so an unavailable upstream never
prevents the application from starting. Loaders use injected `httpx` clients,
which keeps tests and offline deployments deterministic.
