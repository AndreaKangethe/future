# Deepsight architecture

Deepsight is a modular monolith: FastAPI exposes versioned APIs, SQLAlchemy persists evidence and history in PostgreSQL/TimescaleDB, Celery handles isolated background work through Redis, and MinIO stores raw payloads and reports. Nginx serves the React SPA and proxies `/api`.

The platform separates observed, normalized, inferred, predicted, and assessed data. The current foundation exposes authenticated assets, findings, dashboard summaries, and health/metrics endpoints; subsequent modules extend the same boundaries for ingestion, identity, intelligence, risk, ML, investigations, and grounded assistant tools.

ASIVM is retained only as the technical designation used by the source design documents.
