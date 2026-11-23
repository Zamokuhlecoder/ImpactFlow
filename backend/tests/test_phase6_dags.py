from pathlib import Path

DAGS = Path(__file__).parents[2] / "airflow" / "dags"


def test_phase6_dags_define_expected_workflows_and_dependencies() -> None:
    complete = (DAGS / "impactflow_complete_pipeline.py").read_text(encoding="utf-8")
    quality = (DAGS / "impactflow_data_quality.py").read_text(encoding="utf-8")
    ingestion = (DAGS / "impactflow_scheduled_ingestion.py").read_text(encoding="utf-8")
    warehouse = (DAGS / "impactflow_warehouse_refresh.py").read_text(encoding="utf-8")

    assert 'dag_id="impactflow_complete_pipeline"' in complete
    assert "check_api" in complete
    assert "run_etl" in complete
    assert "verify_warehouse" in complete
    assert "warehouse >> dbt" in complete
    assert 'dag_id="impactflow_data_quality"' in quality
    assert 'dag_id="impactflow_scheduled_ingestion"' in ingestion
    assert 'schedule="0 * * * *"' in ingestion
    assert 'dag_id="impactflow_warehouse_refresh"' in warehouse
    assert "check >> run_dbt()" in warehouse
