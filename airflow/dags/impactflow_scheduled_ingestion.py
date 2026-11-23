from datetime import datetime, timedelta

from airflow.decorators import dag, task
from impactflow_common import api_request


@dag(
    dag_id="impactflow_scheduled_ingestion",
    description="Check configured ImpactFlow sources and available Bronze datasets.",
    schedule="0 * * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=2)},
    tags=["impactflow", "ingestion"],
)
def scheduled_ingestion():
    @task
    def inspect_sources() -> dict:
        sources = api_request("GET", "data-sources")
        datasets = api_request("GET", "processing/datasets")
        return {
            "sources": len(sources),
            "datasets": len(datasets),
            "processable_datasets": sum(bool(item.get("can_process")) for item in datasets),
        }

    inspect_sources()


scheduled_ingestion()
