# Deepsight API

OpenAPI is available at `/docs` and `/openapi.json` when the backend is running. Authenticated endpoints use a bearer JWT returned by `POST /api/auth/login`.

Implemented endpoint groups include health/readiness/metrics, login, asset listing/creation/detail, findings listing, dashboard summary, source and observation ingestion/listing, scan import, vulnerabilities and KEV, risk assessment preview/history, anomaly scoring, ML model listing, audit log, assistant fallback queries, investigations with notes/timeline, and report metadata CRUD.

Report metadata can also be rendered by the backend report service as JSON or
CSV (`app.services.reports.render_report_json` and
`render_report_csv`). PDF rendering is optional: when the `reportlab`
dependency is unavailable, `render_report_pdf` raises an explicit
`ReportPdfUnsupportedError` instead of returning a placeholder document.

Authenticated observation endpoints:

- `POST /api/observations` accepts a manual observation, normalizes identifiers,
  computes quality flags/score, and stores an immutable record with a deduplication hash.
- `GET /api/observations` lists observations with optional `source_id`,
  `processing_status`, `limit`, and `offset` filters.
- `POST /api/observations/sources` registers a source for submitted observations.
