from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from app.api.routes.business import router as business_router
from app.api.routes.health import router as health_router
from app.api.routes.imports import router as imports_router
from app.api.routes.ingestion import router as ingestion_router
from app.api.routes.metadata import router as metadata_router
from app.core.config import Settings
from app.database.session import create_database_engine


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an API application using the provided or environment settings."""
    app_settings = settings or Settings()
    engine = (
        create_database_engine(app_settings.database_url)
        if app_settings.database_url
        else None
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        database_engine = cast(Engine | None, app.state.database_engine)
        if database_engine is not None:
            database_engine.dispose()

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        docs_url="/docs" if app_settings.docs_enabled else None,
        redoc_url="/redoc" if app_settings.docs_enabled else None,
        openapi_url="/openapi.json" if app_settings.docs_enabled else None,
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    app.state.database_engine = engine
    app.state.session_factory = (
        sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        if engine is not None
        else None
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["DELETE", "GET", "OPTIONS", "PATCH", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(health_router, prefix=app_settings.api_prefix)
    app.include_router(business_router, prefix=app_settings.api_prefix)
    app.include_router(ingestion_router, prefix=app_settings.api_prefix)
    app.include_router(imports_router, prefix=app_settings.api_prefix)
    app.include_router(metadata_router, prefix=app_settings.api_prefix)
    return app


app = create_app()
