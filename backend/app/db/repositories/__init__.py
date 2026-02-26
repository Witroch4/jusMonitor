"""Repository modules for data access with tenant isolation."""

from app.db.repositories.base import BaseRepository
from app.db.repositories.case_movement import CaseMovementRepository
from app.db.repositories.client import ClientRepository
from app.db.repositories.client_automation import ClientAutomationRepository
from app.db.repositories.client_note import ClientNoteRepository
from app.db.repositories.lead import LeadRepository
from app.db.repositories.legal_case import LegalCaseRepository
from app.db.repositories.tenant import TenantRepository
from app.db.repositories.user import UserRepository

__all__ = [
    "BaseRepository",
    "TenantRepository",
    "UserRepository",
    "LeadRepository",
    "ClientRepository",
    "ClientNoteRepository",
    "ClientAutomationRepository",
    "LegalCaseRepository",
    "CaseMovementRepository",
]
