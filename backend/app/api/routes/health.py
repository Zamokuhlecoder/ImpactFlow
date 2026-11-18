import logging

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.health import LiveHealthResponse, ReadyHealthResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=LiveHealthResponse, name="liveness")
def liveness() -> LiveHealthResponse:
    """Report that the API process is responsive without requiring PostgreSQL."""
    return LiveHealthResponse()


@router.get("/ready", response_model=ReadyHealthResponse, name="readiness")
def readiness(request: Request) -> ReadyHealthResponse:
    """Report readiness only after the configured database accepts a query."""
    engine = request.app.state.database_engine
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "database": "not_configured"},
        )

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Database readiness check failed.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "database": "unavailable"},
        ) from None

    return ReadyHealthResponse()
