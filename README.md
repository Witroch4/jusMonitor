# JusMonitorIA - CRM Orquestrador

Sistema multi-tenant de gestão jurídica que integra CRM, monitoramento processual automatizado e inteligência artificial para escritórios de advocacia.

## 🚀 Visão Geral

O JusMonitorIA orquestra a comunicação entre clientes (via Chatwit), monitoramento de processos (DataJud) e agentes de IA especializados para automatizar triagem, investigação e redação de documentos jurídicos.

### Principais Funcionalidades

- **Multi-tenancy**: Isolamento completo de dados entre escritórios de advocacia
- **Funil Inteligente**: Gestão de leads com qualificação automática por IA e drag-and-drop
- **Prontuário 360º**: Visão completa do cliente com timeline unificada e health score
- **Central Operacional**: Dashboard com briefing matinal e classificação de urgência (Urgente, Atenção, Boas Notícias, Ruído)
- **Monitoramento Automático**: Sincronização com DataJud respeitando rate limits (100 processos/lote, distribuído em 6 horas)
- **4 Agentes de IA**: Triagem, Investigador, Redator e Maestro (orquestrador)
- **Busca Semântica**: Embeddings vetoriais com pgvector para encontrar processos similares
- **Notificações em Tempo Real**: WebSocket para atualizações instantâneas
- **Automações Personalizadas**: Briefing matinal, alertas urgentes e resumos semanais por cliente

## 🏗️ Arquitetura

### Stack Tecnológica

**Backend:**
- **Framework**: Python 3.12+ com FastAPI (async)
- **ORM**: SQLAlchemy 2.0 (async) com suporte a PostgreSQL
- **Database**: PostgreSQL 17 com extensão pgvector para embeddings
- **Cache/Queue**: Redis 7+ para cache, sessões e filas
- **Task Queue**: Taskiq para processamento assíncrono (embeddings, sync DataJud, notificações)
- **IA**: LangGraph para orquestração de agentes + LiteLLM para roteamento multi-provider
- **Validação**: Pydantic v2 para schemas e validação de dados
- **Testes**: pytest + pytest-asyncio + hypothesis (property-based testing)

**Frontend:**
- **Framework**: Next.js 16 com App Router e React Server Components
- **Linguagem**: TypeScript 5+
- **Estilização**: Tailwind CSS + Shadcn/UI para componentes
- **Estado**: React Query (server state) + Zustand (client state)
- **Validação**: Zod para schemas
- **Real-time**: WebSocket para notificações instantâneas
- **Drag-and-Drop**: dnd-kit para Kanban do funil

**Infraestrutura:**
- **Containerização**: Docker + Docker Compose
- **Database**: PostgreSQL 17 com pgvector extension
- **Cache**: Redis 7 para cache, sessões e backend do Taskiq
- **Observabilidade**: Structured logging (structlog) + Prometheus metrics

### Integrações Externas

- **Chatwit**: Comunicação omnichannel (WhatsApp, Instagram, Facebook, etc.)
  - Webhooks para receber mensagens e eventos
  - API para enviar mensagens e gerenciar tags
  - Rate limit: 100 req/min
  
- **DataJud**: API oficial do CNJ para consulta de processos judiciais
  - Autenticação via certificado digital
  - Rate limit: 100 req/hora (1 req/36s)
  - Batching: 100 processos por lote, distribuído em 6 horas
  
- **Provedores de IA**: OpenAI, Anthropic, Google (via LiteLLM)
  - Fallback automático entre provedores
  - Modelos: GPT-4 Turbo, Claude 3 Opus, Gemini Pro
  - Embeddings: text-embedding-3-small (OpenAI)

### Arquitetura de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Dashboard │  │  Funil   │  │Prontuário│  │ Central  │   │
│  │          │  │  Kanban  │  │   360º   │  │Operacional│   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│         │              │              │              │       │
│         └──────────────┴──────────────┴──────────────┘       │
│                         │                                     │
│                    REST API + WebSocket                      │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────┐
│                    Backend API (FastAPI)                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Middleware: Tenant Isolation + Auth + Rate Limit    │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Auth    │  │  Leads   │  │ Clients  │  │Processes │  │
│  │Endpoints │  │Endpoints │  │Endpoints │  │Endpoints │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │Dashboard │  │ Timeline │  │ Webhooks │  │  Health  │  │
│  │Endpoints │  │Endpoints │  │ Handler  │  │  Checks  │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼────────┐ ┌──────▼──────┐ ┌───────▼────────┐
│   PostgreSQL   │ │    Redis    │ │ Taskiq Workers │
│   + pgvector   │ │             │ │                │
│                │ │  - Cache    │ │ - Embeddings   │
│ - Tenants      │ │  - Sessions │ │ - DataJud Sync │
│ - Users        │ │  - Queue    │ │ - AI Agents    │
│ - Leads        │ │  - Pub/Sub  │ │ - Notifications│
│ - Clients      │ └─────────────┘ └────────┬───────┘
│ - Processes    │                          │
│ - Movements    │                          │
│ - Embeddings   │                          │
└────────────────┘                          │
                                            │
                    ┌───────────────────────┴────────────┐
                    │                                    │
            ┌───────▼────────┐              ┌───────────▼──────────┐
            │  AI Providers  │              │ External Integrations│
            │                │              │                      │
            │ - OpenAI       │              │ - Chatwit API        │
            │ - Anthropic    │              │ - DataJud API        │
            │ - Google       │              │                      │
            └────────────────┘              └──────────────────────┘
