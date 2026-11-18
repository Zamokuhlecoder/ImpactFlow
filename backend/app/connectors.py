import json
import time
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

import httpx
from sqlalchemy import MetaData, Table, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import SourceConnection
from app.database.session import create_database_engine
from app.ingestion import MAX_CSV_BYTES, MAX_CSV_ROWS


class ConnectorError(Exception):
    pass


def fetch_rest(connection: SourceConnection) -> bytes:
    deadline = time.monotonic() + 30
    try:
        with httpx.Client(timeout=10, follow_redirects=False, trust_env=False) as client:
            with client.stream(
                "GET", connection.url.get_secret_value(), headers={"Accept-Encoding": "identity"}
            ) as response:
                if response.status_code != 200:
                    raise ConnectorError("REST source returned a non-success response.")
                if response.headers.get("content-encoding", "identity").lower() != "identity":
                    raise ConnectorError("Compressed REST responses are not supported.")
                content = bytearray()
                for chunk in response.iter_raw():
                    if time.monotonic() > deadline:
                        raise ConnectorError("REST source exceeded the time limit.")
                    content.extend(chunk)
                    if len(content) > MAX_CSV_BYTES:
                        raise ConnectorError("REST response exceeds the 2 MB limit.")
                return bytes(content)
    except httpx.HTTPError:
        raise ConnectorError("REST source could not be reached.") from None


def _json_value(value: object) -> str:
    if isinstance(value, (date, datetime, Decimal, UUID)):
        return str(value)
    raise TypeError("Unsupported database value.")


def snapshot_postgresql(connection: Connection, config: SourceConnection) -> bytes:
    if config.table is None:
        raise ConnectorError("PostgreSQL source is not configured with a table.")
    connection.execute(text("SET TRANSACTION READ ONLY"))
    connection.execute(text("SET LOCAL statement_timeout = '15s'"))
    table = Table(config.table, MetaData(), schema=config.schema_name, autoload_with=connection)
    result = connection.execution_options(stream_results=True).execute(
        select(table).limit(MAX_CSV_ROWS + 1)
    )
    chunks: list[bytes] = []
    size = 2
    try:
        for index, row in enumerate(result.mappings()):
            if index >= MAX_CSV_ROWS:
                raise ConnectorError(f"Database source exceeds the {MAX_CSV_ROWS} row limit.")
            encoded = json.dumps(
                dict(row), default=_json_value, ensure_ascii=False, allow_nan=False
            ).encode("utf-8")
            size += len(encoded) + (1 if chunks else 0)
            if size > MAX_CSV_BYTES:
                raise ConnectorError("Database snapshot exceeds the 2 MB limit.")
            chunks.append(encoded)
    finally:
        result.close()
    return b"[" + b",".join(chunks) + b"]"


def fetch_postgresql(config: SourceConnection) -> bytes:
    engine = None
    try:
        engine = create_database_engine(config.url.get_secret_value())
        with engine.connect() as connection:
            with connection.begin():
                return snapshot_postgresql(connection, config)
    except (SQLAlchemyError, TypeError, ValueError):
        raise ConnectorError("PostgreSQL source could not be read.") from None
    finally:
        if engine is not None:
            engine.dispose()
