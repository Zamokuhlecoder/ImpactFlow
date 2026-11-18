# API documentation

## Phase 2 scope

The API currently provides health/readiness endpoints only. No dashboard metrics, data-source, ingestion, pipeline, authentication, user, warehouse, or governance endpoints are implemented.

With the API running, interactive OpenAPI documentation is available at `/docs`, ReDoc at `/redoc`, and the OpenAPI JSON document at `/openapi.json`. These documentation routes can be disabled with `IMPACTFLOW_DOCS_ENABLED=false`.

## Health checks

### `GET /api/v1/health/live`

Checks that the API process responds. It does not depend on PostgreSQL.

Successful response (`200`):

```json
{"status": "ok"}
```

### `GET /api/v1/health/ready`

Executes `SELECT 1` using the configured SQLAlchemy engine.

Successful response (`200`):

```json
{"status": "ready", "database": "connected"}
```

Not-ready response (`503`), when no database URL is configured:

```json
{"detail": {"status": "not_ready", "database": "not_configured"}}
```

Unavailable response (`503`), when the configured database cannot be reached:

```json
{"detail": {"status": "not_ready", "database": "unavailable"}}
```

Connection details are not included in the error response. The failure is logged by the API process.

## Configuration and CORS

Settings use the `IMPACTFLOW_` environment prefix. The required PostgreSQL connection setting for database-backed operations is `IMPACTFLOW_DATABASE_URL`, using the `postgresql+psycopg` SQLAlchemy URL scheme. `IMPACTFLOW_CORS_ORIGINS` accepts a JSON string array and defaults to the local Vite development origins.

The frontend Axios client remains configured but is not yet wired to these endpoints; dashboard figures remain synthetic.