```

### Fluxo de Dados Principal

1. **Recebimento de Mensagem (Chatwit)**:
   - Webhook recebe evento → Valida assinatura → Publica no event bus
   - Worker processa → Cria/atualiza lead → Agente Triagem analisa
   - Calcula score → Atualiza funil → Notifica usuário via WebSocket

2. **Monitoramento de Processos (DataJud)**:
   - Scheduler agenda consultas a cada 6 horas
   - Worker busca processos ativos → Agrupa em lotes de 100
   - Distribui requisições respeitando rate limit (1 req/36s)
   - Detecta novas movimentações → Gera embeddings assíncronos
   - Agente Investigador classifica urgência → Cria evento na timeline
   - Notifica usuário se urgente

3. **Briefing Matinal**:
   - Scheduler dispara às 8h para cada tenant
   - Agente Maestro orquestra: busca movimentações 24h → classifica em 4 blocos
   - Agente Redator gera resumos → Salva briefing no banco
   - Dashboard carrega briefing → Exibe na Central Operacional

4. **Conversão de Lead**:
   - Usuário arrasta lead no Kanban → Frontend valida transição
   - API atualiza estado → Publica evento → Worker cria cliente
   - Associa processos → Ativa automações → Envia mensagem de boas-vindas

## 📦 Instalação e Setup

### Pré-requisitos

- **Docker** 24+ e **Docker Compose** 2.20+
- **Python** 3.12+ (para desenvolvimento local)
- **Node.js** 20+ e **npm** 10+ (para desenvolvimento local)
- **Poetry** 1.7+ (gerenciador de dependências Python)
- **Git** para controle de versão

### Quick Start com Docker (Recomendado)

Este é o método mais rápido para rodar o sistema completo:

```bash
# 1. Clonar o repositório
git clone <repository-url>
cd jusmonitoria

# 2. Configurar variáveis de ambiente
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local

# 3. Editar arquivos .env com suas credenciais
# Mínimo necessário para rodar localmente:
# - DATABASE_URL (já configurado para Docker)
# - REDIS_URL (já configurado para Docker)
# - SECRET_KEY (gerar com: openssl rand -hex 32)
# - JWT_SECRET_KEY (gerar com: openssl rand -hex 32)
# - OPENAI_API_KEY (obter em https://platform.openai.com)

nano backend/.env  # ou use seu editor preferido

# 4. Iniciar todos os serviços (PostgreSQL, Redis, Backend, Frontend)
docker-compose up -d

# 5. Aguardar serviços iniciarem (verificar logs)
docker-compose logs -f backend

# 6. Aplicar migrations do banco de dados
docker-compose exec backend alembic upgrade head

# 7. (Opcional) Popular banco com dados de demonstração
docker-compose exec backend python -m cli.seed --all

# 8. Acessar a aplicação
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs (Swagger): http://localhost:8000/docs
# API Docs (ReDoc): http://localhost:8000/redoc

# Login padrão (após seed):
# Email: admin@demo.com
# Senha: admin123
```

### Comandos Docker Úteis

```bash
# Ver logs de todos os serviços
docker-compose logs -f

# Ver logs de um serviço específico
docker-compose logs -f backend
docker-compose logs -f frontend

# Parar todos os serviços
docker-compose down

# Parar e remover volumes (CUIDADO: apaga dados do banco)
docker-compose down -v

# Reconstruir imagens após mudanças no código
docker-compose up -d --build

# Executar comando no container backend
docker-compose exec backend <comando>

# Executar comando no container frontend
docker-compose exec frontend <comando>

# Acessar shell do container
docker-compose exec backend bash
docker-compose exec frontend sh

# Ver status dos serviços
docker-compose ps

# Reiniciar um serviço específico
docker-compose restart backend
```

### Desenvolvimento Local (Sem Docker)

Para desenvolvimento com hot-reload e debugging:

#### 1. Configurar PostgreSQL e Redis

Você precisa ter PostgreSQL 17 e Redis 7 rodando localmente:

```bash
# Opção 1: Usar Docker apenas para banco e cache
docker-compose up -d postgres redis

# Opção 2: Instalar nativamente (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql-17 postgresql-contrib redis-server

# Habilitar extensão pgvector no PostgreSQL
sudo -u postgres psql -c "CREATE EXTENSION vector;"
```

#### 2. Configurar Backend

```bash
cd backend

# Instalar Poetry (se não tiver)
curl -sSL https://install.python-poetry.org | python3 -

# Instalar dependências
poetry install

# Ativar ambiente virtual
poetry shell

# Configurar variáveis de ambiente
cp .env.example .env
nano .env

# Ajustar URLs para localhost:
# DATABASE_URL=postgresql+asyncpg://jusmonitoria:jusmonitoria_dev_password@localhost:5432/jusmonitoria
# REDIS_URL=redis://localhost:6379/0

# Criar banco de dados
createdb jusmonitoria

# Aplicar migrations
alembic upgrade head

# (Opcional) Popular com dados de teste
python -m cli.seed --all

# Iniciar servidor de desenvolvimento (com hot-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Em outro terminal, iniciar workers Taskiq
poetry shell
taskiq worker app.workers.broker:broker --reload
```

#### 3. Configurar Frontend

```bash
cd frontend

# Instalar dependências
npm install

# Configurar variáveis de ambiente
cp .env.example .env.local
nano .env.local

# Ajustar URL da API:
# NEXT_PUBLIC_API_URL=http://localhost:8000

# Iniciar servidor de desenvolvimento (com hot-reload)
npm run dev

# Frontend estará disponível em http://localhost:3000
```

### Configuração de Variáveis de Ambiente

#### Backend (.env)

Variáveis **obrigatórias** para funcionamento básico:

```bash
# Segurança (GERAR NOVAS CHAVES!)
SECRET_KEY=<gerar-com-openssl-rand-hex-32>
JWT_SECRET_KEY=<gerar-com-openssl-rand-hex-32>

# Database
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname

# Redis
REDIS_URL=redis://host:6379/0

# IA (pelo menos um provider)
OPENAI_API_KEY=sk-...
```

Variáveis **opcionais** (mas recomendadas):

```bash
# Integrações externas
CHATWIT_API_KEY=<sua-chave>
CHATWIT_WEBHOOK_SECRET=<seu-secret>
DATAJUD_API_KEY=<sua-chave>
DATAJUD_CERT_PATH=/path/to/cert.pem

