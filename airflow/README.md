# ImpactFlow orchestration

ImpactFlow uses Apache Airflow as an orchestration layer around the existing
FastAPI ETL and warehouse services. The DAGs do not reimplement transformation
logic: they call the existing `/api/v1/processing/runs` and
`/api/v1/warehouse/overview` services. The custom Airflow image installs
`dbt-postgres==1.8.2`, and the repository dbt project is mounted into the
scheduler and webserver containers.

## Local startup

Docker Desktop is required. Copy `.env.example` to `.env`, replace every
Airflow and PostgreSQL placeholder, and keep the file private.

```powershell
docker compose up -d db airflow-db
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
cd ..
docker compose up airflow-init
docker compose up -d airflow-webserver airflow-scheduler
```

Open Airflow at `http://127.0.0.1:8080`. DAGs are paused by default. Unpause
them only after the API is healthy at
`http://127.0.0.1:8000/api/v1/health/ready`.

The ImpactFlow orchestration proxy uses the Airflow REST API and never sends
Airflow credentials to the browser. Configure `IMPACTFLOW_AIRFLOW_BASE_URL`,
`IMPACTFLOW_AIRFLOW_USERNAME`, and `IMPACTFLOW_AIRFLOW_PASSWORD` in the API
environment before using the proxy endpoints. If
`IMPACTFLOW_ORCHESTRATION_TOKEN` is configured, send it as
`X-Orchestration-Token` to protect orchestration reads and manual triggers.

## DAGs

- `impactflow_complete_pipeline`: checks API health, selects a Bronze import,
  runs the existing ETL, verifies the warehouse load, and executes `dbt build`.
- `impactflow_scheduled_ingestion`: inventories configured sources and
  processable imports hourly. The current connector APIs do not expose a
  generic scheduled fetch operation, so this DAG does not invent one.
- `impactflow_data_quality`: invokes the existing standardise/validate
  service on a selected import.
- `impactflow_warehouse_refresh`: checks Silver/warehouse availability and
  executes `dbt build`.

Trigger a DAG from the ImpactFlow orchestration workspace or Airflow itself.
For a dataset-specific run, provide `dataset_import_id` in the DAG run
configuration.

The dbt project reads `DBT_HOST`, `DBT_PORT`, `DBT_DATABASE`, `DBT_USER`, and
`DBT_PASSWORD` from the Airflow scheduler environment. It builds staging views
from the Phase 5 warehouse facts and materializes programme and provincial
performance marts. A dbt failure fails the Airflow task; it is not converted
into a successful or skipped result.

## API proxy

- `GET /api/v1/orchestration/dags`
- `GET /api/v1/orchestration/runs`
- `POST /api/v1/orchestration/dags/{dag_id}/trigger`
- `GET /api/v1/orchestration/runs/{run_id}/tasks`
- `GET /api/v1/orchestration/monitoring/summary`

When Airflow is not configured or reachable, these endpoints return an
explicit unavailable response rather than synthetic execution data.
