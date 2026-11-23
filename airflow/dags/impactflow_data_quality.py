from datetime import datetime, timedelta

from airflow.decorators import dag, task
from impactflow_common import api_request, dataset_import_id


@dag(
    dag_id="impactflow_data_quality",
    description="Run the existing standardise/validate service for a Silver candidate.",
    schedule="0 2 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=2)},
    tags=["impactflow", "quality"],
)
def data_quality():
    @task
    def validate(**context) -> dict:
        import_id = dataset_import_id(context["dag_run"].conf or {})
        return api_request(
            "POST",
            "processing/runs",
            json={"dataset_import_id": import_id, "pipeline_name": "standardize_validate"},
        )

    validate()


data_quality()
