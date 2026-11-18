# ImpactFlow API

Phase 2 provides the FastAPI/PostgreSQL foundation: environment-backed configuration, SQLAlchemy engine and session infrastructure, Alembic migration scaffolding, API health endpoints, and tests. No application data models, authentication, or dashboard API have been implemented in this phase.

## Requirements

- Python 3.12 or newer.
- Docker Desktop with Compose, or a separately managed PostgreSQL 17 instance.

## Local setup (PowerShell)

From the repository root, copy `.env.example` to `.env`. Set a local development password in `POSTGRES_PASSWORD`, then update `IMPACTFLOW_DATABASE_URL` with the same credentials. URL-encode special characters in the password.

Start PostgreSQL with Docker Compose:

```powershell
docker compose up -d db
```

Install and run the API from the `backend` directory:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

If `py -3.12` is unavailable, use another Python 3.12+ interpreter to create the virtual environment. The API reads `IMPACTFLOW_DATABASE_URL` from the repository-root `.env` file.

OpenAPI UI: `http://127.0.0.1:8000/docs`

## Health endpoints

- `GET /api/v1/health/live` checks only whether the API process responds.
- `GET /api/v1/health/ready` runs `SELECT 1` against PostgreSQL and returns `503` when no database is configured or the connection is unavailable.

## Tests and lint

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check .
```

The tests use SQLite in memory for the successful database-readiness path and do not require Docker or PostgreSQL. They also verify missing and unavailable database states and configured frontend CORS.

Alembic is configured for later schema migrations. Phase 2 defines no business tables; add migrations with the data model in the phase that introduces it.
