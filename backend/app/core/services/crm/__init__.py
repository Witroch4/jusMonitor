"""CRM services package."""

from app.core.services.crm.health_dashboard import HealthDashboardService
from app.core.services.crm.timeline import TimelineService

__all__ = [
    "TimelineService",
    "HealthDashboardService",
]
