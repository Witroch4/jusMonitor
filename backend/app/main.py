"""FastAPI application with Taskiq integration."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware.audit import AuditMiddleware
from app.core.middleware.cache import CacheMiddleware
from app.core.middleware.logging import LoggingMiddleware
from app.core.middleware.metrics import MetricsMiddleware
from app.core.middleware.rate_limit import RateLimitMiddleware
from app.core.middleware.security import SecurityHeadersMiddleware
from app.core.middleware.shutdown import ShutdownMiddleware
from app.core.middleware.tenant import TenantMiddleware
from app.core.shutdown import setup_graceful_shutdown
from app.db.engine import close_db
from app.workers.broker import broker

# Configure structured logging
configure_logging()
logger = get_logger(__name__)

# Suppress noisy health-check lines from uvicorn access log
class _HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        return "GET /health" not in record.getMessage()

logging.getLogger("uvicorn.access").addFilter(_HealthCheckFilter())


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan.
    
    Handles startup and shutdown of:
    - Graceful shutdown handler (signal handlers)
    - Taskiq broker (Redis connection pool)
    - Database connections
    - Other resources
    """
    # Startup
    logger.info("application_startup", environment=settings.environment)
    
    # Setup graceful shutdown handler
    shutdown_handler = setup_graceful_shutdown(
        shutdown_timeout=30.0,
        force_shutdown_timeout=60.0,
    )
    shutdown_handler.setup_signal_handlers()
    logger.info("graceful_shutdown_configured")
    
    # Initialize Taskiq broker
    if not broker.is_worker_process:
        await broker.startup()
        logger.info("taskiq_broker_started")
        
        # Register broker shutdown callback
        shutdown_handler.register_shutdown_callback(broker.shutdown)
    
    # Register database cleanup callback
    shutdown_handler.register_shutdown_callback(close_db)

    # Start task scheduler
    if settings.scheduler_enabled:
        from app.workers.scheduler import start_scheduler, stop_scheduler
        await start_scheduler()
        logger.info("task_scheduler_started")
        shutdown_handler.register_shutdown_callback(stop_scheduler)

    # Garante que as tabelas TPU estejam populadas; se vazias, dispara sync em background
    from app.workers.tasks.tpu_sync import ensure_tpu_populated
    await ensure_tpu_populated()

    yield
    
    # Shutdown — these run both via signal handler callbacks AND here (lifespan post-yield).
    # The try/except blocks handle the case where resources were already cleaned up by the
    # signal handler's shutdown callbacks, avoiding double-cleanup errors.
    logger.info("application_shutdown_initiated")
    
    # Shutdown Taskiq broker gracefully
    if not broker.is_worker_process:
        try:
            if not shutdown_handler.is_shutting_down:
                logger.info("shutting_down_taskiq_broker")
                await broker.shutdown()
                logger.info("taskiq_broker_shutdown_complete")
            else:
                logger.info("taskiq_broker_already_shutdown_by_signal_handler")
        except Exception as e:
            logger.error(
                "taskiq_broker_shutdown_error",
                error=str(e),
                error_type=type(e).__name__,
            )
    
    # Close database connections
    try:
        if not shutdown_handler.is_shutting_down:
            logger.info("closing_database_connections")
            await close_db()
            logger.info("database_connections_closed")
        else:
            logger.info("database_already_closed_by_signal_handler")
    except Exception as e:
        logger.error(
            "database_close_error",
            error=str(e),
            error_type=type(e).__name__,
        )
    
    logger.info("application_shutdown_complete")


