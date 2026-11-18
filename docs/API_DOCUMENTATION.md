# API documentation

## Current scope

The API provides metadata, dashboard aggregates, CSV, XLSX, XLS and JSON file imports, and configured REST/PostgreSQL connectors. Overview defaults to API data; browser-only CSV and public World Bank context are also available. The older CSV job worker remains separate. General-purpose pipeline execution is not implemented.

The programme model stores aggregate reach counts, not individual beneficiaries. Use synthetic data only.

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

Not-ready and unavailable database states return `503`. Connection details are not included in the response.

## Access

The API does not enforce authentication or authorization, and sign-in endpoints are not mounted. Anyone who can reach it can read, modify and delete database records and upload files. Use synthetic data only and keep the service on a trusted local machine; do not expose it to a network or deploy it to production. Existing accounts are preserved but cannot be used to sign in.

## Business and dashboard routes

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/v1/dashboard/summary` | Aggregate KPI counts |
| `GET` | `/api/v1/dashboard/snapshot?days=30` | Overview metrics, trends, reach, and recent operational metadata |
| `GET` | `/api/v1/dashboard/programme-performance` | Active programme reach versus target |
| `GET` | `/api/v1/dashboard/provincial-reach` | Aggregate active-programme reach by province |
| `GET`, `POST` | `/api/v1/organisations`, `/api/v1/locations`, `/api/v1/datasets` | List/create metadata |
| `PATCH`, `DELETE` | `/api/v1/organisations/{id}`, `/api/v1/locations/{id}`, `/api/v1/datasets/{id}` | Update/delete metadata |
| `GET`, `POST` | `/api/v1/programmes` | List/create aggregate programme records |
| `PATCH`, `DELETE` | `/api/v1/programmes/{id}` | Update/delete a programme |
| `GET`, `POST` | `/api/v1/data-sources` | List/create source metadata |
| `PATCH`, `DELETE` | `/api/v1/data-sources/{id}` | Update/delete source metadata |
| `GET`, `POST` | `/api/v1/pipeline-runs` | List/record run metadata; does not execute pipelines |
| `GET`, `POST` | `/api/v1/data-quality/snapshots` | List/record quality scores |
| `GET`, `POST` | `/api/v1/ingestion-records` | List/record ingestion metadata; does not ingest data |
| `POST` | `/api/v1/ingestions/csv` | Validate and enqueue an aggregate programme CSV |
| `GET` | `/api/v1/ingestions/jobs` | List ingestion job statuses |
| `GET` | `/api/v1/ingestions/jobs/{job_id}` | Read one ingestion job status |
| `POST` | `/api/v1/imports/files` | Synchronously validate and import a CSV, XLSX, XLS or JSON file |
| `GET` | `/api/v1/imports` | List import history; filter by `source_type`, `import_status`, `from_date`, `to_date` |
| `GET` | `/api/v1/imports/connections` | List configured reference names and types, never URLs or credentials |
| `POST` | `/api/v1/imports/connections` | Import from a registered configured REST or PostgreSQL source |

Collection endpoints support `limit` (1–100, default 50) and `offset` (default 0). Invalid payloads return `422` and duplicate resource names return `409`.

Organisations have a unique `name`. Locations have a South African `province` and optional `district` and `area`. Datasets have a unique `name` and optional `description` and `source_id`; the referenced data source must exist. Deleting a source unlinks its datasets.

### CSV aggregate job

Upload as `multipart/form-data` with a `source_id` field and a `.csv` file. The source must be active and have type `CSV`. Required columns are `name`, `category`, `province`, `target_beneficiaries`, and `reached_beneficiaries`; optional column: `status`. Files are limited to 2 MB and 2,000 rows. Other columns are rejected. The `202 Accepted` response includes a job ID; poll the job routes until `succeeded` or `failed`. Run the worker separately with `python -m app.worker` and the same database configuration as the API. Successful jobs create/update aggregate programme rows and record pipeline/ingestion metadata. This worker does not call arbitrary external systems.

### Shared file imports

Submit `source_id`, `dataset_name`, `schema_type` (`aggregate` or `participation`) and `file` as multipart form data. Source type must match the file extension: `CSV`/`.csv`, `Excel`/`.xlsx` or `.xls`, or `JSON`/`.json`. JSON must be an array of objects. Participation columns are `beneficiary_id` (synthetic IDs such as `B001`), `programme`, `province`, and `participation_date`. Aggregate columns match the CSV job above. Column names may use spaces and capitalization, for example `Beneficiary ID`. Files are limited to 2 MB and 2,000 rows; unsupported columns are rejected. XLSX formulas are rejected; legacy XLS is read as cached values without executing formulas. Originals are stored locally under `IMPACTFLOW_BRONZE_DIR`; participation records are not inserted into beneficiary tables. Validation failures return `422` and appear in history. Do not upload personal data.

### Configured connections

Configure named connection references using `IMPACTFLOW_SOURCE_CONNECTIONS` in the server environment as described in the backend README. Register a data source with a matching `source_type` and `connection_ref`, then POST JSON containing `source_id`, `dataset_name`, and `schema_type` to `/api/v1/imports/connections`. REST sources must return an uncompressed JSON array; redirects are not followed. PostgreSQL sources read a configured table or view in a read-only transaction. A successful REST import preserves the exact response bytes; a PostgreSQL import preserves a JSON snapshot, not an original file. Both use the same schema and size limits as file imports. Connection failures return `502` and are recorded in history without credentials.

## Database configuration and migrations

Settings use the `IMPACTFLOW_` environment prefix. Set `IMPACTFLOW_DATABASE_URL` in an uncommitted `.env` file. Standard Neon `postgresql://` URLs (including `sslmode=require`) are normalized to Psycopg 3.

Apply the schema with `python -m alembic upgrade head`. Revision `0001_phase2_domain_schema` creates users, programmes, sources, pipeline runs, quality snapshots, and ingestion records; `0002_database_ingestion_jobs` adds the CSV queue; `0003_phase2_metadata_tables` adds organisations, locations, and datasets. Never run `alembic downgrade` on a shared database without an explicit backup and approval.

`python -m app.cli seed-demo` inserts synthetic fixtures only when all business tables are empty; it will not overwrite existing data.

`IMPACTFLOW_CORS_ORIGINS` accepts a JSON string array and defaults to the local Vite development origins. CORS is not an access-control mechanism. Unfinished modules remain labeled previews.
