# Deepsight decisions

- The repository was absent from the workspace, so the platform is scaffolded in `/root/deepsight`.
- ASIVM source documents were not present; this implementation follows the master build prompt and preserves ASIVM references only in architecture mapping notes.
- PostgreSQL/TimescaleDB is the system of record; Redis is reserved for Celery and cache; MinIO stores object evidence.
- The first runnable slice is a modular monolith with FastAPI, Celery, and a Vite SPA.
- Relationships will use PostgreSQL recursive CTEs rather than a separate graph database.
