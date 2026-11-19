# ImpactFlow API

Phase 4 builds on Phase 3 source registration, CSV, XLSX, XLS and JSON file imports, and configured REST and PostgreSQL sources. Original files and REST responses are stored in Bronze; PostgreSQL extracts are stored as JSON snapshots. The Pandas processing pipeline standardises and validates records, writes Silver and Gold JSON files, quarantines invalid/duplicate records, and stores quality reports and transformation history in PostgreSQL. The ETL Processing page reads these real API results. Overview defaults to database-backed data; the browser-only CSV and public World Bank context are also available. Other module views remain previews.

**No authentication or authorization is enforced.** Anyone who can reach the API can read, modify and delete shared data and upload files. Run only on a trusted local machine with synthetic data; do not expose this service to a network or deploy it to production. Existing account records are preserved but cannot be used to sign in.

Imports validate programme aggregates, synthetic participation records, or accept general-purpose rows for later ETL validation. Aggregate imports create or update programmes by name; participation rows are preserved in Bronze but not inserted into beneficiary tables. Use synthetic data only: validation cannot establish whether a file contains personal information.

Imports and the initial ETL pipeline run synchronously and are limited to 2 MB and 2,000 rows. Bronze, Silver, Gold and quarantine data are stored under `.impactflow/{bronze,silver,gold,quarantine}` by default, with each layer configurable through its matching `IMPACTFLOW_*_DIR` setting. This is local development storage, not a backup or shared object store; protect the directories and back them up separately. Failed intake validation is recorded in import history and, when within the size limit, the original is retained for ETL processing. The API does not expose raw file downloads. An interrupted API process can leave an import or transformation marked running and requires manual investigation. Enforce request-body limits at the reverse proxy before deploying, because multipart parsing occurs before the file size check. Existing worker-based CSV jobs remain separate and do not appear in the new import history.

The built-in `standardize_validate` pipeline cleans headers and category casing, converts dates and numeric fields, validates South African provinces, participation IDs/programme references, and age/count ranges, detects duplicates, and quarantines rejected rows with record-level reasons. It produces programme performance, provincial performance, and aggregate beneficiary summary Gold datasets where input fields allow. It does not enrich from external datasets, schedule jobs, or build a warehouse; PySpark, dbt and Airflow are not used in this phase.

### Configure external sources

Set `IMPACTFLOW_SOURCE_CONNECTIONS` in the private root `.env` to a JSON object of named connections, then restart the API. For example (replace all placeholders; never commit credentials):

```text
IMPACTFLOW_SOURCE_CONNECTIONS='{"example-api":{"kind":"rest","url":"https://example.org/programmes.json"},"example-db":{"kind":"postgresql","url":"postgresql://readonly:<password>@<host>/<database>?sslmode=require","schema_name":"public","table":"programme_import"}}'
```

In Data Sources, choose REST API or PostgreSQL and select the configured reference. Then use **Import from a connection** in Data Ingestion. The browser receives only reference names and types, not URLs or passwords. REST must return a JSON array of records in one of the supported schemas; redirects and compressed responses are rejected. PostgreSQL reads one configured table or view using a read-only transaction and a 15-second statement timeout. Use a dedicated database role with `SELECT` permission only on the intended table/view; transaction read-only is not a substitute for restricted credentials. The connection must have access to the configured endpoint and return at most 2,000 rows / 2 MB.

Only configure synthetic sources and destinations you trust. Because there is no authentication, anyone who can reach the API can trigger any configured connector and read its imported data. Do not configure sensitive endpoints or credentials in an exposed application.

## Requirements

- Python 3.12 or newer.
- Docker Desktop with Compose, or a separately managed PostgreSQL 17 instance.

## Local setup (PowerShell)

From the repository root, copy `.env.example` to `.env`. Set a local development password in `POSTGRES_PASSWORD`, then update `IMPACTFLOW_DATABASE_URL` with the same credentials. URL-encode special characters in the password. Keep `.env` private; it is ignored by Git.

### Local PostgreSQL

Start PostgreSQL with Docker Compose:

```powershell
docker compose up -d db
```

### Neon PostgreSQL

Create a Neon project and copy its connection string from the Neon dashboard. Put it in the repository-root `.env` as `IMPACTFLOW_DATABASE_URL`; do not commit or share the connection string. Standard `postgresql://` Neon URLs (including `sslmode=require`) are supported and routed through the installed Psycopg 3 driver. URL-encode special characters in the password. For deployed applications, prefer Neon's pooled connection string when offered.

Once the database URL is configured, readiness verifies connectivity:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/ready
```

An unconfigured or unreachable database returns `503`; no database connection details are included in the response. A cold Neon compute may take several seconds to wake, so PostgreSQL connection attempts allow up to 10 seconds.

Install and run the API from the `backend` directory:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.cli seed-demo
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

If `py -3.12` is unavailable, use another Python 3.12+ interpreter to create the virtual environment. The API reads `IMPACTFLOW_DATABASE_URL` from the repository-root `.env` file.

`seed-demo` refuses to write if any business tables already contain records. It creates aggregate programme counts and synthetic source, pipeline-run, data-quality, and ingestion metadata.

OpenAPI UI: `http://127.0.0.1:8000/docs`

### CSV aggregate ingestion

Start the API and worker as separate processes using the same `IMPACTFLOW_DATABASE_URL`:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.worker
```

Create an active data source with type `CSV`, then submit a multipart request to `POST /api/v1/ingestions/csv` with `source_id` and a `.csv` file. Accepted headers are `name`, `category`, `province`, `target_beneficiaries`, `reached_beneficiaries`, and optional `status`. Uploads are limited to 2 MB and 2,000 rows; unsupported columns (including personal-data fields) are rejected. The endpoint queues a durable job and returns `202`; poll `GET /api/v1/ingestions/jobs/{job_id}` for its status. The worker imports aggregate programme rows and records ingestion/pipeline metadata. It does not call external systems.

## Health endpoints

- `GET /api/v1/health/live` checks only whether the API process responds.
- `GET /api/v1/health/ready` runs `SELECT 1` against PostgreSQL and returns `503` when no database is configured or the connection is unavailable.

## Business endpoints

- `GET /api/v1/dashboard/summary`, `/dashboard/programme-performance`, `/dashboard/provincial-reach`, and `/dashboard/snapshot?days=30`.
- List/create/update/delete `/api/v1/programmes`, `/api/v1/data-sources`, `/api/v1/organisations`, `/api/v1/locations`, and `/api/v1/datasets`. Deleting a source unlinks its datasets.
- List and record `/api/v1/pipeline-runs`, `/api/v1/data-quality/snapshots`, and `/api/v1/ingestion-records`.

List endpoints accept bounded pagination. Pipeline-run and quality routes record metadata only. The new file imports run in the API process; the older CSV job path runs in a separate worker.

## Tests and lint

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check .
```

The tests use SQLite in memory and do not require Docker or PostgreSQL. They cover health checks, Neon-style URL handling, unauthenticated access, dashboard aggregation, file imports and the CSV job flow. SQLite tests do not establish that a Neon database is reachable or migrated.

Verify database connectivity and migrations separately in each environment.

Alembic revision `0001_phase2_domain_schema` creates the initial application tables; `0002_database_ingestion_jobs` adds the durable ingestion queue; `0003_phase2_metadata_tables` adds organisation, location, and dataset metadata; `0004_phase3_imports` adds source details and import history; `0005_phase4_transformations` adds transformation history.
