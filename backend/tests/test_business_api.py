import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.cli import _seed_demo
from app.core.config import Settings
from app.database.base import Base
from app.database.session import create_database_engine
from app.main import create_app
from app.models import (
    DataQualitySnapshot,
    DataSource,
    IngestionRecord,
    Organisation,
    PipelineRun,
    Programme,
    User,
)
from app.worker import process_next_job


def create_test_client() -> TestClient:
    app = create_app(
        Settings(
            _env_file=None,
            database_url="sqlite+pysqlite:///:memory:",
        )
    )
    engine = app.state.database_engine
    Base.metadata.create_all(engine)
    return TestClient(app)


def test_business_routes_are_available_without_sign_in() -> None:
    with create_test_client() as client:
        response = client.get("/api/v1/programmes")
        login = client.post("/api/v1/auth/login", json={})

    assert response.status_code == 200
    assert login.status_code == 404


def test_metadata_management_and_source_relationship() -> None:
    with create_test_client() as client:
        headers = {}
        organisation = client.post(
            "/api/v1/organisations", headers=headers, json={"name": "Example organisation"}
        )
        assert organisation.status_code == 201
        assert client.post(
            "/api/v1/organisations", headers=headers, json={"name": "Example organisation"}
        ).status_code == 409
        another = client.post(
            "/api/v1/organisations", headers=headers, json={"name": "Another organisation"}
        )
        organisation_id = organisation.json()["id"]
        assert client.patch(
            f"/api/v1/organisations/{organisation_id}",
            headers=headers, json={"name": "Another organisation"},
        ).status_code == 409
        assert client.patch(
            f"/api/v1/organisations/{organisation_id}",
            headers=headers, json={"name": "Updated organisation"},
        ).json()["name"] == "Updated organisation"
        assert len(client.get("/api/v1/organisations?limit=1", headers=headers).json()) == 1

        assert client.post(
            "/api/v1/locations", headers=headers, json={"province": "Invalid"}
        ).status_code == 422
        location = client.post(
            "/api/v1/locations", headers=headers,
            json={"province": "Gauteng", "district": "District"},
        )
        assert location.status_code == 201
        location_id = location.json()["id"]
        assert client.patch(
            f"/api/v1/locations/{location_id}", headers=headers, json={"province": None}
        ).status_code == 422
        assert client.patch(
            f"/api/v1/locations/{location_id}", headers=headers, json={"district": None}
        ).json()["district"] is None
        assert len(client.get("/api/v1/locations", headers=headers).json()) == 1

        source = client.post(
            "/api/v1/data-sources", headers=headers, json={"name": "Source", "source_type": "CSV"}
        )
        source_id = source.json()["id"]
        dataset = client.post(
            "/api/v1/datasets", headers=headers,
            json={"name": "Dataset", "source_id": source_id},
        )
        assert dataset.status_code == 201
        dataset_id = dataset.json()["id"]
        second_dataset = client.post(
            "/api/v1/datasets", headers=headers, json={"name": "Second dataset"}
        )
        assert second_dataset.status_code == 201
        assert client.patch(
            f"/api/v1/datasets/{dataset_id}", headers=headers, json={"name": "Second dataset"}
        ).status_code == 409
        assert client.post(
            "/api/v1/datasets", headers=headers,
            json={"name": "Other", "source_id": "00000000-0000-0000-0000-000000000001"},
        ).status_code == 404
        assert client.patch(
            f"/api/v1/datasets/{dataset_id}", headers=headers, json={}
        ).status_code == 422
        assert client.patch(
            f"/api/v1/datasets/{dataset_id}", headers=headers, json={"description": "Metadata"}
        ).json()["description"] == "Metadata"
        assert client.patch(
            f"/api/v1/datasets/{dataset_id}", headers=headers, json={"source_id": None}
        ).json()["source_id"] is None
        assert client.patch(
            f"/api/v1/datasets/{dataset_id}", headers=headers, json={"source_id": source_id}
        ).json()["source_id"] == source_id
        assert client.delete(
            f"/api/v1/data-sources/{source_id}", headers=headers
        ).status_code == 204
        assert client.get("/api/v1/datasets", headers=headers).json()[0]["source_id"] is None
        for path, item_id in (
            ("organisations", organisation_id),
            ("organisations", another.json()["id"]),
            ("locations", location_id),
            ("datasets", dataset_id),
            ("datasets", second_dataset.json()["id"]),
        ):
            assert client.delete(f"/api/v1/{path}/{item_id}", headers=headers).status_code == 204
            assert client.delete(f"/api/v1/{path}/{item_id}", headers=headers).status_code == 404


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("organisations", {"name": "Organisation"}),
        ("locations", {"province": "Gauteng"}),
        ("datasets", {"name": "Dataset"}),
    ],
)
def test_metadata_routes_allow_reads_and_writes_without_sign_in(path: str, payload: dict) -> None:
    with create_test_client() as client:
        assert client.get(f"/api/v1/{path}").status_code == 200
        assert client.post(f"/api/v1/{path}", json=payload).status_code == 201


