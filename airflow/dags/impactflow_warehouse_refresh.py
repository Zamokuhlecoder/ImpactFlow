import shutil
import subprocess
from datetime import datetime, timedelta

from airflow.decorators import dag, task
from impactflow_common import api_request


@dag(
    dag_id="impactflow_warehouse_refresh",
    description="Verify the Silver-to-warehouse state and optionally run dbt when installed.",
    schedule="0 3 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=2)},
    tags=["impactflow", "warehouse"],
)
def warehouse_refresh():
    @task
    def check_silver_and_warehouse() -> dict:
        datasets = api_request("GET", "processing/datasets")
        overview = api_request("GET", "warehouse/overview")
        if not datasets:
            raise RuntimeError("No imported datasets are available for warehouse refresh.")
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

    check = check_silver_and_warehouse()
    check >> run_dbt()


warehouse_refresh()
