"""Main API v1 router."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    certificados,
    clients,
    dashboard,
    leads,
    peticoes,
    processos,
    storage,
    webhooks,
)

# Create main API v1 router
api_router = APIRouter(prefix="/v1")

# Include endpoint routers
api_router.include_router(auth.router)
api_router.include_router(clients.router)
api_router.include_router(dashboard.router)
api_router.include_router(leads.router)
api_router.include_router(webhooks.router)
api_router.include_router(certificados.router)
api_router.include_router(peticoes.router)
api_router.include_router(processos.router)
api_router.include_router(storage.router)

__all__ = ["api_router"]