# Create FastAPI application
app = FastAPI(
    title="JusMonitorIA CRM Orquestrador",
    description="""
## Sistema Multi-Tenant de Gestão Jurídica com IA

O JusMonitorIA é uma plataforma completa que integra:

* **CRM Inteligente**: Gestão de leads e clientes com qualificação automática por IA
* **Monitoramento Processual**: Sincronização automática com DataJud (API do CNJ)
* **Agentes de IA**: Triagem, investigação, redação e orquestração
* **Busca Semântica**: Embeddings vetoriais com pgvector
* **Notificações em Tempo Real**: WebSocket para atualizações instantâneas

### Autenticação

Todos os endpoints (exceto `/auth/login` e webhooks) requerem autenticação via JWT:

```
Authorization: Bearer <access_token>
```

O token JWT contém o `tenant_id` que é usado para isolamento multi-tenant.

### Rate Limiting

* **Endpoints gerais**: 100 requisições/minuto
* **Endpoints de IA**: 10 requisições/minuto
* **Login**: 5 tentativas/minuto

### Paginação

Endpoints de listagem suportam paginação via query parameters:

* `limit`: Número de itens por página (padrão: 20, máximo: 100)
* `offset`: Número de itens para pular (padrão: 0)

### Filtros e Ordenação

* `sort_by`: Campo para ordenação
* `sort_order`: `asc` ou `desc` (padrão: `desc`)
* `search`: Busca textual (quando disponível)

### Códigos de Status HTTP

* `200 OK`: Sucesso
* `201 Created`: Recurso criado
* `204 No Content`: Sucesso sem corpo de resposta
* `400 Bad Request`: Dados inválidos
* `401 Unauthorized`: Não autenticado
* `403 Forbidden`: Sem permissão
* `404 Not Found`: Recurso não encontrado
* `409 Conflict`: Conflito (ex: duplicata)
* `422 Unprocessable Entity`: Validação falhou
* `429 Too Many Requests`: Rate limit excedido
* `500 Internal Server Error`: Erro no servidor
    """,
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.debug,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "JusMonitorIA Support",
        "email": "suporte@jusmonitoria.com",
        "url": "https://jusmonitoria.com/support",
    },
    license_info={
        "name": "Proprietary",
        "url": "https://jusmonitoria.com/license",
    },
    terms_of_service="https://jusmonitoria.com/terms",
    openapi_tags=[
        {
            "name": "auth",
            "description": "Autenticação e autorização (login, refresh token, logout)",
        },
        {
            "name": "leads",
            "description": "Gestão de leads do funil de vendas",
        },
        {
            "name": "clients",
            "description": "Gestão de clientes e prontuário 360º",
        },
        {
            "name": "processes",
            "description": "Gestão de processos jurídicos e movimentações",
        },
        {
            "name": "dashboard",
            "description": "Central Operacional com briefing matinal e métricas",
        },
        {
            "name": "timeline",
            "description": "Timeline de eventos de clientes e processos",
        },
        {
            "name": "webhooks",
            "description": "Recebimento de webhooks de integrações externas (Chatwit)",
        },
        {
            "name": "health",
            "description": "Health checks e status do sistema",
        },
        {
            "name": "metrics",
            "description": "Métricas Prometheus para monitoramento",
        },
        {
            "name": "audit",
            "description": "Logs de auditoria de operações",
        },
        {
            "name": "admin",
            "description": "Super Admin: gestão de tenants, users, agentes IA, workers e métricas globais",
        },
        {
            "name": "certificados",
            "description": "Gestão de certificados digitais A1 (ICP-Brasil) para mTLS e assinatura",
        },
        {
            "name": "peticoes",
            "description": "Gestão de petições e protocolo eletrônico via MNI 2.2.2",
        },
        {
            "name": "tribunais",
            "description": "Registro de tribunais com endpoints MNI e configurações",
        },
        {
            "name": "contratos",
            "description": "Gestão de contratos jurídicos",
        },
        {
            "name": "financeiro",
            "description": "Gestão financeira: faturas, lançamentos e dashboard",
        },
    ],
)

# Configure middlewares
# Note: Middleware order matters - they execute in reverse order of addition
# (last added = first executed)

# Compression should be last (first to execute) to compress final response
if settings.compression_enabled:
    app.add_middleware(
        GZipMiddleware,
        minimum_size=settings.compression_minimum_size,
        compresslevel=settings.compression_level,
    )
    logger.info(
        "compression_enabled",
        minimum_size=settings.compression_minimum_size,
        level=settings.compression_level,
    )

# Cache middleware adds Cache-Control and ETag headers
if settings.cache_enabled:
    app.add_middleware(
        CacheMiddleware,
        default_max_age=settings.cache_default_max_age,
        static_max_age=settings.cache_static_max_age,
        api_max_age=settings.cache_api_max_age,
    )
    logger.info(
        "cache_enabled",
        static_max_age=settings.cache_static_max_age,
        api_max_age=settings.cache_api_max_age,
    )

