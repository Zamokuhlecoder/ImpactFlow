from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import DataQualitySnapshot, DatasetImport, PipelineRun, TransformationRun
from tests.test_business_api import create_test_client


def _client_with_layers(tmp_path: Path):
    client = create_test_client()
    settings = client.app.state.settings
    settings.bronze_dir = tmp_path / "bronze"
    settings.silver_dir = tmp_path / "silver"
    settings.gold_dir = tmp_path / "gold"
    settings.quarantine_dir = tmp_path / "quarantine"
    return client


def test_generic_bronze_to_silver_gold_quarantine_and_history(tmp_path: Path) -> None:
    content = (
        b"Name,Province,Age,Programme\n"
        b"John,Gauteng,22,Skills\n"
        b"Sarah,gauteng,25,skills\n"
        b"Peter,NULL,-5,Skills\n"
        b"Mary,Limpopo,30,Skills\n"
        b"Sarah, Gauteng ,25, Skills \n"
    )
    with _client_with_layers(tmp_path) as client:
        source = client.post(
            "/api/v1/data-sources", json={"name": "Phase 4 CSV", "source_type": "CSV"}
        ).json()
        imported = client.post(
            "/api/v1/imports/files",
            data={
                "source_id": source["id"],
                "dataset_name": "Participants",
                "schema_type": "generic",
            },
            files={"file": ("participants.csv", content, "text/csv")},
        )
        assert imported.status_code == 201, imported.text
        import_id = imported.json()["id"]

        bronze = client.get(f"/api/v1/processing/datasets/{import_id}/layers/bronze")
        assert bronze.status_code == 200
        assert bronze.json()["datasets"][0]["records"][2]["province"] == "NULL"

        result = client.post(
            "/api/v1/processing/runs",
            json={"dataset_import_id": import_id, "pipeline_name": "standardize_validate"},
        )
        assert result.status_code == 201, result.text
        run = result.json()
        assert run["status"] == "warning"
        assert run["records_received"] == 5
        assert run["records_processed"] == 3
        assert run["records_rejected"] == 2
        assert run["duplicate_records"] == 1
        assert run["quality_report"] == {
            "total_records": 5,
            "valid_records": 3,
            "invalid_records": 1,
            "duplicate_records": 1,
            "missing_values": 1,
            "quality_percentage": 60,
        }

        silver = client.get(f"/api/v1/processing/datasets/{import_id}/layers/silver").json()
        silver_rows = silver["datasets"][0]["records"]
        assert [row["name"] for row in silver_rows] == ["John", "Sarah", "Mary"]
        assert [row["province"] for row in silver_rows] == ["Gauteng", "Gauteng", "Limpopo"]
        assert [row["programme"] for row in silver_rows] == ["Skills"] * 3

        rejected = client.get(
            f"/api/v1/processing/datasets/{import_id}/layers/quarantine"
        ).json()["datasets"][0]["records"]
        assert {tuple(row["errors"]) for row in rejected} == {
            ("age", "province"),
            ("duplicate_record",),
        }
        gold = client.get(f"/api/v1/processing/datasets/{import_id}/layers/gold").json()
        gold_by_name = {item["name"]: item["records"] for item in gold["datasets"]}
        assert gold_by_name["Programme Performance"][0]["participants"] == 3
        assert gold_by_name["Provincial Performance"][0] == {
            "province": "Gauteng",
            "records": 2,
            "participants": 2,
        }
        assert gold_by_name["Beneficiary Summary"][0]["unique_beneficiaries"] == 3

        history = client.get("/api/v1/processing/runs").json()
        assert len(history) == 1
        assert history[0]["id"] == run["id"]
        with client.app.state.session_factory() as session:
            assert session.query(TransformationRun).count() == 1
            assert session.query(PipelineRun).filter_by(
                pipeline_name="ETL standardisation and validation"
            ).count() == 1
            snapshot = session.query(DataQualitySnapshot).one()
            assert snapshot.score == 60

        datasets = client.get("/api/v1/processing/datasets").json()
        assert datasets[0]["latest_run"]["id"] == run["id"]


