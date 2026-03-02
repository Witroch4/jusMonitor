"""Scraper service configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Bright Data Proxy
    bd_host: str = "brd.superproxy.io:33335"
    bd_username: str = ""
    bd_password: str = ""

    # S3 Storage
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "jusmonitoria"
    s3_endpoint: str = "objstoreapi.witdev.com.br"

    # Timeouts (seconds)
    navigation_timeout: int = 60
    wait_timeout: int = 20

    # Environment
    environment: str = "development"
    log_level: str = "INFO"


settings = Settings()
