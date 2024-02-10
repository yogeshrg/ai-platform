"""AI Platform configuration."""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "AI Platform"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # Server
    host: str = "0.0.0.0"
    port: int = 8006

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_platform"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # RBAC
    default_roles: list[str] = Field(default=["admin", "developer", "viewer"])

    # Deployment
    kubernetes_namespace: str = "ai-platform"
    docker_registry: str = "localhost:5000"

    # Compliance
    audit_log_retention_days: int = 2555  # 7 years
    data_retention_days: int = 365

    # Monitoring
    metrics_port: int = 9090
    health_check_interval: int = 30


settings = Settings()