# Provedores de IA adicionais (fallback)
ANTHROPIC_API_KEY=<sua-chave>
GOOGLE_API_KEY=<sua-chave>

# Email (para notificações)
SMTP_HOST=smtp.gmail.com
SMTP_USER=seu-email@gmail.com
SMTP_PASSWORD=<senha-app>

# Monitoramento
SENTRY_DSN=<seu-dsn>
```

Veja `backend/.env.example` para lista completa com descrições.

#### Frontend (.env.local)

```bash
# URL da API backend
NEXT_PUBLIC_API_URL=http://localhost:8000

# (Opcional) Outras configurações
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

### Troubleshooting

#### Erro: "Connection refused" ao conectar no banco

```bash
# Verificar se PostgreSQL está rodando
docker-compose ps postgres
# ou
sudo systemctl status postgresql

# Verificar logs
docker-compose logs postgres

# Recriar container
docker-compose down
docker-compose up -d postgres
```

#### Erro: "Extension vector not found"

```bash
# Instalar extensão pgvector
docker-compose exec postgres psql -U jusmonitoria -d jusmonitoria -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

#### Erro: "Module not found" no backend

```bash
# Reinstalar dependências
cd backend
poetry install --no-root

# Verificar ambiente virtual ativo
poetry shell
```

#### Erro: "Cannot find module" no frontend

```bash
# Limpar cache e reinstalar
cd frontend
rm -rf node_modules .next
npm install
npm run dev
```

#### Workers Taskiq não processam tarefas

```bash
# Verificar se Redis está acessível
redis-cli ping

# Verificar logs do worker
docker-compose logs -f backend

