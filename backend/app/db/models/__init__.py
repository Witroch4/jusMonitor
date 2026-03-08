"""Database models package.

All models must be imported here for Alembic autogenerate to work.
"""

from app.db.models.ai_conversation import AIConversation
from app.db.models.ai_provider import AIProvider
from app.db.models.audit_log import AuditLog
from app.db.models.automation import Automation
from app.db.models.briefing import Briefing
from app.db.models.case_movement import CaseMovement
from app.db.models.client import Client, ClientStatus
from app.db.models.client_automation import ClientAutomation
from app.db.models.client_note import ClientNote
from app.db.models.event import Event
from app.db.models.lead import Lead, LeadSource, LeadStage, LeadStatus
from app.db.models.legal_case import LegalCase
from app.db.models.tag import ClientTag, LegalCaseTag, Tag
from app.db.models.tenant import Tenant
from app.db.models.timeline_embedding import TimelineEmbedding
from app.db.models.timeline_event import TimelineEvent
from app.db.models.user import User, UserRole
from app.db.models.user_preference import UserPreference
from app.db.models.notification import Notification
from app.db.models.agent_execution_log import AgentExecutionLog
from app.db.models.worker_schedule import WorkerSchedule
from app.db.models.certificado_digital import CertificadoDigital
from app.db.models.peticao import (
    DocumentoStatus,
    Peticao,
    PeticaoDocumento,
    PeticaoEvento,
    PeticaoStatus,
    TipoDocumento,
    TipoPeticao,
)
from app.db.models.tpu import TpuClasse, TpuAssunto, TpuDocumento, PjeJurisdicao
from app.db.models.processo_monitorado import ProcessoMonitorado
from app.db.models.user_integration import UserIntegration, IntegrationType
from app.db.models.caso_oab import CasoOAB
from app.db.models.oab_sync_config import OABSyncConfig
from app.db.models.scrape_job import ScrapeJob
from app.db.models.contrato import Contrato, TipoContrato, StatusContrato, IndiceReajuste
from app.db.models.fatura import Fatura, StatusFatura, FormaPagamento
from app.db.models.lancamento import Lancamento, TipoLancamento, CategoriaLancamento
from app.db.models.cobranca import Cobranca, TipoCobranca, StatusCobranca, CanalCobranca

__all__ = [
    "Tenant",
    "User",
    "UserRole",
    "UserPreference",
    "Lead",
    "LeadStatus",
    "LeadStage",
    "LeadSource",
    "Client",
    "ClientStatus",
    "ClientNote",
    "ClientAutomation",
    "LegalCase",
    "CaseMovement",
    "Tag",
    "ClientTag",
    "LegalCaseTag",
    "AIProvider",
    "AIConversation",
    "Briefing",
    "TimelineEvent",
    "TimelineEmbedding",
    "Event",
    "Automation",
    "AuditLog",
    "AgentExecutionLog",
    "WorkerSchedule",
    "CertificadoDigital",
    "Peticao",
    "PeticaoDocumento",
    "PeticaoEvento",
    "PeticaoStatus",
    "TipoPeticao",
    "TipoDocumento",
    "DocumentoStatus",
    "TpuClasse",
    "TpuAssunto",
    "PjeJurisdicao",
    "ProcessoMonitorado",
    "UserIntegration",
    "IntegrationType",
    "CasoOAB",
    "OABSyncConfig",
    "ScrapeJob",
    "Contrato",
    "TipoContrato",
    "StatusContrato",
    "IndiceReajuste",
    "Fatura",
    "StatusFatura",
    "FormaPagamento",
    "Lancamento",
    "TipoLancamento",
    "CategoriaLancamento",
    "Cobranca",
    "TipoCobranca",
    "StatusCobranca",
    "CanalCobranca",
]
