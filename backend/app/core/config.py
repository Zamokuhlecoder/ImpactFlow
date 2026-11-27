from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class SourceConnection(BaseModel):
    kind: Literal["rest", "postgresql"]
    url: SecretStr
    table: str | None = Field(default=None, min_length=1, max_length=63)
    schema_name: str = Field(default="public", min_length=1, max_length=63)

    @model_validator(mode="after")
    def validate_connection(self) -> "SourceConnection":
        url = urlsplit(self.url.get_secret_value())
        if self.kind == "rest" and (url.scheme not in {"http", "https"} or not url.hostname):
            raise ValueError("REST connections require an HTTP or HTTPS URL.")
        if self.kind == "postgresql" and (
            url.scheme not in {"postgresql", "postgresql+psycopg"}
            or not url.hostname
            or not self.table
        ):
            raise ValueError("PostgreSQL connections require a URL and table.")
        return self


class Settings(BaseSettings):
    """Environment-backed settings for the ImpactFlow API."""

    model_config = SettingsConfigDict(
        env_prefix="IMPACTFLOW_",
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ImpactFlow API"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    database_url: str | None = None
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    docs_enabled: bool = True
    bronze_dir: Path = PROJECT_ROOT / ".impactflow" / "bronze"
    silver_dir: Path = PROJECT_ROOT / ".impactflow" / "silver"
    gold_dir: Path = PROJECT_ROOT / ".impactflow" / "gold"
    quarantine_dir: Path = PROJECT_ROOT / ".impactflow" / "quarantine"
    source_connections: dict[str, SourceConnection] = Field(default_factory=dict)
    airflow_base_url: str | None = None
    airflow_username: str | None = None
    airflow_password: SecretStr | None = None
    orchestration_token: SecretStr | None = None
    auth_secret_key: SecretStr | None = None
    auth_token_ttl_minutes: int = Field(default=480, ge=5, le=10080)
    governance_service_token: SecretStr | None = None
    dbt_project_dir: Path = PROJECT_ROOT / "dbt"