# Reiniciar workers
docker-compose restart backend
```

## 🗂️ Estrutura do Projeto

```
jusmonitoria/
├── backend/                    # API FastAPI + Workers
│   ├── app/
│   │   ├── api/               # Camada de API REST
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/ # Endpoints por recurso
│   │   │   │   │   ├── auth.py          # Login, refresh token
│   │   │   │   │   ├── clients.py       # CRUD de clientes
│   │   │   │   │   ├── leads.py         # CRUD de leads
│   │   │   │   │   ├── processes.py     # CRUD de processos
│   │   │   │   │   ├── dashboard.py     # Central Operacional
│   │   │   │   │   ├── timeline.py      # Timeline de eventos
│   │   │   │   │   └── webhooks.py      # Webhooks Chatwit
│   │   │   │   ├── dependencies.py      # Injeção de dependências
│   │   │   │   └── router.py            # Router principal
│   │   │   └── middleware/               # Middlewares
│   │   │       ├── tenant.py             # Isolamento multi-tenant
│   │   │       ├── auth.py               # Autenticação JWT
│   │   │       └── rate_limit.py         # Rate limiting
│   │   │
│   │   ├── core/              # Lógica de Negócio (Clean Architecture)
│   │   │   ├── domain/        # Entidades e Value Objects
│   │   │   │   ├── entities/
│   │   │   │   │   ├── client.py
│   │   │   │   │   ├── lead.py
│   │   │   │   │   └── process.py
│   │   │   │   └── value_objects/
│   │   │   │       ├── cpf.py
│   │   │   │       └── cnj_number.py
│   │   │   ├── use_cases/     # Casos de uso
│   │   │   │   ├── create_client.py
│   │   │   │   ├── convert_lead.py
│   │   │   │   └── sync_process.py
│   │   │   └── services/      # Serviços de domínio
│   │   │       ├── chatwit_service.py
│   │   │       ├── datajud_service.py
│   │   │       └── ai_service.py
│   │   │
│   │   ├── db/                # Camada de Dados
│   │   │   ├── models/        # Modelos SQLAlchemy
│   │   │   │   ├── base.py              # Base model
│   │   │   │   ├── tenant.py            # Tenants
│   │   │   │   ├── user.py              # Usuários
│   │   │   │   ├── client.py            # Clientes
│   │   │   │   ├── lead.py              # Leads
│   │   │   │   ├── legal_case.py        # Processos
│   │   │   │   ├── case_movement.py     # Movimentações
│   │   │   │   ├── timeline_event.py    # Eventos timeline
│   │   │   │   ├── ai_provider.py       # Config IA
│   │   │   │   └── audit_log.py         # Logs de auditoria
│   │   │   ├── repositories/  # Repositories (padrão Repository)
│   │   │   │   ├── base.py              # Base repository
│   │   │   │   ├── client_repository.py
│   │   │   │   ├── lead_repository.py
│   │   │   │   └── process_repository.py
│   │   │   └── session.py     # Configuração de sessão async
│   │   │
│   │   ├── workers/           # Taskiq Workers (processamento assíncrono)
│   │   │   ├── broker.py                # Configuração do broker
│   │   │   ├── embeddings_worker.py     # Geração de embeddings
│   │   │   ├── datajud_worker.py        # Sync com DataJud
│   │   │   ├── ai_worker.py             # Processamento IA
│   │   │   └── notification_worker.py   # Envio de notificações
│   │   │
│   │   ├── ai/                # Camada de IA (LangGraph + LiteLLM)
│   │   │   ├── agents/        # Agentes especializados
│   │   │   │   ├── base_agent.py
│   │   │   │   ├── triagem_agent.py     # Qualificação de leads
│   │   │   │   ├── investigador_agent.py # Análise de processos
│   │   │   │   ├── redator_agent.py     # Geração de textos
│   │   │   │   └── maestro_agent.py     # Orquestrador
│   │   │   ├── graphs/        # Grafos LangGraph
│   │   │   │   ├── briefing_graph.py
│   │   │   │   └── lead_qualification_graph.py
│   │   │   ├── prompts/       # Templates de prompts
│   │   │   │   └── templates.py
│   │   │   └── providers/     # Roteamento de providers
│   │   │       └── router.py
│   │   │
│   │   ├── schemas/           # Schemas Pydantic (validação)
│   │   │   ├── client.py
│   │   │   ├── lead.py
│   │   │   ├── process.py
│   │   │   ├── webhook.py
│   │   │   └── ai.py
│   │   │
│   │   ├── config.py          # Configurações da aplicação
│   │   └── main.py            # Entry point FastAPI
│   │
│   ├── tests/                 # Testes
│   │   ├── unit/              # Testes unitários
│   │   ├── integration/       # Testes de integração
│   │   └── property/          # Property-based tests (Hypothesis)
│   │
│   ├── alembic/               # Migrations do banco
│   │   ├── versions/          # Arquivos de migration
│   │   └── env.py             # Configuração Alembic
│   │
│   ├── cli/                   # CLI tools
│   │   └── seed.py            # Comando para popular dados
│   │
│   ├── .env.example           # Exemplo de variáveis de ambiente
│   ├── pyproject.toml         # Dependências Poetry
│   ├── Dockerfile             # Imagem Docker
│   └── README.md              # Documentação do backend
│
├── frontend/                  # App Next.js 16
│   ├── app/                   # App Router (Next.js 16)
│   │   ├── (auth)/            # Grupo de rotas de autenticação
│   │   │   ├── login/
│   │   │   │   └── page.tsx   # Página de login
│   │   │   └── layout.tsx     # Layout de auth
│   │   │
│   │   ├── (dashboard)/       # Grupo de rotas do dashboard
│   │   │   ├── dashboard/
│   │   │   │   └── page.tsx   # Central Operacional
│   │   │   ├── funil/
│   │   │   │   └── page.tsx   # Kanban de leads
│   │   │   ├── clientes/
│   │   │   │   ├── page.tsx   # Lista de clientes
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx # Prontuário 360º
│   │   │   ├── processos/
│   │   │   │   ├── page.tsx   # Lista de processos
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx # Detalhes do processo
│   │   │   └── layout.tsx     # Layout com sidebar
│   │   │
│   │   ├── api/               # API Routes (Next.js)
│   │   │   └── webhooks/
│   │   │       └── route.ts   # Webhook receiver
│   │   │
│   │   ├── layout.tsx         # Root layout
│   │   └── page.tsx           # Landing page
│   │
│   ├── components/            # Componentes React
│   │   ├── ui/                # Componentes Shadcn/UI
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   └── ...
│   │   ├── dashboard/         # Componentes do dashboard
│   │   │   ├── urgent-cases.tsx
│   │   │   ├── attention-cases.tsx
│   │   │   ├── good-news.tsx
│   │   │   └── metrics.tsx
│   │   ├── funil/             # Componentes do funil
│   │   │   ├── kanban-board.tsx
│   │   │   ├── lead-card.tsx
│   │   │   └── lead-modal.tsx
│   │   ├── prontuario/        # Componentes do prontuário
│   │   │   ├── overview.tsx
│   │   │   ├── timeline.tsx
│   │   │   ├── processes.tsx
│   │   │   └── automations.tsx
│   │   └── layout/            # Componentes de layout
│   │       ├── sidebar.tsx
│   │       └── header.tsx
│   │
│   ├── lib/                   # Utilitários e configurações
│   │   ├── api-client.ts      # Cliente HTTP (axios)
│   │   ├── auth.ts            # Funções de autenticação
│   │   ├── websocket.ts       # Cliente WebSocket
│   │   └── utils.ts           # Funções auxiliares
│   │
│   ├── actions/               # Server Actions (Next.js)
│   │   ├── client-actions.ts
│   │   ├── lead-actions.ts
│   │   └── process-actions.ts
│   │
│   ├── hooks/                 # Custom React Hooks
│   │   ├── use-auth.ts        # Hook de autenticação
│   │   ├── use-realtime.ts    # Hook de WebSocket
│   │   └── use-tenant.ts      # Hook de tenant
│   │
│   ├── types/                 # TypeScript types
│   │   └── index.ts
│   │
│   ├── .env.example           # Exemplo de variáveis de ambiente
│   ├── package.json           # Dependências npm
│   ├── tsconfig.json          # Configuração TypeScript
│   ├── tailwind.config.ts     # Configuração Tailwind
│   ├── next.config.ts         # Configuração Next.js
│   └── README.md              # Documentação do frontend
│
├── docker/                    # Dockerfiles customizados
│   ├── backend/
│   │   └── Dockerfile
│   ├── frontend/
│   │   └── Dockerfile
│   └── postgres/
│       └── init.sql           # Script de inicialização do banco
│
├── scripts/                   # Scripts de automação
│   ├── dev.sh                 # Iniciar ambiente de desenvolvimento
│   ├── test.sh                # Rodar todos os testes
│   ├── migrate.sh             # Aplicar migrations
│   └── seed.sh                # Popular banco com dados
│
├── docs/                      # Documentação adicional
│   ├── architecture.md        # Arquitetura detalhada
│   ├── api.md                 # Documentação da API
│   └── deployment.md          # Guia de deploy
│
├── .gitignore                 # Arquivos ignorados pelo Git
├── .dockerignore              # Arquivos ignorados pelo Docker
├── docker-compose.yml         # Orquestração de serviços
├── README.md                  # Este arquivo
└── CONTRIBUTING.md            # Guia de contribuição
```

### Convenções de Código

**Backend (Python):**
- PEP 8 para estilo de código
- Type hints obrigatórios
- Docstrings em formato Google
- Imports organizados: stdlib → third-party → local
- Nomes: `snake_case` para funções/variáveis, `PascalCase` para classes

**Frontend (TypeScript):**
- ESLint + Prettier para formatação
- Componentes em `PascalCase`
- Hooks em `camelCase` com prefixo `use`
- Tipos em `PascalCase` com sufixo `Type` ou `Interface`
- Server Components por padrão, Client Components quando necessário

## 🧪 Testes

O projeto utiliza uma estratégia de testes em múltiplas camadas para garantir qualidade e confiabilidade.

### Backend

#### Tipos de Testes

1. **Testes Unitários** (`tests/unit/`): Testam funções e classes isoladamente
2. **Testes de Integração** (`tests/integration/`): Testam interação entre componentes
3. **Property-Based Tests** (`tests/property/`): Testam propriedades universais com Hypothesis

#### Executar Testes

```bash
cd backend

