from collections.abc import Iterator

from fastapi import HTTPException, Request, status
from sqlalchemy import Engine, create_engine, event, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def normalize_database_url(database_url: str) -> str:
    """Use the installed psycopg 3 driver for standard PostgreSQL URLs."""
    url = make_url(database_url)
    if url.drivername in {"postgres", "postgresql"}:
        return url.set(drivername="postgresql+psycopg").render_as_string(
            hide_password=False
        )
    return database_url


def create_database_engine(database_url: str) -> Engine:
    """Create the SQLAlchemy engine without opening a connection immediately."""
    normalized_url = normalize_database_url(database_url)
    url = make_url(normalized_url)
    if url.drivername.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        pool_options = (
            {"poolclass": StaticPool} if url.database in {None, "", ":memory:"} else {}
        )
    else:
        connect_args = {"connect_timeout": 10}
        pool_options = {}
    engine = create_engine(
        normalized_url,
        pool_pre_ping=True,
        connect_args=connect_args,
        **pool_options,
    )
    if url.drivername.startswith("sqlite"):
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def _enable_sqlite_foreign_keys(connection, _record) -> None:
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_db_session(request: Request) -> Iterator[Session]:
    """Yield a request-scoped SQLAlchemy session from the configured engine."""
    session_factory: sessionmaker[Session] | None = request.app.state.session_factory
    if session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured.",
        )
    with session_factory() as session:
        yield session