def test_can_create_business_records_and_read_dashboard_summary() -> None:
    with create_test_client() as client:
        headers = {}

        programme_response = client.post(
            "/api/v1/programmes",
            headers=headers,
            json={
                "name": "Demo learning",
                "category": "Education",
                "province": "Gauteng",
                "target_beneficiaries": 100,
                "reached_beneficiaries": 75,
            },
        )
        assert programme_response.status_code == 201

        source_response = client.post(
            "/api/v1/data-sources",
            headers=headers,
            json={
                "name": "Demo source",
                "source_type": "CSV",
                "records_count": 250,
            },
        )
        assert source_response.status_code == 201

        run_response = client.post(
            "/api/v1/pipeline-runs",
            headers=headers,
            json={
                "pipeline_name": "Recorded demo run",
                "source_id": source_response.json()["id"],
                "status": "succeeded",
            },
        )
        assert run_response.status_code == 201

        quality_response = client.post(
            "/api/v1/data-quality/snapshots",
            headers=headers,
            json={"score": 96.5},
        )
        assert quality_response.status_code == 201

        summary = client.get("/api/v1/dashboard/summary", headers=headers)
        assert summary.status_code == 200
        assert summary.json() == {
            "total_records": 250,
            "total_sources": 1,
            "active_sources": 1,
            "successful_pipelines": 1,
            "quality_score": 96.5,
            "beneficiaries": 75,
            "total_programmes": 1,
            "active_programmes": 1,
        }

        performance = client.get(
            "/api/v1/dashboard/programme-performance", headers=headers
        )
        assert performance.json() == [
            {"programme": "Demo learning", "achievement": 75.0, "target": 100}
        ]

        updated = client.patch(
            f"/api/v1/programmes/{programme_response.json()['id']}",
            headers=headers,
            json={"reached_beneficiaries": 80},
        )
        assert updated.status_code == 200
        assert updated.json()["reached_beneficiaries"] == 80

        duplicate = client.post(
            "/api/v1/programmes",
            headers=headers,
            json={
                "name": "Demo learning",
                "category": "Education",
                "province": "Gauteng",
                "target_beneficiaries": 100,
                "reached_beneficiaries": 75,
            },
        )
        assert duplicate.status_code == 409

        deleted_source = client.delete(
            f"/api/v1/data-sources/{source_response.json()['id']}",
            headers=headers,
        )
        assert deleted_source.status_code == 204
        pipeline_runs = client.get("/api/v1/pipeline-runs", headers=headers)
        assert pipeline_runs.json()[0]["source_id"] is None


