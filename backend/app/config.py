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
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://jusmonitoriaia.witdev.com.br",
    ]
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

    # Instagram OAuth
    instagram_app_id: str = "1543909259581320"
    instagram_app_secret: str = ""
    instagram_callback_url: str = "https://jusmonitoriaia.witdev.com.br/auth/instagram/callback"

    # Chatwit
    chatwit_api_url: str = "https://api.chatwit.com/v1"
    chatwit_api_key: str = ""
    chatwit_webhook_secret: str = ""
    chatwit_rate_limit_per_minute: int = 100

    # S3 / MinIO Storage
    s3_endpoint: str = "objstoreapi.witdev.com.br"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "jusmonitoria"
    s3_presign_expiry_seconds: int = 3600  # 1 hour

    # Certificate Encryption
    encrypt_key: str = ""  # Fernet key (32 bytes base64) for encrypting PFX blobs

    # MNI / Tribunal
    mni_wsdl_cache_path: str = "/tmp/zeep_cache.db"
    mni_request_timeout: int = 60
    mni_max_file_size_mb: int = 5

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
    openai_model: str = "gpt-4.1"                          # padrão geral / análise de petições
    openai_document_model: str = "gpt-4.1"                 # análise de documentos/petições
    openai_daily_model: str = "gpt-4.1-mini"               # rotina diária (DataJud poller / briefing)
    openai_embedding_model: str = "text-embedding-3-small"
    openai_max_tokens: int = 4096
    openai_temperature: float = 0.7

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    anthropic_haiku_model: str = "claude-haiku-4-5-20251001"  # modelo rápido/econômico
    anthropic_max_tokens: int = 4096

    google_api_key: str = ""
    google_model: str = "gemini-flash-latest"              # alias → gemini-2.5-flash mais recente
    google_document_model: str = "gemini-3-flash-preview"  # análise de documentos/petições
    google_daily_model: str = "gemini-flash-latest"        # rotina diária (DataJud poller / briefing)

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

    # Super Admin
    super_admin_email: str = ""
    super_admin_password: str = ""
    scheduler_enabled: bool = True

    # SMTP Configuration
    mailer_sender_email: str = "suporte@witdev.com.br"
    smtp_domain: str = "zoho.com"
    smtp_address: str = "smtp.zoho.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_authentication: str = "login"
    smtp_enable_starttls_auto: bool = True
    smtp_openssl_verify_mode: str = "peer"
    
    # Frontend URL for emails
    frontend_url: str = "http://localhost:3000"

    # SMTP Configuration
    mailer_sender_email: str = "suporte@witdev.com.br"
    smtp_domain: str = "zoho.com"
    smtp_address: str = "smtp.zoho.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_authentication: str = "login"
    smtp_enable_starttls_auto: bool = True
    smtp_openssl_verify_mode: str = "peer"
    
    # Frontend URL for emails
    frontend_url: str = "http://localhost:3000"

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