def test_participation_processing_checks_programme_reference_and_dates(
    tmp_path: Path,
) -> None:
    with _client_with_layers(tmp_path) as client:
        source = client.post(
            "/api/v1/data-sources", json={"name": "Participation", "source_type": "CSV"}
        ).json()
        programme_source = client.post(
            "/api/v1/data-sources", json={"name": "Programmes", "source_type": "CSV"}
        ).json()
        programme = client.post(
            "/api/v1/imports/files",
            data={
                "source_id": programme_source["id"],
                "dataset_name": "Programme definitions",
                "schema_type": "aggregate",
            },
            files={
                "file": (
                    "programmes.csv",
                    b"name,category,province,target_beneficiaries,reached_beneficiaries\n"
                    b"Skills,Employment,Gauteng,100,20\n",
                    "text/csv",
                )
            },
        )
        assert programme.status_code == 201, programme.text

        content = (
            b"beneficiary_id,programme,province,participation_date\n"
            b"B001,skills,gauteng,2026-10-12\n"
            b"B002,Unknown,Limpopo,not-a-date\n"
        )
        imported = client.post(
            "/api/v1/imports/files",
            data={
                "source_id": source["id"],
                "dataset_name": "Participation records",
                "schema_type": "participation",
            },
            files={"file": ("participation.csv", content, "text/csv")},
        )
        assert imported.status_code == 422
        failed_import = client.get("/api/v1/imports?import_status=failed").json()[0]
        import_id = failed_import["id"]

        result = client.post(
            "/api/v1/processing/runs",
            json={"dataset_import_id": import_id, "pipeline_name": "standardize_validate"},
        )
        assert result.status_code == 201, result.text
        assert result.json()["status"] == "warning"
        assert result.json()["records_processed"] == 1
        assert result.json()["records_rejected"] == 1
        quarantine = client.get(
            f"/api/v1/processing/datasets/{import_id}/layers/quarantine"
        ).json()["datasets"][0]["records"]
        assert set(quarantine[0]["errors"]) == {"participation_date", "programme"}

        with Session(client.app.state.database_engine) as session:
            bronze_path = client.app.state.settings.bronze_dir / session.get(
                DatasetImport, UUID(import_id)
            ).raw_path
        assert bronze_path.read_bytes() == content


def test_processing_failure_is_recorded_and_reported(tmp_path: Path) -> None:
    with _client_with_layers(tmp_path) as client:
        source = client.post(
            "/api/v1/data-sources", json={"name": "Bad source", "source_type": "CSV"}
        ).json()
        imported = client.post(
            "/api/v1/imports/files",
            data={
                "source_id": source["id"],
                "dataset_name": "Malformed rows",
                "schema_type": "generic",
            },
            files={"file": ("bad.csv", b"name,name\nA,B\n", "text/csv")},
        )
        assert imported.status_code == 422
        import_id = client.get("/api/v1/imports?import_status=failed").json()[0]["id"]

        result = client.post(
            "/api/v1/processing/runs",
            json={"dataset_import_id": import_id, "pipeline_name": "standardize_validate"},
        )
        assert result.status_code == 201, result.text
        assert result.json()["status"] == "failed"
        assert "duplicate columns" in result.json()["error_details"].lower()
        assert client.get("/api/v1/processing/runs").json()[0]["status"] == "failed"


def test_processing_api_exposes_only_configured_pipeline_and_layer_data(tmp_path: Path) -> None:
    with _client_with_layers(tmp_path) as client:
        pipelines = client.get("/api/v1/processing/pipelines").json()
        assert [item["name"] for item in pipelines] == ["standardize_validate"]
        assert client.get("/api/v1/processing/datasets").json() == []
        assert client.get(
            "/api/v1/processing/datasets/00000000-0000-0000-0000-000000000001/layers/silver"
        ).status_code == 404