def test_dashboard_totals_include_inactive_programmes_and_sources() -> None:
    with create_test_client() as client:
        headers = {}
        programme = client.post(
            "/api/v1/programmes", headers=headers,
            json={
                "name": "Inactive programme", "category": "Education", "province": "Gauteng",
                "target_beneficiaries": 1, "reached_beneficiaries": 0, "status": "inactive",
            },
        )
        source = client.post(
            "/api/v1/data-sources", headers=headers,
            json={"name": "Inactive source", "source_type": "CSV", "status": "inactive"},
        )
        assert programme.status_code == source.status_code == 201
        summary = client.get("/api/v1/dashboard/summary", headers=headers).json()
        snapshot = client.get("/api/v1/dashboard/snapshot", headers=headers).json()["metrics"]
        for metrics in (summary, snapshot):
            assert metrics["total_programmes"] == 1
            assert metrics["active_programmes"] == 0
            assert metrics["total_sources"] == 1
            assert metrics["active_sources"] == 0


def test_demo_seed_adds_only_synthetic_aggregate_records_and_is_idempotent() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            _seed_demo(session)
            assert session.scalar(select(func.count()).select_from(Programme)) == 4
            assert session.scalar(select(func.count()).select_from(DataSource)) == 3
            assert session.scalar(select(func.count()).select_from(PipelineRun)) == 6
            assert session.scalar(select(func.count()).select_from(DataQualitySnapshot)) == 4
            assert session.scalar(select(func.count()).select_from(IngestionRecord)) == 6
            assert session.scalar(select(func.count()).select_from(User)) == 0

            with pytest.raises(SystemExit, match="business tables"):
                _seed_demo(session)
    finally:
        engine.dispose()


def test_demo_seed_refuses_existing_organisation_metadata() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            session.add(Organisation(name="Existing organisation"))
            session.commit()
            with pytest.raises(SystemExit, match="business tables"):
                _seed_demo(session)
            assert session.scalar(select(func.count()).select_from(Programme)) == 0
    finally:
        engine.dispose()


def test_csv_upload_is_queued_then_imported_by_database_worker() -> None:
    csv_content = (
        "name,category,province,target_beneficiaries,reached_beneficiaries,status\n"
        "Learning Demo,Education,Gauteng,100,75,active\n"
        "Health Demo,Healthcare,Western Cape,80,40,\n"
    )
    with create_test_client() as client:
        headers = {}
        source_response = client.post(
            "/api/v1/data-sources",
            headers=headers,
            json={"name": "CSV Upload Demo", "source_type": "CSV"},
        )
        assert source_response.status_code == 201

        queued = client.post(
            "/api/v1/ingestions/csv",
            headers=headers,
            data={"source_id": source_response.json()["id"]},
            files={"file": ("programmes.csv", csv_content, "text/csv")},
        )
        assert queued.status_code == 202
        assert queued.json()["status"] == "queued"
        assert queued.json()["row_count"] == 2

        assert process_next_job(client.app.state.session_factory) is True
        job = client.get(f"/api/v1/ingestions/jobs/{queued.json()['id']}", headers=headers)
        assert job.status_code == 200
        assert job.json()["status"] == "succeeded"
        assert job.json()["imported_count"] == 2

        snapshot = client.get("/api/v1/dashboard/snapshot?days=7", headers=headers)
        assert snapshot.status_code == 200
        assert snapshot.json()["has_data"] is True
        assert snapshot.json()["metrics"]["total_records"] == 2
        assert snapshot.json()["metrics"]["beneficiaries"] == 115
        assert snapshot.json()["metrics"]["successful_pipelines"] == 1
        assert len(snapshot.json()["programme_performance"]) == 2


def test_csv_import_rejects_personal_columns_before_queueing() -> None:
    csv_content = (
        "name,category,province,target_beneficiaries,reached_beneficiaries,email\n"
        "Learning Demo,Education,Gauteng,100,75,person@example.com\n"
    )
    with create_test_client() as client:
        headers = {}
        source_response = client.post(
            "/api/v1/data-sources",
            headers=headers,
            json={"name": "CSV Upload Demo", "source_type": "CSV"},
        )
        response = client.post(
            "/api/v1/ingestions/csv",
            headers=headers,
            data={"source_id": source_response.json()["id"]},
            files={"file": ("programmes.csv", csv_content, "text/csv")},
        )

    assert response.status_code == 422
    assert "Unsupported CSV columns: email." in response.text
