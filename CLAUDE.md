# CLAUDE.md

SEU NOME É JAVISThis file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
se for solicitado pra navehgar use sempre MCP Tool:
playwright / browser_navigate
## Project Overview

JusMonitor is a multi-tenant legal case management and AI-powered automation platform for law firms. The UI and docs are in Portuguese. It has a FastAPI backend and Next.js frontend, orchestrated with Docker Compose.

## Architecture

**Backend** (`/backend/`) — Python 3.12+, FastAPI, SQLAlchemy (async) + asyncpg, PostgreSQL 17 with pgvector, Redis 7, Alembic migrations, Taskiq async workers, LangGraph AI agents with LiteLLM multi-provider routing.

**Frontend** (`/frontend/`) — Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS, Shadcn/UI (Radix), React Query, Zustand, React Hook Form + Zod.

**Key backend layers:**
- `app/api/v1/endpoints/` — Route handlers
- `app/core/services/` — Domain services
- `app/db/models/` and `app/db/repositories/` — Repository pattern over SQLAlchemy
- `app/ai/agents/` — LangGraph agents (triagem, investigador, redator, maestro)
- `app/workers/` — Taskiq async workers (embeddings, datajud, ai, notifications)
- `app/schemas/` — Pydantic request/response schemas

**Key frontend structure:**
- `app/(auth)/` and `app/(dashboard)/` — Route groups (auth vs authenticated)
- `components/ui/` — Shadcn/UI base components
- `lib/api-client.ts` — Axios HTTP client
- `lib/websocket.ts` — WebSocket client
- `hooks/` — Custom React hooks
- `types/` — TypeScript type definitions
- Path alias: `@/*` maps to frontend root

## Development Commands

### Full stack (Docker)
```bash
./dev.sh                    # Start all services (postgres, redis, backend, worker, frontend)
docker compose up -d        # Alternative: start detached
```
Services: frontend at :3000, backend API at :8000, Swagger docs at :8000/docs

### Backend (local)
```bash
cd backend
poetry install
poetry shell
alembic upgrade head                          # Run migrations
uvicorn app.main:app --reload                 # Start API server
taskiq worker app.workers.main:broker --reload  # Start async workers
```

### Frontend (local)
```bash
cd frontend
npm install
npm run dev          # Dev server at :3000
npm run build        # Production build
```

### Database migrations
```bash
cd backend
alembic revision --autogenerate -m "description"   # Create migration
alembic upgrade head                                # Apply migrations
# Or via Docker:
docker compose exec backend alembic upgrade head
```

### Seeding
```bash
./scripts/seed.sh --all          # Seed all data
./scripts/seed.sh --tenant       # Seed tenants only
./scripts/seed.sh --crm          # Seed CRM data
```

### Testing
```bash
# Backend
cd backend
poetry run pytest                                    # All tests
poetry run pytest tests/unit/                        # Unit tests only
poetry run pytest tests/integration/                 # Integration tests
poetry run pytest --cov=app --cov-report=html        # With coverage (80% min)
poetry run pytest tests/unit/test_foo.py::test_bar   # Single test

# Frontend E2E
cd frontend
npx playwright test                  # Run all E2E tests
npx playwright test --ui             # Interactive UI mode
npx playwright test path/to/test.ts  # Single test file
```

### Linting & Formatting
```bash
# Backend
poetry run ruff check .     # Lint
poetry run black .          # Format
poetry run mypy app/        # Type check

# Frontend
npm run lint                # ESLint
npm run format              # Prettier
```

## Key Conventions

- Backend uses async/await throughout (async SQLAlchemy, asyncpg, httpx)
- Multi-tenant: all queries are tenant-scoped
- JWT authentication with refresh tokens
- Real-time updates via WebSocket at `/ws`
- AI agents use LiteLLM for provider-agnostic LLM calls with fallback support
- Backend logging: structlog (structured JSON logs)
- Backend metrics: Prometheus via `/metrics`
- Docker networking: `backend-net` (API + workers + frontend), `db-net` (API + workers + DB)
- PostgreSQL exposed on port 5433 (not default 5432), Redis on 6380
