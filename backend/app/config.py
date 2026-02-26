"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"
    secret_key: str = Field(..., min_length=32)
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: PostgresDsn
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: RedisDsn
    redis_max_connections: int = 50

    # JWT
    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]
    cors_allow_credentials: bool = True
    cors_max_age: int = 600  # 10 minutes
    
    # Security
    security_headers_enabled: bool = True
    max_payload_size_mb: int = 10  # Maximum request payload size in MB
    input_validation_enabled: bool = True  # XSS and SQL injection detection

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 100
    rate_limit_ai_per_minute: int = 10

    # HTTP Compression
    compression_enabled: bool = True
    compression_minimum_size: int = 500  # bytes
    compression_level: int = 6  # 1-9, balance between speed and ratio

    # HTTP Caching
    cache_enabled: bool = True
    cache_default_max_age: int = 0  # seconds, 0 = no cache
    cache_static_max_age: int = 86400  # 1 day for static resources
    cache_api_max_age: int = 60  # 1 minute for cacheable API responses

    # Chatwit
    chatwit_api_url: str = "https://api.chatwit.com/v1"
    chatwit_api_key: str = ""
    chatwit_webhook_secret: str = ""
    chatwit_rate_limit_per_minute: int = 100

    # DataJud
    DATAJUD_API_URL: str = "https://api-publica.datajud.cnj.jus.br"
    DATAJUD_API_KEY: str = ""
    DATAJUD_CERT_PATH: str = ""
    DATAJUD_KEY_PATH: str = ""
    DATAJUD_RATE_LIMIT_PER_HOUR: int = 100
    DATAJUD_BATCH_SIZE: int = 100
    DATAJUD_SYNC_INTERVAL_HOURS: int = 6

    # AI Providers
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo-preview"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_max_tokens: int = 4096
    openai_temperature: float = 0.7

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-opus-20240229"
    anthropic_max_tokens: int = 4096

    google_api_key: str = ""
    google_model: str = "gemini-pro"

    # LiteLLM
    litellm_fallback_enabled: bool = True
    litellm_retry_attempts: int = 3
    litellm_timeout_seconds: int = 60

    # Embeddings
    embedding_dimension: int = 1536
    embedding_batch_size: int = 50

    # Taskiq
    taskiq_workers: int = 4
    taskiq_max_retries: int = 3
    taskiq_retry_delay_seconds: int = 60

    # Monitoring
    prometheus_enabled: bool = True
    sentry_dsn: str = ""

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
