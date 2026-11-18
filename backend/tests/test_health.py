from fastapi.testclient import TestClient

from app.core.config import Settings
from app.database.session import create_database_engine
from app.main import create_app


def test_standard_postgresql_url_uses_psycopg_and_preserves_neon_ssl() -> None:
    engine = create_database_engine(
        "postgresql://impactflow:secret@ep-example.neon.tech/impactflow?sslmode=require"
    )

    try:
        assert engine.url.drivername == "postgresql+psycopg"
        assert engine.url.query["sslmode"] == "require"
    finally:
        engine.dispose()


def test_liveness_does_not_require_database() -> None:
    app = create_app(Settings(_env_file=None, database_url=None))

    with TestClient(app) as client:
        response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_missing_database_configuration() -> None:
    app = create_app(Settings(_env_file=None, database_url=None))

    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": {"status": "not_ready", "database": "not_configured"}}


def test_readiness_executes_query_against_database() -> None:
    app = create_app(
        Settings(_env_file=None, database_url="sqlite+pysqlite:///:memory:")
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "connected"}


def test_database_unavailable_is_reported_without_connection_details() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            database_url="postgresql+psycopg://impactflow:secret@127.0.0.1:1/impactflow",
        )
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": {"status": "not_ready", "database": "unavailable"}}
    assert "secret" not in response.text


def test_cors_allows_configured_frontend_origin() -> None:
    app = create_app(Settings(_env_file=None, database_url=None))

    with TestClient(app) as client:
        response = client.options(
            "/api/v1/health/live",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
