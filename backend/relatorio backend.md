# Relatório Completo do Backend - JusMonitorIA

O backend é uma aplicação **FastAPI modular multi-tenant** com arquitetura em camadas, utilizando **async/await** em toda a stack e integração de IA com múltiplos provedores.

---

## 1. app/api/v1/endpoints/ — Rotas HTTP

| Arquivo | Função |
| --- | --- |
| `auth.py` | Login (rate limited 5/min), refresh token, logout, GET /me |
| `leads.py` | CRUD de leads, máquina de estados, scoring por IA, histórico de funil |
| `clients.py` | CRUD de clientes, timeline, health score, notas com @mentions |
| `dashboard.py` | Casos urgentes, sem movimento, KPIs com tendências |
| `audit.py` | Listagem de logs de auditoria com filtros avançados |
| `websocket.py` | Canal de comunicação por tenant para atualizações em tempo real |
| `notifications.py` | Gerenciamento de notificações do sistema |

## 2. app/core/auth/ — Autenticação e Autorização

| Arquivo | Função |
| --- | --- |
| `jwt.py` | Geração/validação de JWT (access 30m, refresh 7d), RBAC (4 roles) |
| `dependencies.py` | Injeção de dependência: `get_current_user`, `get_tenant_id`, `get_db` |
| `password.py` | Hashing Bcrypt e verificação de segurança |

## 3. app/core/middleware/ — Middleware Global

| Arquivo | Função |
| --- | --- |
| `audit.py` | Captura IP e loga operações de escrita (POST/PUT/PATCH/DELETE) |
| `logging.py` | Log de request/response com métricas de tempo de execução |
| `metrics.py` | Exportação de métricas Prometheus (contadores, histogramas) |
| `rate_limit.py` | Limites: 100/min geral, 10/min IA, 5/min login |
| `security.py` | Headers de segurança (CSP, HSTS, X-Frame-Options) |
| `cache.py` | Implementação de Cache-Control e ETag |
| `shutdown.py` | Graceful shutdown com rastreio de conexões ativas |
| `compression.py` | Compressão GZip para respostas HTTP |

## 4. app/core/services/ — Serviços de Domínio

| Módulo | Função |
| --- | --- |
| `lead_state_machine.py` | Gerencia transições do funil (Novo → Convertido) com validação |
| `lead_scorer.py` | Cálculo 0-100 (Urgência 30%, Caso 25%, Engagement 25%, Dados 20%) |
| `funnel_automations.py` | Automações baseadas em score e inatividade |
| `timeline.py` | Agregador de eventos (movimentações, notas, mensagens) |
| `health_dashboard.py` | Score de saúde do cliente baseado em atividade e prazos |
| `datajud/` | Cliente API DataJud com rate limit e parser de movimentos |
| `search/semantic.py` | Busca semântica utilizando vetores `pgvector` |
| `audit_service.py` | Registro automático de estado anterior/posterior (diff) |
| `chatwit_client.py` | Integração com webhooks e tags do Chatwit |

## 5. app/db/ — Banco de Dados

### Base e Mixins (`base.py`)

* **UUIDMixin**: Identificadores únicos universais para PKs.
* **TimestampMixin**: Gestão automática de `created_at` e `updated_at`.
* **TenantMixin**: Isolamento de dados via `tenant_id`.
* **TenantBaseModel**: Modelo base consolidando os mixins acima.

### Modelos de Dados (`models/`)

| Modelo | Descrição |
| --- | --- |
| **Tenant** | Configuração do escritório (raiz multi-tenant) |
| **User** | Usuários e permissões (Admin, Lawyer, Assistant, Viewer) |
| **Lead** | Funil CRM com sumário de IA e estágio atual |
| **LegalCase** | Processos judiciais, tribunais e monitoramento de prazos |
| **CaseMovement** | Histórico DataJud com detecção automática de prazos |
| **TimelineEmbedding** | Vetores (1536 dims) para busca semântica em eventos |
| **AIProvider** | Configurações de LLM por tenant (OpenAI, Anthropic, Google) |

### Repositories e Engine

* **BaseRepository[T]**: CRUD genérico com injeção automática de filtro por tenant.
* **AsyncEngine**: Pool de 20 conexões + 10 de overflow para alta performance.

## 6. app/ai/ — Inteligência Artificial

### Agentes e Orquestração

* **TriageAgent**: Qualificação automática de leads.
* **InvestigatorAgent**: Análise de jurisprudência e riscos.
* **WriterAgent**: Redação de resumos e petições.
* **MaestroAgent**: Orquestrador dos workflows entre agentes.

### Provedores e Workflows

* **ProviderManager**: Seleção dinâmica e fallback automático (ex: OpenAI caiu → Anthropic).
* **Legal Translator**: Converte termos jurídicos complexos para linguagem leiga.

## 7. app/workers/ — Workers Assíncronos (Taskiq)

Utiliza **Redis** como broker para processamento em segundo plano:

| Task | Função |
| --- | --- |
| `embeddings.py` | Gera vetores para busca semântica em novas movimentações |
| `datajud_poller.py` | Sincronização periódica (6h) com tribunais e detecção de prazos |
| `lead_scoring.py` | Recálculo de score via LLM em eventos de lead |
| `chatwit_handlers.py` | Processamento de webhooks e integração de mensagens |

> **Event Bus:** Utiliza Redis Pub/Sub para eventos globais.

---

## Padrões Arquiteturais Chave

* **Isolamento Total**: Filtro de `tenant_id` em nível de repositório.
* **Performance**: Stack 100% assíncrona (SQLAlchemy 2.0, Taskiq, httpx).
* **Auditabilidade**: Log completo de "antes/depois" em todas as mutações.
* **Resiliência**: Fallback de IA multi-provider via LiteLLM.

