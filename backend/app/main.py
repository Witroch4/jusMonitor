"""FastAPI application with Taskiq integration."""

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
from app.core.shutdown import setup_graceful_shutdown
from app.db.engine import close_db
from app.workers.broker import broker

# Configure structured logging
configure_logging()
logger = get_logger(__name__)


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
    
    yield
    
    # Shutdown
    logger.info("application_shutdown_initiated")
    
    # Shutdown Taskiq broker gracefully
    if not broker.is_worker_process:
        try:
            logger.info("shutting_down_taskiq_broker")
            await broker.shutdown()
            logger.info("taskiq_broker_shutdown_complete")
        except Exception as e:
            logger.error(
                "taskiq_broker_shutdown_error",
                error=str(e),
                error_type=type(e).__name__,
            )
    
    # Close database connections
    try:
        logger.info("closing_database_connections")
        await close_db()
        logger.info("database_connections_closed")
    except Exception as e:
        logger.error(
            "database_close_error",
            error=str(e),
            error_type=type(e).__name__,
        )
    
    logger.info("application_shutdown_complete")


# Create FastAPI application
app = FastAPI(
    title="JusMonitor CRM Orquestrador",
    description="""
## Sistema Multi-Tenant de Gestão Jurídica com IA

O JusMonitor é uma plataforma completa que integra:

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
        "name": "JusMonitor Support",
        "email": "suporte@jusmonitor.com",
        "url": "https://jusmonitor.com/support",
    },
    license_info={
        "name": "Proprietary",
        "url": "https://jusmonitor.com/license",
    },
    terms_of_service="https://jusmonitor.com/terms",
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
        "message": "JusMonitor CRM Orquestrador API",
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