app.add_middleware(AuditMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(TenantMiddleware)  # Extract tenant_id from JWT/header into request.state
app.add_middleware(ShutdownMiddleware)  # Track in-flight requests
app.add_middleware(RateLimitMiddleware)  # Rate limiting before CORS

# Security headers middleware (add security headers to all responses)
if settings.security_headers_enabled:
    app.add_middleware(SecurityHeadersMiddleware)
    logger.info("security_headers_enabled")

# CORS middleware with restrictive configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],  # Explicit methods
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "User-Agent",
        "DNT",
        "Cache-Control",
        "X-Requested-With",
        "X-Tenant-ID",
    ],  # Explicit headers
    expose_headers=["Content-Length", "X-Request-ID"],
    max_age=settings.cors_max_age,
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "version": "0.1.0",
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "JusMonitorIA CRM Orquestrador API",
        "version": "0.1.0",
        "docs": "/docs",
    }


# WebSocket endpoint for real-time notifications
from app.api.v1.websocket import websocket_endpoint

app.websocket("/ws")(websocket_endpoint)


# Include metrics endpoint (no prefix, at root level)
from app.api.v1.endpoints.metrics import router as metrics_router

app.include_router(metrics_router)

# Include health check endpoints (no prefix, at root level)
from app.api.v1.endpoints.health import router as health_router

app.include_router(health_router)

# Include API v1 routers with prefix
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.leads import router as leads_router
from app.api.v1.endpoints.clients import router as clients_router
from app.api.v1.endpoints.dashboard import router as dashboard_router
from app.api.v1.endpoints.audit import router as audit_router
from app.api.v1.endpoints.webhooks import router as webhooks_router

app.include_router(auth_router, prefix=settings.api_v1_prefix, tags=["auth"])
app.include_router(leads_router, prefix=settings.api_v1_prefix, tags=["leads"])
app.include_router(clients_router, prefix=settings.api_v1_prefix, tags=["clients"])
app.include_router(dashboard_router, prefix=settings.api_v1_prefix, tags=["dashboard"])
app.include_router(audit_router, prefix=settings.api_v1_prefix, tags=["audit"])
app.include_router(webhooks_router, tags=["webhooks"])  # No prefix for webhooks

# Profile and Integrations endpoints
from app.api.v1.endpoints.profile import router as profile_router
from app.api.v1.endpoints.integrations import router as integrations_router

app.include_router(profile_router, prefix=settings.api_v1_prefix, tags=["profile"])
app.include_router(integrations_router, prefix=settings.api_v1_prefix, tags=["integrations"])

# Super Admin endpoints
from app.api.v1.endpoints.admin import router as admin_router

app.include_router(admin_router, prefix=settings.api_v1_prefix, tags=["admin"])

# Certificados digitais endpoints
from app.api.v1.endpoints.certificados import router as certificados_router

app.include_router(certificados_router, prefix=settings.api_v1_prefix, tags=["certificados"])

# Petições e Tribunais endpoints
from app.api.v1.endpoints.peticoes import router as peticoes_router
from app.api.v1.endpoints.tribunais import router as tribunais_router

app.include_router(peticoes_router, prefix=settings.api_v1_prefix, tags=["peticoes"])
app.include_router(tribunais_router, prefix=settings.api_v1_prefix, tags=["tribunais"])

# Processos (consulta MNI em tempo real) endpoints
from app.api.v1.endpoints.processos import router as processos_router

app.include_router(processos_router, prefix=settings.api_v1_prefix, tags=["processos"])

# Processos Monitorados (monitoramento via DataJud) endpoints
from app.api.v1.endpoints.processos_monitorados import router as processos_monitorados_router

app.include_router(processos_monitorados_router, prefix=settings.api_v1_prefix, tags=["processos-monitorados"])

# TPU (Tabelas Processuais Unificadas) endpoints
from app.api.v1.endpoints.tpu import router as tpu_router

app.include_router(tpu_router, prefix=settings.api_v1_prefix, tags=["tpu"])

# OAB-scraped cases (Casos) endpoints
from app.api.v1.endpoints.casos_oab import router as casos_oab_router

app.include_router(casos_oab_router, prefix=settings.api_v1_prefix, tags=["casos-oab"])

# Contratos e Financeiro endpoints
from app.api.v1.endpoints.contratos import router as contratos_router
from app.api.v1.endpoints.financeiro import router as financeiro_router

app.include_router(contratos_router, prefix=settings.api_v1_prefix, tags=["contratos"])
app.include_router(financeiro_router, prefix=settings.api_v1_prefix, tags=["financeiro"])

# S3/MinIO storage — presigned URL generation
from app.api.v1.endpoints.storage import router as storage_router

app.include_router(storage_router, prefix=settings.api_v1_prefix, tags=["storage"])

# Serve static files (avatars, etc.)
import os

from fastapi.staticfiles import StaticFiles

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