# Todos os testes
poetry run pytest

# Com cobertura de código
poetry run pytest --cov=app --cov-report=html --cov-report=term

# Apenas testes unitários
poetry run pytest tests/unit/

# Apenas testes de integração
poetry run pytest tests/integration/

# Apenas property-based tests
poetry run pytest tests/property/

# Testes específicos
poetry run pytest tests/unit/test_auth.py
poetry run pytest tests/unit/test_auth.py::test_create_token

# Modo verbose
poetry run pytest -v

# Parar no primeiro erro
poetry run pytest -x

# Rodar em paralelo (mais rápido)
poetry run pytest -n auto

# Ver print statements
poetry run pytest -s
```

#### Cobertura de Código

```bash
# Gerar relatório HTML
poetry run pytest --cov=app --cov-report=html

# Abrir relatório no navegador
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

#### Escrever Testes

```python
# tests/unit/test_example.py
import pytest
from app.core.services.example_service import ExampleService

@pytest.fixture
def example_service():
    return ExampleService()

def test_example_function(example_service):
    result = example_service.do_something("input")
    assert result == "expected_output"

# Property-based test
from hypothesis import given, strategies as st

@given(st.text())
def test_property_always_returns_string(input_text):
    result = example_service.process(input_text)
    assert isinstance(result, str)
```

### Frontend

```bash
cd frontend

# Linting (verificar erros de código)
npm run lint

# Linting com auto-fix
npm run lint:fix

# Formatação com Prettier
npm run format

# Verificar tipos TypeScript
npm run type-check
```

### Testes E2E (End-to-End)

```bash
# Instalar Playwright (primeira vez)
cd frontend
npx playwright install

# Rodar testes E2E
npm run test:e2e

# Rodar em modo UI (interativo)
npm run test:e2e:ui

# Rodar apenas em um navegador
npm run test:e2e -- --project=chromium
```

### CI/CD

Os testes são executados automaticamente em cada push/PR via GitHub Actions:

- Testes unitários e de integração do backend
- Linting e type-checking do frontend
- Verificação de cobertura de código (mínimo 80%)
- Testes E2E em ambiente staging

## 📚 Documentação da API

### Swagger UI (Interativo)

Acesse http://localhost:8000/docs para explorar e testar todos os endpoints da API de forma interativa.

### ReDoc (Documentação Estática)

Acesse http://localhost:8000/redoc para visualização em formato de documentação tradicional.

### Principais Endpoints

#### Autenticação

```bash
# Login
POST /api/v1/auth/login
Body: { "email": "user@example.com", "password": "senha123" }
Response: { "access_token": "...", "refresh_token": "...", "token_type": "bearer" }

# Refresh Token
POST /api/v1/auth/refresh
Body: { "refresh_token": "..." }

# Logout
POST /api/v1/auth/logout
Headers: Authorization: Bearer <token>
```

#### Leads

```bash
# Listar leads
GET /api/v1/leads?stage=novo&limit=20&offset=0
Headers: Authorization: Bearer <token>

# Criar lead
POST /api/v1/leads
Body: { "full_name": "João Silva", "phone": "+5511999999999", "source": "chatwit" }

# Atualizar estágio do lead
PATCH /api/v1/leads/{lead_id}/stage
Body: { "stage": "qualificado" }

# Converter lead em cliente
POST /api/v1/leads/{lead_id}/convert
```

#### Clientes

```bash
# Listar clientes
GET /api/v1/clients?status=active&limit=20

# Obter prontuário 360º
GET /api/v1/clients/{client_id}

# Timeline do cliente
GET /api/v1/clients/{client_id}/timeline?limit=50

# Health score do cliente
GET /api/v1/clients/{client_id}/health

# Configurar automações
PUT /api/v1/clients/{client_id}/automations
Body: { "briefing_matinal": true, "alertas_urgentes": true }
```

#### Processos

```bash
# Listar processos
GET /api/v1/processes?client_id={id}&monitoring_enabled=true

# Criar processo
POST /api/v1/processes
Body: { "cnj_number": "0000000-00.0000.0.00.0000", "client_id": "...", "court": "TJSP" }

# Sincronizar com DataJud (manual)
POST /api/v1/processes/{process_id}/sync

# Movimentações do processo
GET /api/v1/processes/{process_id}/movements?limit=50
```

#### Dashboard (Central Operacional)

```bash
# Casos urgentes
GET /api/v1/dashboard/urgent

# Casos que precisam atenção
GET /api/v1/dashboard/attention

# Boas notícias
GET /api/v1/dashboard/good-news

# Ruído (movimentações irrelevantes)
GET /api/v1/dashboard/noise

# Métricas do escritório
GET /api/v1/dashboard/metrics?period=30d
```

#### Webhooks

```bash
# Receber webhook do Chatwit
POST /webhooks/chatwit
Headers: X-Chatwit-Signature: <hmac-signature>
Body: { "event_type": "message.received", "contact": {...}, "message": {...} }
```

### Autenticação

Todos os endpoints (exceto `/auth/login` e webhooks) requerem autenticação via JWT:

```bash
# Incluir header em todas as requisições
Authorization: Bearer <access_token>

# Incluir tenant_id (extraído automaticamente do token)
X-Tenant-ID: <tenant_uuid>
```

### Rate Limiting

- **Endpoints gerais**: 100 requisições/minuto por IP
- **Endpoints de IA**: 10 requisições/minuto por tenant
- **Login**: 5 tentativas/minuto por IP

Quando o limite é excedido, a API retorna `429 Too Many Requests` com header `Retry-After`.

### Paginação

Endpoints de listagem suportam paginação:

