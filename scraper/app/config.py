"""Scraper service configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Proxy ---
    # Default: Bright Data (legacy)
    bd_host: str = "brd.superproxy.io:33335"
    bd_username: str = ""
    bd_password: str = ""

    # Decodo/Smartproxy — ativado via SMARTPROXY_DECODO=true
    smartproxy_decodo: bool = False
    proxy_host: str = "gate.decodo.com"
    proxy_port: int = 7000
    proxy_user: str = ""
    proxy_pass: str = ""

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

    # Browser pool
    browser_pool_size: int = 2
    browser_max_uses: int = 20

    # ── Certificado A1 para login no PJe (scraper de comarcas / peticionamento) ──
    # Path dentro do container: /app/shared-docs/Amanda Alves de Sousa_07071649316.pfx
    pje_pfx_path: str = "/app/shared-docs/Amanda Alves de Sousa_07071649316.pfx"
    pje_pfx_password: str = "22051998"
    # TOTP base32 secret (vazio = sem 2FA)
    pje_totp_secret: str = ""

    # ── Comunicação interna com o backend FastAPI ──
    # Usado pelo scraper para sincronizar dados coletados com o banco via API REST
    backend_url: str = "http://backend:8000"

    # ── Scheduler de coleta de comarcas ──
    # Intervalo em horas para re-executar a coleta automática (0 = desabilitado)
    comarcas_refresh_interval_hours: int = 30


settings = Settings()


# ── Per-tribunal throttling config ──
# Controls how aggressively we scrape each tribunal.
# This prevents IP blocking and makes the scraper behave more humanly.

from dataclasses import dataclass


@dataclass
class TribunalThrottleConfig:
    """Rate limiting and delay configuration per tribunal."""
    max_concurrent: int = 1          # Max concurrent requests to this tribunal
    delay_between_requests: tuple[float, float] = (5.0, 15.0)  # Delay range (seconds)
    delay_between_docs: tuple[float, float] = (3.0, 8.0)       # Delay between doc downloads
    delay_between_pages: tuple[float, float] = (1.0, 3.0)      # Delay between movement pages
    max_requests_per_hour: int = 30  # Hard cap
    backoff_on_error: float = 30.0   # Wait this long after an error


TRIBUNAL_THROTTLE: dict[str, TribunalThrottleConfig] = {
    "trf1": TribunalThrottleConfig(
        max_concurrent=1,
        delay_between_requests=(5.0, 12.0),
        delay_between_docs=(3.0, 6.0),
        max_requests_per_hour=40,
    ),
    "trf3": TribunalThrottleConfig(
        max_concurrent=1,
        delay_between_requests=(8.0, 18.0),
        delay_between_docs=(4.0, 8.0),
        max_requests_per_hour=25,
    ),
    "trf5": TribunalThrottleConfig(
        max_concurrent=1,
        delay_between_requests=(5.0, 12.0),
        delay_between_docs=(3.0, 6.0),
        max_requests_per_hour=40,
    ),
    "trf6": TribunalThrottleConfig(
        max_concurrent=1,
        delay_between_requests=(8.0, 18.0),
        delay_between_docs=(4.0, 8.0),
        max_requests_per_hour=25,
    ),
    "tjce": TribunalThrottleConfig(
        max_concurrent=1,
        delay_between_requests=(5.0, 12.0),
        delay_between_docs=(3.0, 6.0),
        max_requests_per_hour=30,
    ),
    "tjce2g": TribunalThrottleConfig(
        max_concurrent=1,
        delay_between_requests=(5.0, 12.0),
        delay_between_docs=(3.0, 6.0),
        max_requests_per_hour=30,
    ),
}

# Default for unknown tribunals
DEFAULT_THROTTLE = TribunalThrottleConfig()


def get_throttle(tribunal: str) -> TribunalThrottleConfig:
    """Get throttle config for a tribunal."""
    return TRIBUNAL_THROTTLE.get(tribunal.lower(), DEFAULT_THROTTLE)
