import json
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from uuid import UUID

import pytest
import xlwt
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import SourceConnection
from app.models import DatasetImport
from app.phase3_ingestion import parse_dataset
from tests.test_business_api import create_test_client


def test_file_imports_preserve_originals_and_record_failures(tmp_path: Path) -> None:
    with create_test_client() as client:
        client.app.state.settings.bronze_dir = tmp_path
        headers = {}
        csv_source = client.post(
            "/api/v1/data-sources", headers=headers, json={"name": "Upload", "source_type": "CSV"}
        ).json()
        content = (
            b"name,category,province,target_beneficiaries,reached_beneficiaries\n"
            b"Youth Skills,Skills,Gauteng,20,10\n"
        )
        response = client.post(
            "/api/v1/imports/files",
            headers=headers,
            data={
                "source_id": csv_source["id"],
                "dataset_name": "Programmes",
                "schema_type": "aggregate",
            },
            files={"file": ("sample.csv", content, "text/csv")},
        )
        assert response.status_code == 201, response.text
        assert response.json()["records_received"] == 1
        assert client.get("/api/v1/programmes", headers=headers).json()[0]["name"] == "Youth Skills"
        with Session(client.app.state.database_engine) as session:
            entry = session.scalar(select(DatasetImport))
            assert entry is not None
            assert entry.raw_path is not None
            assert (tmp_path / entry.raw_path).read_bytes() == content

        invalid = client.post(
            "/api/v1/imports/files",
            headers=headers,
            data={"source_id": csv_source["id"], "dataset_name": "Bad", "schema_type": "aggregate"},
            files={"file": ("bad.csv", b"name\nwrong\n", "text/csv")},
        )
        assert invalid.status_code == 422
        failures = client.get("/api/v1/imports?import_status=failed", headers=headers).json()
        assert len(failures) == 1
        assert failures[0]["error_message"]


def test_json_and_excel_participation_imports(tmp_path: Path) -> None:
    with create_test_client() as client:
        client.app.state.settings.bronze_dir = tmp_path
        headers = {}
        workbook = Workbook()
        workbook.active.append(["Beneficiary ID", "Programme", "Province", "Participation Date"])
        workbook.active.append(["B001", "Youth Skills", "Gauteng", datetime(2026, 10, 12)])
        output = BytesIO()
        workbook.save(output)
        row = {
            "beneficiary_id": "B002",
            "programme": "Skills",
            "province": "Limpopo",
            "participation_date": "2026-10-15",
        }
        for source_type, filename, content in (
            ("Excel", "sample.xlsx", output.getvalue()),
            ("JSON", "sample.json", json.dumps([row]).encode()),
        ):
            source = client.post(
                "/api/v1/data-sources",
                headers=headers,
                json={"name": source_type, "source_type": source_type},
            ).json()
            result = client.post(
                "/api/v1/imports/files",
                headers=headers,
                data={
                    "source_id": source["id"],
                    "dataset_name": source_type,
                    "schema_type": "participation",
                },
                files={"file": (filename, content)},
            )
            assert result.status_code == 201, result.text
            assert result.json()["records_received"] == 1
            with Session(client.app.state.database_engine) as session:
                entry = session.get(DatasetImport, UUID(result.json()["id"]))
                assert entry is not None and entry.raw_path
                assert (tmp_path / entry.raw_path).read_bytes() == content
        assert len(client.get("/api/v1/datasets", headers=headers).json()) == 2


def test_import_history_is_available_without_sign_in() -> None:
    with create_test_client() as client:
        assert client.get("/api/v1/imports").status_code == 200


