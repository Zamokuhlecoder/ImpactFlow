from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_database_engine(database_url: str) -> Engine:
    """Create the SQLAlchemy engine without opening a connection immediately."""
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    else:
        connect_args = {"connect_timeout": 3}
    return create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


def get_db_session(request: Request) -> Iterator[Session]:
    """Yield a request-scoped SQLAlchemy session from the configured engine."""
    engine: Engine | None = request.app.state.database_engine
    if engine is None:
        raise RuntimeError("The database is not configured.")

    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_factory() as session:
        yield session
