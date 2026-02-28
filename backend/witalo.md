docker compose exec backend alembic upgrade head

./scripts/seed.sh --all

Relatório Completo do Backend - JusMonitor
Visão Geral
O backend é uma aplicação FastAPI modular multi-tenant com arquitetura em camadas, async/await em toda a stack, e integração IA com múltiplos provedores.

1. app/api/v1/endpoints/ — Rotas HTTP
Arquivo	Função
auth.py	Login (rate limited 5/min), refresh token, logout, GET /me
leads.py	CRUD de leads, transição de estágio (state machine), scoring por IA, histórico de funil
clients.py	CRUD de clientes, timeline de eventos, health score, notas com @mentions, automações
dashboard.py	Casos urgentes (<3 dias), sem movimento (>30 dias), boas notícias, KPIs com trends
audit.py	Listagem de logs de auditoria com filtros avançados
websocket.py	WebSocket por tenant para updates real-time
notifications.py	Gerenciamento de notificações
2. app/core/auth/ — Autenticação e Autorização
Arquivo	Função
jwt.py	Geração/validação de JWT (access 30min, refresh 7d), RBAC com 4 roles (admin, lawyer, assistant, viewer)
dependencies.py	Dependências FastAPI: get_current_user, get_current_tenant_id, get_db
password.py	Hash bcrypt e verificação segura
3. app/core/middleware/ — Middleware Global
Arquivo	Função
audit.py	Captura IP, loga operações de escrita (POST/PUT/PATCH/DELETE)
logging.py	Log de request/response com tempo de execução
metrics.py	Métricas Prometheus (contadores, histogramas, gauges)
rate_limit.py	Rate limiting (100/min geral, 10/min IA, 5/min login)
security.py	Headers de segurança (CSP, HSTS, X-Frame-Options)
cache.py	Cache-Control e ETag
shutdown.py	Graceful shutdown com tracking de requests em voo
compression.py	GZip para responses
4. app/core/services/ — Serviços de Domínio
Módulo	Função
lead_state_machine.py	Máquina de estados do funil (novo → contatado → qualificado → proposta → negociação → convertido) com validação de transições
lead_scorer.py	Pontuação 0-100 baseada em urgência (30%), tipo de caso (25%), engagement (25%), completude (20%)
funnel_automations.py	Automações de transição (score > 80 → qualificado, sem resposta 7d → lost)
timeline.py	Agregação de eventos de múltiplas fontes (movimentos, notas, mensagens, automações)
health_dashboard.py	Health score do cliente baseado em atividade, status dos casos e tempo de resposta
datajud/	Cliente API DataJud (rate limited 100/h), batcher para sync em lote, parser de movimentações
dashboard/	Cálculo de KPIs e agregação de métricas com trend analysis
search/semantic.py	Busca semântica via pgvector embeddings
audit_service.py	Log automático de todas as operações com before/after
chatwit_client.py	Integração com Chatwit (chatbot de leads, webhooks, tags)
5. app/db/ — Banco de Dados
Base e Mixins (base.py):

UUIDMixin — PK UUID
TimestampMixin — created_at/updated_at automáticos
TenantMixin — tenant_id com FK para isolamento
TenantBaseModel — combina todos (base de quase todos os modelos)
Modelos (models/):

Modelo	Descrição
Tenant	Raiz multi-tenant (escritório)
User	Usuários com role (admin/lawyer/assistant/viewer)
Lead	Funil CRM: stage, score, source, ai_summary
Client	Clientes ativos: cpf_cnpj, health_score, custom_fields
LegalCase	Processos: cnj_number, tribunal, prazos, monitoring
CaseMovement	Movimentações DataJud: tipo, importância, prazo
TimelineEvent	Eventos unificados de múltiplas fontes
TimelineEmbedding	Vetores pgvector (1536 dims) para busca semântica
AIProvider	Config de provedores IA por tenant (OpenAI, Anthropic, Google)
AIConversation	Histórico de conversas com IA
AuditLog	Log de auditoria completo
Notification	Notificações para usuários
UserPreference	Preferências customizáveis
Repositories (repositories/):

BaseRepository[T] — CRUD genérico com filtro automático por tenant_id
Especializados: LeadRepository, ClientRepository, LegalCaseRepository
Versões otimizadas com eager loading para queries complexas
Engine (engine.py):

AsyncEngine com pool de 20 conexões + 10 overflow
Session factory com auto commit/rollback
6. app/ai/ — Inteligência Artificial
Agentes (agents/):

Agente	Função
TriageAgent	Qualifica leads automaticamente (score, urgência, tipo de caso)
InvestigatorAgent	Análise profunda de casos (jurisprudência, riscos, estratégias)
WriterAgent	Redação de resumos, briefings, petições
MaestroAgent	Orquestra workflow entre os 3 agentes acima
Providers (providers/):

ProviderManager — Seleção dinâmica de provider por prioridade com fallback automático
litellm_config.py — Abstração multi-provider (OpenAI, Anthropic, Google)
Workflows (workflows/):

morning_briefing.py — Briefing matinal automático para cada cliente
legal_translator.py — Tradução de juridiquês para linguagem leiga
7. app/workers/ — Workers Assíncronos (Taskiq)
Broker (broker.py): Redis-backed com logging e graceful shutdown

Tasks (tasks/):

Task	Função
embeddings.py	Geração de embeddings (text-embedding-3-small) para busca semântica
datajud_poller.py	Sincronização periódica (6h) com DataJud — batch, parse, detecção de prazos
lead_scoring.py	Recálculo de score via IA quando lead é criado/atualizado
chatwit_handlers.py	Processamento de webhooks Chatwit (novos leads, mensagens)
funnel_automations.py	Execução de automações de funil
Events (events/): Event bus via Redis Pub/Sub (LEAD_CREATED, LEAD_SCORED, CASE_MOVEMENT_DETECTED, etc.)

8. app/schemas/ — Schemas Pydantic
Validação de request/response para: auth, leads, clients, dashboard, audit, chatwit. Todos com Field validators (min/max length, ge/le, EmailStr, etc.)

9. Outros Módulos
Arquivo	Função
app/config.py	Settings via variáveis de ambiente
app/main.py	Entry point FastAPI, registro de routers e middleware
app/core/logging.py	structlog em JSON (prod) / colorido (dev)
app/core/metrics.py	Prometheus em /metrics
Padrões Arquiteturais Chave
Multi-tenant: Toda query filtrada por tenant_id automaticamente no repository
Async/await: Toda a stack (SQLAlchemy, httpx, Redis, Taskiq)
Repository Pattern: Abstração sobre SQLAlchemy com CRUD genérico
Event-Driven: Workers reagem a eventos via Redis Pub/Sub
IA com Fallback: Múltiplos providers LLM com seleção por prioridade
RBAC: 4 roles com permissões granulares no JWT