import shutil
import subprocess
from datetime import datetime, timedelta

from airflow.decorators import dag, task
from impactflow_common import api_request, dataset_import_id


@dag(
    dag_id="impactflow_complete_pipeline",
    description="Ingest, validate, transform, load and publish one ImpactFlow dataset.",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=1)},
    tags=["impactflow", "etl", "warehouse"],
)
def complete_pipeline():
    @task
    def check_api() -> dict:
        return api_request("GET", "health/ready")

    @task
    def resolve_dataset(**context) -> str:
        return dataset_import_id(context["dag_run"].conf or {})

    @task
    def run_etl(import_id: str) -> dict:
        return api_request(
            "POST",
            "processing/runs",
            json={"dataset_import_id": import_id, "pipeline_name": "standardize_validate"},
        )

    @task
    def verify_warehouse(run: dict) -> dict:
        if run.get("status") not in {"succeeded", "warning"}:
            raise RuntimeError(f"ETL did not complete successfully: {run.get('status')}")
        overview = api_request("GET", "warehouse/overview")
        latest = overview.get("latest_load") or {}
        if latest.get("status") not in {"succeeded", "warning"}:
            raise RuntimeError("The ETL run did not produce a successful warehouse load.")
        return overview

    @task
    def run_dbt() -> str:
        if shutil.which("dbt") is None:
            raise RuntimeError("dbt is required in the Airflow image but was not found.")
        result = subprocess.run(
            [
                "dbt",
                "build",
                "--project-dir",
                "/opt/airflow/dbt",
                "--profiles-dir",
                "/opt/airflow/dbt",
                "--target",
                "dev",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode:
            raise RuntimeError((result.stdout + result.stderr)[-4000:])
        return "dbt build completed successfully."

    @task
    def capture_metrics(run: dict, warehouse: dict) -> dict:
        return {
            "transformation_run_id": run.get("id"),
            "records_processed": run.get("records_processed", 0),
            "records_rejected": run.get("records_rejected", 0),
            "warehouse_facts": warehouse.get("facts", {}),
        }

    api = check_api()
    import_id = resolve_dataset()
    run = run_etl(import_id)
    warehouse = verify_warehouse(run)
    dbt = run_dbt()
    api >> import_id
    run >> warehouse
    warehouse >> dbt
    capture_metrics(run, warehouse)


complete_pipeline()