```bash
GET /api/v1/clients?limit=20&offset=40

Response:
{
  "items": [...],
  "total": 150,
  "limit": 20,
  "offset": 40,
  "has_more": true
}
```

### Filtros e Ordenação

```bash
# Filtros
GET /api/v1/leads?stage=qualificado&source=chatwit&score_min=70

# Ordenação
GET /api/v1/clients?sort_by=created_at&sort_order=desc

# Busca
GET /api/v1/clients?search=João Silva
```

### Códigos de Status HTTP

- `200 OK`: Sucesso
- `201 Created`: Recurso criado
- `204 No Content`: Sucesso sem corpo de resposta
- `400 Bad Request`: Dados inválidos
- `401 Unauthorized`: Não autenticado
- `403 Forbidden`: Sem permissão
- `404 Not Found`: Recurso não encontrado
- `409 Conflict`: Conflito (ex: duplicata)
- `422 Unprocessable Entity`: Validação falhou
- `429 Too Many Requests`: Rate limit excedido
- `500 Internal Server Error`: Erro no servidor

### Documentação Adicional

- **Backend README**: [backend/README.md](backend/README.md) - Detalhes técnicos do backend
- **Frontend README**: [frontend/README.md](frontend/README.md) - Detalhes técnicos do frontend
- **Guia de Contribuição**: [CONTRIBUTING.md](CONTRIBUTING.md) - Como contribuir com o projeto

## 🔐 Segurança

### Práticas de Segurança Implementadas

- **Autenticação JWT**: Tokens com expiração e refresh tokens
- **Isolamento Multi-Tenant**: Filtro automático por tenant_id em todas as queries
- **Rate Limiting**: Proteção contra abuso de API (100 req/min geral, 10 req/min IA)
- **Validação de Schemas**: Pydantic (backend) e Zod (frontend) para validação rigorosa
- **CORS Configurável**: Whitelist de origens permitidas
- **Headers de Segurança**: CSP, HSTS, X-Frame-Options, X-Content-Type-Options
- **Sanitização de Inputs**: Proteção contra XSS e SQL Injection
- **Senhas Hasheadas**: bcrypt com salt para armazenamento seguro
- **HTTPS Only**: Forçar HTTPS em produção
- **Audit Logs**: Registro de todas as operações sensíveis

### Configurações de Segurança

```python
# backend/app/config.py
CORS_ORIGINS = ["https://app.jusmonitoria.com"]  # Apenas origens confiáveis
CORS_ALLOW_CREDENTIALS = True

# Headers de segurança
SECURITY_HEADERS = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'"
}

# Rate limiting
RATE_LIMIT_PER_MINUTE = 100
RATE_LIMIT_AI_PER_MINUTE = 10
```

### Checklist de Segurança para Produção

- [ ] Gerar novas chaves secretas (`SECRET_KEY`, `JWT_SECRET_KEY`)
- [ ] Configurar CORS apenas para domínios confiáveis
- [ ] Habilitar HTTPS com certificado válido
- [ ] Configurar firewall para bloquear portas não utilizadas
- [ ] Usar secrets manager para credenciais (AWS Secrets Manager, Vault)
- [ ] Habilitar backups automáticos do banco de dados
- [ ] Configurar monitoramento de segurança (Sentry, CloudWatch)
- [ ] Implementar rotação de tokens JWT
- [ ] Revisar permissões de usuários e roles
- [ ] Configurar WAF (Web Application Firewall)
- [ ] Habilitar 2FA para usuários admin
- [ ] Realizar scan de vulnerabilidades (OWASP ZAP, Snyk)

### Reportar Vulnerabilidades

Se você descobrir uma vulnerabilidade de segurança, por favor **NÃO** abra uma issue pública. Envie um email para security@jusmonitoria.com com:

- Descrição da vulnerabilidade
- Passos para reproduzir
- Impacto potencial
- Sugestões de correção (se houver)

Responderemos em até 48 horas.

## 🚦 Health Checks e Monitoramento

### Endpoints de Health Check

```bash
# Liveness probe (verifica se aplicação está rodando)
curl http://localhost:8000/health/live
Response: { "status": "ok" }

# Readiness probe (verifica se aplicação está pronta para receber tráfego)
curl http://localhost:8000/health/ready
Response: {
  "status": "ok",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "chatwit_api": "ok",
    "datajud_api": "ok"
  }
}
```

### Métricas Prometheus

```bash
# Endpoint de métricas
curl http://localhost:8000/metrics

# Métricas disponíveis:
# - http_requests_total: Total de requisições HTTP
# - http_request_duration_seconds: Duração das requisições
# - http_requests_in_progress: Requisições em andamento
# - leads_created_total: Total de leads criados
# - leads_converted_total: Total de leads convertidos
# - processes_synced_total: Total de processos sincronizados
# - ai_requests_total: Total de requisições para IA
# - ai_request_duration_seconds: Duração das requisições IA
```

### Logs Estruturados

Os logs são emitidos em formato JSON estruturado para facilitar parsing:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "logger": "app.api.v1.endpoints.leads",
  "message": "Lead created successfully",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "660e8400-e29b-41d4-a716-446655440000",
  "request_id": "abc123",
  "lead_id": "770e8400-e29b-41d4-a716-446655440000"
}
```

### Audit Logs

Todas as operações importantes são registradas em audit logs:

```bash
# Consultar audit logs
GET /api/v1/audit-logs?entity_type=client&entity_id={id}&limit=50

Response: {
  "items": [
    {
      "id": "...",
      "action": "update",
      "entity_type": "client",
      "entity_id": "...",
      "user_id": "...",
      "old_values": { "status": "active" },
      "new_values": { "status": "inactive" },
      "ip_address": "192.168.1.1",
      "created_at": "2024-01-15T10:30:45Z"
    }
  ]
}
```

### Monitoramento em Produção

Para produção, recomendamos integrar com:

- **Prometheus + Grafana**: Métricas e dashboards
- **Sentry**: Rastreamento de erros
- **ELK Stack** ou **Loki**: Agregação de logs
- **Uptime Robot**: Monitoramento de disponibilidade

## 🔧 Comandos Úteis

### Gerenciamento do Banco de Dados

```bash
# Criar nova migration
cd backend
alembic revision --autogenerate -m "Descrição da mudança"

