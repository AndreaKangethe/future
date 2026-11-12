# DEEPSIGHT

**Machine Learning-Driven Attack Surface Intelligence and Vulnerability Management Platform**  
*See beyond the surface.*

## Quickstart

```bash
cp .env.example .env
docker compose up --build
docker compose --profile demo run --rm seed
```

Open <http://localhost:8080>. The development login is `admin@deepsight.local` / `ChangeMe123!`; change it before any non-demo use.

The backend OpenAPI UI is available at <http://localhost:8000/docs> when using the development override. The system uses PostgreSQL/TimescaleDB, Redis/Celery, MinIO, FastAPI, and React/Vite. See `docs/ARCHITECTURE.md` and `docs/DECISIONS.md`.
