from fastapi.testclient import TestClient

from app.core.config import Settings
from app.database.base import Base
from app.main import create_app


class FakeAirflowResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def test_orchestration_reports_unavailable_without_airflow_configuration() -> None:
    app = create_app(
        Settings(_env_file=None, database_url="sqlite+pysqlite:///:memory:")
    )
    Base.metadata.create_all(app.state.database_engine)

    with TestClient(app) as client:
        summary = client.get("/api/v1/orchestration/monitoring/summary")
        dags = client.get("/api/v1/orchestration/dags")

    assert summary.status_code == 200
    assert summary.json()["available"] is False
    assert dags.status_code == 503


def test_orchestration_token_protects_routes() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            database_url="sqlite+pysqlite:///:memory:",
            orchestration_token="test-token",
        )
    )
    Base.metadata.create_all(app.state.database_engine)

    with TestClient(app) as client:
        missing = client.get("/api/v1/orchestration/monitoring/summary")
        invalid = client.get(
            "/api/v1/orchestration/monitoring/summary",
            headers={"X-Orchestration-Token": "wrong"},
        )

    assert missing.status_code == 401
    assert invalid.status_code == 403


def test_trigger_creates_correlation_record(monkeypatch) -> None:
    app = create_app(
        Settings(
            _env_file=None,
            database_url="sqlite+pysqlite:///:memory:",
            airflow_base_url="http://airflow",
        )
    )
    Base.metadata.create_all(app.state.database_engine)

    def fake_request(*args, **kwargs):
        assert args[0] == "POST"
        assert args[1].endswith("/api/v1/dags/impactflow_complete_pipeline/dagRuns")
        return FakeAirflowResponse({"dag_run_id": "manual__test", "state": "queued"})

    monkeypatch.setattr("app.orchestration.httpx.request", fake_request)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/orchestration/dags/impactflow_complete_pipeline/trigger",
            json={"conf": {}},
        )

    assert response.status_code == 201
    assert response.json()["orchestration_run"]["airflow_run_id"] == "manual__test"