def test_rejects_oversized_and_formula_files() -> None:
    with pytest.raises(ValueError, match="2 MB"):
        parse_dataset(b"x" * (2 * 1024 * 1024 + 1), "csv", "aggregate")
    workbook = Workbook()
    workbook.active.append(["beneficiary_id", "programme", "province", "participation_date"])
    workbook.active.append(["B001", "=1+1", "Gauteng", "2026-10-12"])
    output = BytesIO()
    workbook.save(output)
    with pytest.raises(ValueError, match="formulas"):
        parse_dataset(output.getvalue(), "xlsx", "participation")
    with pytest.raises(ValueError, match="duplicate"):
        parse_dataset(
            b"Beneficiary ID,beneficiary_id,Programme,Province,Participation Date\n"
            b"B001,B002,Skills,Gauteng,2026-10-12\n",
            "csv",
            "participation",
        )


def test_rest_connector_imports_and_records_upstream_failures(tmp_path: Path) -> None:
    content = json.dumps(
        [
            {
                "name": "Connected programme",
                "category": "Skills",
                "province": "Gauteng",
                "target_beneficiaries": 20,
                "reached_beneficiaries": 10,
            }
        ]
    ).encode()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "/data")
                self.end_headers()
                return
            if self.path == "/compressed":
                self.send_response(200)
                self.send_header("Content-Encoding", "gzip")
                self.end_headers()
                return
            if self.path == "/large":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"x" * (2 * 1024 * 1024 + 1))
                return
            self.send_response(200)
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with create_test_client() as client:
            settings = client.app.state.settings
            settings.bronze_dir = tmp_path
            base_url = f"http://127.0.0.1:{server.server_port}"
            settings.source_connections = {
                "local": SourceConnection(kind="rest", url=f"{base_url}/data"),
                "redirect": SourceConnection(kind="rest", url=f"{base_url}/redirect"),
                "compressed": SourceConnection(kind="rest", url=f"{base_url}/compressed"),
                "large": SourceConnection(kind="rest", url=f"{base_url}/large"),
            }
            refs = client.get("/api/v1/imports/connections").json()
            assert {item["reference"] for item in refs} == {
                "local",
                "redirect",
                "compressed",
                "large",
            }
            assert base_url not in str(refs)
            source = client.post(
                "/api/v1/data-sources",
                json={
                    "name": "Connected source",
                    "source_type": "REST API",
                    "connection_ref": "local",
                },
            ).json()
            request = {
                "source_id": source["id"],
                "dataset_name": "Connected",
                "schema_type": "aggregate",
            }
            response = client.post("/api/v1/imports/connections", json=request)
            assert response.status_code == 201, response.text
            assert response.json()["records_received"] == 1
            with Session(client.app.state.database_engine) as session:
                entry = session.scalar(select(DatasetImport))
                assert entry is not None and entry.raw_path
                assert (tmp_path / entry.raw_path).read_bytes() == content
            assert client.get("/api/v1/dashboard/summary").json()["total_programmes"] == 1
            assert (
                client.patch(
                    f"/api/v1/data-sources/{source['id']}", json={"connection_ref": "redirect"}
                ).status_code
                == 200
            )
            failed = client.post("/api/v1/imports/connections", json=request)
            assert failed.status_code == 502
            history = client.get("/api/v1/imports?import_status=failed").json()
            assert len(history) == 1
            assert "non-success" in history[0]["error_message"]
            assert base_url not in str(history)
            for ref, reason in (("compressed", "Compressed"), ("large", "2 MB")):
                assert (
                    client.patch(
                        f"/api/v1/data-sources/{source['id']}", json={"connection_ref": ref}
                    ).status_code
                    == 200
                )
                failed = client.post("/api/v1/imports/connections", json=request)
                assert failed.status_code == 502
                assert reason in failed.json()["detail"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_connector_rejects_unconfigured_reference(tmp_path: Path) -> None:
    with create_test_client() as client:
        client.app.state.settings.bronze_dir = tmp_path
        source = client.post(
            "/api/v1/data-sources",
            json={
                "name": "Missing connection",
                "source_type": "PostgreSQL",
                "connection_ref": "missing",
            },
        ).json()
        response = client.post(
            "/api/v1/imports/connections",
            json={
                "source_id": source["id"],
                "dataset_name": "Missing",
                "schema_type": "participation",
            },
        )
        assert response.status_code == 502
        assert client.get("/api/v1/imports?import_status=failed").json()[0]["records_received"] == 0


def test_postgresql_connector_registers_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = (
        b'[{"beneficiary_id":"B001","programme":"Skills","province":"Gauteng",'
        b'"participation_date":"2026-10-12"}]'
    )
    seen: list[SourceConnection] = []

    def fake_fetch(config: SourceConnection) -> bytes:
        seen.append(config)
        return content

    monkeypatch.setattr("app.api.routes.imports.fetch_postgresql", fake_fetch)
    with create_test_client() as client:
        settings = client.app.state.settings
        settings.bronze_dir = tmp_path
        settings.source_connections = {
            "warehouse": SourceConnection(
                kind="postgresql", url="postgresql://localhost/example", table="participation"
            )
        }
        source = client.post(
            "/api/v1/data-sources",
            json={
                "name": "Database source",
                "source_type": "PostgreSQL",
                "connection_ref": "warehouse",
            },
        ).json()
        response = client.post(
            "/api/v1/imports/connections",
            json={
                "source_id": source["id"],
                "dataset_name": "Participation",
                "schema_type": "participation",
            },
        )
        assert response.status_code == 201, response.text
        assert response.json()["records_received"] == 1
        assert len(seen) == 1 and seen[0].table == "participation"
        with Session(client.app.state.database_engine) as session:
            entry = session.scalar(select(DatasetImport))
            assert entry is not None and entry.raw_path
            assert (tmp_path / entry.raw_path).read_bytes() == content


def test_invalid_excel_is_recorded_in_history(tmp_path: Path) -> None:
    with create_test_client() as client:
        client.app.state.settings.bronze_dir = tmp_path
        source = client.post(
            "/api/v1/data-sources",
            json={
                "name": "Invalid Excel",
                "source_type": "Excel",
            },
        ).json()
        result = client.post(
            "/api/v1/imports/files",
            data={"source_id": source["id"], "dataset_name": "Bad", "schema_type": "aggregate"},
            files={"file": ("bad.xlsx", b"not a workbook")},
        )
        assert result.status_code == 422
        history = client.get("/api/v1/imports?import_status=failed&source_type=Excel").json()
        assert len(history) == 1
        assert "invalid" in history[0]["error_message"].lower()


def test_legacy_excel_upload_preserves_original(tmp_path: Path) -> None:
    workbook = xlwt.Workbook()
    sheet = workbook.add_sheet("Data")
    for column, value in enumerate(
        ["beneficiary_id", "programme", "province", "participation_date"]
    ):
        sheet.write(0, column, value)
    for column, value in enumerate(["B001", "Skills", "Gauteng"]):
        sheet.write(1, column, value)
    sheet.write(1, 3, datetime(2026, 10, 12), xlwt.easyxf(num_format_str="YYYY-MM-DD"))
    output = BytesIO()
    workbook.save(output)
    with create_test_client() as client:
        client.app.state.settings.bronze_dir = tmp_path
        source = client.post(
            "/api/v1/data-sources", json={"name": "Legacy Excel", "source_type": "Excel"}
        ).json()
        result = client.post(
            "/api/v1/imports/files",
            data={
                "source_id": source["id"],
                "dataset_name": "Legacy",
                "schema_type": "participation",
            },
            files={"file": ("sample.xls", output.getvalue())},
        )
        assert result.status_code == 201, result.text
        assert result.json()["records_received"] == 1
        with Session(client.app.state.database_engine) as session:
            entry = session.get(DatasetImport, UUID(result.json()["id"]))
            assert entry is not None and entry.raw_path
            assert (tmp_path / entry.raw_path).read_bytes() == output.getvalue()
