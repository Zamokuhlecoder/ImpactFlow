import json
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.base import Base
from app.main import create_app
from app.models import DatasetImport, Programme, TransformationRun
from app.warehouse import load_transformation_run


def test_silver_load_is_idempotent_and_exposes_warehouse_analytics(tmp_path) -> None:
    app = create_app(Settings(_env_file=None, database_url="sqlite+pysqlite:///:memory:"))
    engine = app.state.database_engine
    Base.metadata.create_all(engine)
    silver_file = tmp_path / "silver.json"
    silver_file.write_text(json.dumps([{
        "beneficiary_id": "B-001",
        "programme": "Skills",
        "province": "Gauteng",
        "participation_date": "2026-01-15",
    }]), encoding="utf-8")

    with Session(engine) as session:
        programme = Programme(
            name="Skills",
            category="Education",
            province="Gauteng",
            target_beneficiaries=10,
            reached_beneficiaries=8,
        )
        session.add(programme)
        session.flush()
        dataset_import = DatasetImport(
            dataset_name="Participation",
            schema_type="participation",
            source_name="Test source",
            source_type="CSV",
            status="succeeded",
            records_received=1,
        )
        session.add(dataset_import)
        session.flush()
        run = TransformationRun(
            dataset_import_id=dataset_import.id,
            pipeline_name="standardize_validate",
            schema_type="participation",
            status="succeeded",
            started_at=datetime.now(UTC),
        )
        session.add(run)
        session.flush()
        first = load_transformation_run(session, run, silver_file)
        second = load_transformation_run(session, run, silver_file)
        assert first.status == "succeeded"
        assert first.records_loaded == 1
        assert second.id == first.id

    with TestClient(app) as client:
        overview = client.get("/api/v1/warehouse/overview")
        provincial = client.get("/api/v1/analytics/provincial-performance")

    assert overview.status_code == 200
    assert overview.json()["facts"]["participation"] == 1
    assert provincial.json() == [{"province": "Gauteng", "programmes": 1, "participants": 1}]
