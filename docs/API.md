# Deepsight API

OpenAPI is available at `/docs` and `/openapi.json` when the backend is running. Authenticated endpoints use a bearer JWT returned by `POST /api/auth/login`.

Current foundation endpoints include health/readiness/metrics, login, asset listing/creation/detail, findings listing, and dashboard summary.

Authenticated observation endpoints:

- `POST /api/observations` accepts a manual observation, normalizes identifiers,
  computes quality flags/score, and stores an immutable record with a deduplication hash.
- `GET /api/observations` lists observations with optional `source_id`,
  `processing_status`, `limit`, and `offset` filters.
- `POST /api/observations/sources` registers a source for submitted observations.