# Aplicar migrations
alembic upgrade head

# Reverter última migration
alembic downgrade -1

# Ver histórico de migrations
alembic history

# Ver SQL de uma migration sem aplicar
alembic upgrade head --sql

# Resetar banco (CUIDADO: apaga todos os dados)
docker-compose down -v
docker-compose up -d postgres
alembic upgrade head
```

### Popular Banco com Dados de Teste

```bash
# Popular tudo (tenant, usuários, leads, clientes, processos)
docker-compose exec backend python -m cli.seed --all

# Popular apenas tenant e usuários
docker-compose exec backend python -m cli.seed --tenant

# Popular apenas CRM (leads e clientes)
docker-compose exec backend python -m cli.seed --crm

# Popular apenas processos e movimentações
docker-compose exec backend python -m cli.seed --cases

# Popular configurações de IA
docker-compose exec backend python -m cli.seed --ai

# Resetar e popular novamente
docker-compose exec backend python -m cli.seed --all --reset
```

### Gerenciamento de Dependências

```bash
# Backend (Poetry)
cd backend
poetry add <pacote>              # Adicionar dependência
poetry add --group dev <pacote>  # Adicionar dependência de dev
poetry remove <pacote>           # Remover dependência
poetry update                    # Atualizar todas as dependências
poetry show                      # Listar dependências instaladas
poetry export -f requirements.txt --output requirements.txt  # Gerar requirements.txt

# Frontend (npm)
cd frontend
npm install <pacote>             # Adicionar dependência
npm install --save-dev <pacote>  # Adicionar dependência de dev
npm uninstall <pacote>           # Remover dependência
npm update                       # Atualizar dependências
npm outdated                     # Ver dependências desatualizadas
npm audit                        # Verificar vulnerabilidades
npm audit fix                    # Corrigir vulnerabilidades
```

### Linting e Formatação

```bash
# Backend
cd backend
poetry run ruff check .          # Verificar erros de linting
poetry run ruff check --fix .    # Corrigir automaticamente
poetry run black .               # Formatar código
poetry run mypy app/             # Verificar tipos

# Frontend
cd frontend
npm run lint                     # Verificar erros de linting
npm run lint:fix                 # Corrigir automaticamente
npm run format                   # Formatar com Prettier
npm run type-check               # Verificar tipos TypeScript
```

### Logs e Debugging

```bash
# Ver logs em tempo real
docker-compose logs -f

# Ver logs de um serviço específico
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
docker-compose logs -f redis

# Ver últimas 100 linhas
docker-compose logs --tail=100 backend

# Acessar shell do container
docker-compose exec backend bash
docker-compose exec frontend sh
docker-compose exec postgres psql -U jusmonitoria -d jusmonitoria

# Executar comando Python no backend
docker-compose exec backend python -c "from app.db.session import engine; print(engine)"

# Acessar Redis CLI
docker-compose exec redis redis-cli
```

### Performance e Otimização

```bash
# Analisar queries lentas do PostgreSQL
docker-compose exec postgres psql -U jusmonitoria -d jusmonitoria -c "
  SELECT query, mean_exec_time, calls 
  FROM pg_stat_statements 
  ORDER BY mean_exec_time DESC 
  LIMIT 10;
"

# Ver conexões ativas no banco
docker-compose exec postgres psql -U jusmonitoria -d jusmonitoria -c "
  SELECT count(*) FROM pg_stat_activity;
"

# Limpar cache do Redis
docker-compose exec redis redis-cli FLUSHALL

# Ver uso de memória do Redis
docker-compose exec redis redis-cli INFO memory

# Ver tamanho do banco de dados
docker-compose exec postgres psql -U jusmonitoria -d jusmonitoria -c "
  SELECT pg_size_pretty(pg_database_size('jusmonitoria'));
"
```

### Backup e Restore

```bash
# Backup do banco de dados
docker-compose exec postgres pg_dump -U jusmonitoria jusmonitoria > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore do banco de dados
docker-compose exec -T postgres psql -U jusmonitoria jusmonitoria < backup_20240115_103045.sql

# Backup com compressão
docker-compose exec postgres pg_dump -U jusmonitoria jusmonitoria | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Restore de backup comprimido
gunzip -c backup_20240115_103045.sql.gz | docker-compose exec -T postgres psql -U jusmonitoria jusmonitoria
```

### Produção

```bash
# Build para produção
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d

# Ver status dos serviços
docker-compose -f docker-compose.prod.yml ps

# Escalar workers
docker-compose -f docker-compose.prod.yml up -d --scale backend-worker=4

