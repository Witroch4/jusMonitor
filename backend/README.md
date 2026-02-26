# JusMonitor Backend

Backend API para o sistema JusMonitor CRM Orquestrador.

## Stack Tecnológica

- **Python 3.12+**
- **FastAPI** - Framework web assíncrono
- **SQLAlchemy 2.0** - ORM com suporte async
- **PostgreSQL 17** - Banco de dados com pgvector
- **Redis** - Cache e message broker
- **Taskiq** - Sistema de filas assíncronas
- **LangGraph + LiteLLM** - Orquestração de IA

## Requisitos

- Python 3.12+
- Poetry 1.7+
- PostgreSQL 17 com extensão pgvector
- Redis 7+

## Instalação

### Usando Poetry (desenvolvimento local)

```bash
# Instalar dependências
poetry install

# Ativar ambiente virtual
poetry shell

# Copiar arquivo de configuração
cp .env.example .env

# Editar .env com suas configurações
nano .env
```

### Usando Docker (recomendado)

```bash
# A partir do diretório raiz do projeto
docker-compose up -d
```

## Desenvolvimento

### Rodar servidor de desenvolvimento

```bash
# Com Poetry
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Ou usando o script
poetry run dev
```

### Migrations do banco de dados

```bash
# Criar nova migration
poetry run alembic revision --autogenerate -m "descrição da mudança"

# Aplicar migrations
poetry run alembic upgrade head

# Reverter última migration
poetry run alembic downgrade -1
```

### Testes

```bash
# Rodar todos os testes
poetry run pytest

# Com cobertura
poetry run pytest --cov=app --cov-report=html

# Testes específicos
poetry run pytest tests/unit/
poetry run pytest tests/integration/
poetry run pytest tests/property/
```

### Linting e formatação

```bash
# Ruff (linting)
poetry run ruff check .
poetry run ruff check . --fix

# Black (formatação)
poetry run black .

# MyPy (type checking)
poetry run mypy app/

# Isort (ordenar imports)
poetry run isort .
```

## Estrutura do Projeto

```
backend/
├── app/
│   ├── api/              # Endpoints da API
│   ├── core/             # Lógica de negócio
│   ├── db/               # Modelos e repositórios
│   ├── workers/          # Workers Taskiq
│   ├── ai/               # Agentes de IA
│   ├── schemas/          # Schemas Pydantic
│   └── config.py         # Configurações
├── tests/                # Testes
├── alembic/              # Migrations
└── pyproject.toml        # Dependências
```

## Variáveis de Ambiente

Veja `.env.example` para lista completa de variáveis de ambiente necessárias.

Principais:
- `DATABASE_URL` - URL de conexão do PostgreSQL
- `REDIS_URL` - URL de conexão do Redis
- `SECRET_KEY` - Chave secreta da aplicação
- `JWT_SECRET_KEY` - Chave para assinatura de tokens JWT
- `OPENAI_API_KEY` - Chave da API OpenAI (para embeddings e IA)

## API Documentation

Após iniciar o servidor, acesse:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Workers Taskiq

Para rodar workers em desenvolvimento:

```bash
poetry run taskiq worker app.workers.broker:broker
```

## Licença

Proprietário - JusMonitor