# Ver uso de recursos
docker stats
```

## 📈 Performance e Escalabilidade

### Otimizações Implementadas

**Backend:**
- Connection pooling do PostgreSQL (20 conexões, max overflow 10)
- Cache Redis para queries frequentes (TTL 5 minutos)
- Índices otimizados no banco (compostos, GIN, HNSW para vetores)
- Queries assíncronas com SQLAlchemy async
- Processamento em background com Taskiq
- Batching de embeddings (50 por lote)
- Rate limiting distribuído com Redis

**Frontend:**
- React Server Components para renderização no servidor
- Lazy loading de componentes
- Infinite scroll para listas longas
- Debouncing em campos de busca
- Optimistic updates para melhor UX
- Cache de queries com React Query (stale-while-revalidate)

**Database:**
- Índices HNSW para busca vetorial (pgvector)
- Particionamento de tabelas grandes (audit_logs por mês)
- Vacuum automático configurado
- Índices parciais para queries filtradas

### Benchmarks

Em ambiente de teste (Docker local, 4 CPU, 8GB RAM):

- **API Response Time**: p50 < 50ms, p95 < 200ms, p99 < 500ms
- **Dashboard Load**: < 1s para carregar todos os blocos
- **Busca Semântica**: < 100ms para 10k vetores
- **Sync DataJud**: 100 processos em ~60 minutos (respeitando rate limit)
- **Geração de Embeddings**: 50 textos em ~5s

### Escalabilidade

**Horizontal Scaling:**
- Backend API: Stateless, pode escalar horizontalmente com load balancer
- Workers Taskiq: Adicionar mais workers conforme necessidade
- Frontend: Deploy em CDN (Vercel, Cloudflare)

**Vertical Scaling:**
- PostgreSQL: Aumentar CPU/RAM para queries complexas
- Redis: Aumentar memória para cache maior

**Limites Recomendados por Instância:**
- Backend API: ~1000 req/s (4 CPU, 8GB RAM)
- Workers: ~100 tarefas/min (2 CPU, 4GB RAM)
- PostgreSQL: ~10k processos, ~1M movimentações (8 CPU, 16GB RAM)

### Monitoramento de Performance

```bash
# Ver métricas de performance
curl http://localhost:8000/metrics | grep http_request_duration

# Queries lentas (> 1s)
docker-compose exec postgres psql -U jusmonitoria -d jusmonitoria -c "
  SELECT query, mean_exec_time, calls 
  FROM pg_stat_statements 
  WHERE mean_exec_time > 1000
  ORDER BY mean_exec_time DESC;
"

# Cache hit ratio do Redis
docker-compose exec redis redis-cli INFO stats | grep keyspace
```

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor, leia o [Guia de Contribuição](CONTRIBUTING.md) antes de enviar um Pull Request.

### Processo de Contribuição

1. **Fork** o repositório
2. **Clone** seu fork: `git clone https://github.com/seu-usuario/jusmonitoria.git`
3. **Crie uma branch** para sua feature: `git checkout -b feature/minha-feature`
4. **Faça suas alterações** seguindo os padrões de código
5. **Escreva testes** para suas alterações
6. **Execute os testes**: `poetry run pytest` (backend) e `npm run lint` (frontend)
7. **Commit** suas mudanças: `git commit -m 'feat: adiciona nova funcionalidade'`
8. **Push** para sua branch: `git push origin feature/minha-feature`
9. **Abra um Pull Request** descrevendo suas alterações

### Padrões de Commit

Seguimos [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` Nova funcionalidade
- `fix:` Correção de bug
- `docs:` Alterações na documentação
- `style:` Formatação, ponto e vírgula, etc (sem mudança de código)
- `refactor:` Refatoração de código
- `test:` Adição ou correção de testes
- `chore:` Tarefas de manutenção, dependências, etc

Exemplos:
```
feat: adiciona endpoint de busca semântica
fix: corrige cálculo de score de leads
docs: atualiza README com instruções de deploy
test: adiciona testes para agente de triagem
```

### Code Review

Todos os PRs passam por code review. Verificamos:

- ✅ Código segue padrões do projeto
- ✅ Testes estão passando
- ✅ Cobertura de código mantida (mínimo 80%)
- ✅ Documentação atualizada
- ✅ Sem vulnerabilidades de segurança
- ✅ Performance não degradada

## 📝 Licença

Este projeto é proprietário e confidencial. Todos os direitos reservados © 2024 JusMonitorIA.

Uso não autorizado, cópia, modificação ou distribuição deste software é estritamente proibido.

## 👥 Equipe

**JusMonitorIA Team**

- Product Owner: [Nome]
- Tech Lead: [Nome]
- Backend Developers: [Nomes]
- Frontend Developers: [Nomes]
- DevOps: [Nome]
- QA: [Nome]

## 📞 Suporte e Contato

### Suporte Técnico

- **Email**: suporte@jusmonitoria.com
- **Slack**: #jusmonitoria-support (interno)
- **Documentação**: https://docs.jusmonitoria.com
- **Status Page**: https://status.jusmonitoria.com

### Reportar Bugs

Abra uma issue no GitHub com:
- Descrição clara do problema
- Passos para reproduzir
- Comportamento esperado vs atual
- Screenshots (se aplicável)
- Versão do sistema
- Logs relevantes

### Solicitar Features

Abra uma issue com label `enhancement`:
- Descrição da funcionalidade
- Caso de uso / problema que resolve
- Mockups ou exemplos (se aplicável)
- Prioridade sugerida

## 🗺️ Roadmap

### Q1 2024
- [x] MVP com funcionalidades core
- [x] Integração Chatwit e DataJud
- [x] 4 Agentes de IA
- [ ] Deploy em produção
- [ ] Onboarding de primeiros clientes

### Q2 2024
- [ ] App mobile (React Native)
- [ ] Integração com e-SAJ
- [ ] Relatórios avançados com BI
- [ ] API pública para integrações

### Q3 2024
- [ ] Agente de IA para redação de petições
- [ ] Integração com PJe
- [ ] Marketplace de integrações
- [ ] Suporte a múltiplos idiomas

### Q4 2024
- [ ] Análise preditiva com ML
- [ ] Automação de processos (RPA)
- [ ] Certificação ISO 27001
- [ ] Expansão internacional

## 📚 Recursos Adicionais

### Documentação

- [Arquitetura Detalhada](docs/architecture.md)
- [Guia de Deploy](docs/deployment.md)
- [API Reference](docs/api.md)
- [Guia de Contribuição](CONTRIBUTING.md)

### Tutoriais

- [Como criar um novo agente de IA](docs/tutorials/create-ai-agent.md)
- [Como adicionar um novo endpoint](docs/tutorials/create-endpoint.md)
- [Como configurar ambiente de desenvolvimento](docs/tutorials/dev-setup.md)

### Links Úteis

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Taskiq Documentation](https://taskiq-python.github.io/)

---

**Desenvolvido com ❤️ pela equipe JusMonitorIA**
