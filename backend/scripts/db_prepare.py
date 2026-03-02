#!/usr/bin/env python3
"""
Startup database preparation for JusMonitorIA.

Equivalent to the db-prepare.js pattern: run as part of the container
startup command BEFORE the application server launches.

Usage (in docker-compose command):
    python -m scripts.db_prepare && uvicorn app.main:app --host 0.0.0.0 --port 8000
    python -m scripts.db_prepare --mode=reset && uvicorn ...   # dev full reset

Tudo é automático — o script detecta o estado do banco e age de acordo:
  - Aguarda Postgres ficar pronto (retry automático)
  - Cria o database se não existir
  - Habilita pgvector
  - Roda alembic upgrade head
  - Seeds: só executa se o banco está vazio (primeiro boot)
  - TPU:   só sincroniza se as tabelas estiverem vazias

Nenhuma configuração manual necessária.

Variaveis de ambiente opcionais (valores padrão já são seguros):
    DB_PREPARE=no             Defina 'no' nos workers para pular tudo
    DB_PREPARE_MODE=reset     Só em dev: apaga e recria o banco
    DB_CONNECT_RETRIES=60     Max tentativas aguardando Postgres
    DB_CONNECT_SLEEP_S=2      Segundos entre tentativas
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse, urlunparse

# ── Make sure /app (backend root) is on the path ────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── Configuration ─────────────────────────────────────────────────────────────

def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _envint(key: str, default: int) -> int:
    try:
        return int(_env(key, str(default)))
    except ValueError:
        return default


def _arg(name: str, default: str) -> str:
    prefix = f"--{name}="
    for a in sys.argv[1:]:
        if a.startswith(prefix):
            return a[len(prefix):]
    return default


# deploy (default) = aplica migrações normalmente
# reset            = downgrade base → upgrade (só dev, bloqueado em produção)
MODE         = _arg("mode", _env("DB_PREPARE_MODE", "deploy"))

# workers definem DB_PREPARE=no para pular tudo
DB_PREPARE   = _env("DB_PREPARE", "yes").strip().lower()

RETRIES      = _envint("DB_CONNECT_RETRIES", 60)
SLEEP_S      = _envint("DB_CONNECT_SLEEP_S", 2)
DATABASE_URL = _env("DATABASE_URL")

# ── Colours ───────────────────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
CYAN   = "\033[36m"

def ok(msg: str)   -> None: print(f"{GREEN}✅{RESET} {msg}", flush=True)
def info(msg: str) -> None: print(f"{CYAN}ℹ️ {RESET} {msg}", flush=True)
def warn(msg: str) -> None: print(f"{YELLOW}⚠️ {RESET} {msg}", flush=True)
def err(msg: str)  -> None: print(f"{RED}❌{RESET} {msg}", flush=True)
def step(msg: str) -> None: print(f"\n{BOLD}{CYAN}══ {msg} ══{RESET}", flush=True)


# ── Database URL helpers ───────────────────────────────────────────────────────

def _parse_url(raw: str):
    """Parse DATABASE_URL (asyncpg or psycopg2 scheme) → components."""
    # Ensure it's a standard postgresql:// for urlparse
    url = raw.replace("postgresql+asyncpg://", "postgresql://") \
             .replace("postgresql+psycopg2://", "postgresql://")
    parsed = urlparse(url)
    return parsed


def _admin_url(raw: str) -> str:
    """
    Build admin URL pointing to the 'postgres' maintenance DB so we can
    CREATE DATABASE if it doesn't exist.
    """
    parsed = _parse_url(raw)
    # Replace database name with 'postgres'
    admin = parsed._replace(path="/postgres")
    return urlunparse(admin)


def _target_db(raw: str) -> str:
    parsed = _parse_url(raw)
    return parsed.path.lstrip("/")


def _sync_dsn(raw: str) -> str:
    """Return a plain postgresql:// URL (no +asyncpg) for asyncpg direct use."""
    return raw.replace("postgresql+asyncpg://", "postgresql://") \
              .replace("postgresql+psycopg2://", "postgresql://")


# ── Wait for Postgres ──────────────────────────────────────────────────────────

async def wait_for_postgres(dsn: str, label: str = "Postgres") -> None:
    """Retry connection until Postgres is ready. Exits process on timeout."""
    import asyncpg  # type: ignore

    info(f"Aguardando {label} ficar disponível (max {RETRIES}x, {SLEEP_S}s entre tentativas)...")
    last_err: Exception | None = None

    for attempt in range(1, RETRIES + 1):
        try:
            conn = await asyncpg.connect(dsn, timeout=5)
            await conn.close()
            ok(f"{label} disponível.")
            return
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            print(f"  ⏳ tentativa {attempt}/{RETRIES} — {exc}", flush=True)
            await asyncio.sleep(SLEEP_S)

    err(f"Não foi possível conectar ao {label} após {RETRIES} tentativas.")
    if last_err:
        err(str(last_err))
    sys.exit(1)


# ── Ensure database exists ────────────────────────────────────────────────────

async def ensure_database_exists(admin_dsn: str, db_name: str) -> None:
    """Create the target database if it doesn't exist."""
    import asyncpg  # type: ignore

    conn = await asyncpg.connect(admin_dsn, timeout=10)
    try:
        row = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )
        if row:
            ok(f"Database '{db_name}' já existe.")
            return

        info(f"Criando database '{db_name}'...")
        # asyncpg doesn't allow CREATE DATABASE inside a transaction
        await conn.execute(f'CREATE DATABASE "{db_name}"')
        ok(f"Database '{db_name}' criado.")
    except Exception as exc:
        msg = str(exc)
        if "already exists" in msg:
            ok(f"Database '{db_name}' já existe (concorrência).")
        elif "permission denied" in msg.lower():
            err("Sem permissão para CREATE DATABASE — crie manualmente ou use credenciais de superusuário.")
            raise
        else:
            raise
    finally:
        await conn.close()


# ── Ensure pgvector extension ─────────────────────────────────────────────────

async def ensure_pgvector(dsn: str) -> None:
    """Enable pgvector extension in the target database."""
    import asyncpg  # type: ignore

    conn = await asyncpg.connect(dsn, timeout=10)
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        row = await conn.fetchrow(
            "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
        )
        ver = row["extversion"] if row else "?"
        ok(f"Extensão pgvector habilitada (versão {ver}).")
    except Exception as exc:
        msg = str(exc)
        if "permission denied" in msg.lower():
            err("Permissão insuficiente para CREATE EXTENSION. Use superusuário ou fale com o DBA.")
        elif "could not open extension control file" in msg.lower():
            err("pgvector não está instalado neste Postgres (use a imagem pgvector/pgvector).")
        else:
            err(f"Falha ao habilitar pgvector: {msg}")
        raise
    finally:
        await conn.close()


# ── Postgres server info ───────────────────────────────────────────────────────

async def log_server_info(dsn: str) -> None:
    import asyncpg  # type: ignore

    try:
        conn = await asyncpg.connect(dsn, timeout=10)
        try:
            ver = await conn.fetchval("SHOW server_version")
            info(f"Postgres server_version: {ver}")
            row = await conn.fetchrow(
                "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
            )
            if row:
                info(f"pgvector extversion: {row['extversion']}")
            else:
                info("pgvector ainda não está instalada.")
        finally:
            await conn.close()
    except Exception:
        pass


# ── Alembic migrations ────────────────────────────────────────────────────────

def _run_alembic(*args: str) -> None:
    """Run alembic CLI from the backend directory."""
    cmd = ["alembic", *args]
    info(f"Executando: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ROOT), capture_output=False)
    if result.returncode != 0:
        err(f"alembic {' '.join(args)} falhou (exit {result.returncode})")
        sys.exit(1)


def run_migrations() -> None:
    if MODE == "reset":
        warn("Modo RESET — fazendo downgrade base (apaga todos os dados)...")
        _run_alembic("downgrade", "base")
        ok("Downgrade base concluído.")

    info("Rodando alembic upgrade head...")
    _run_alembic("upgrade", "head")
    ok("Migrações aplicadas.")


# ── Seeds ─────────────────────────────────────────────────────────────────────

async def is_first_boot(dsn: str) -> bool:
    """
    Retorna True se o banco foi recém-criado/migrado e ainda não tem nenhum
    tenant cadastrado. Usamos o slug '_platform' como marcador canônico de
    que os seeds já foram aplicados ao menos uma vez.

    NOTA: em produção com dados reais, esta função retorna False e os seeds
    são ignorados automaticamente no modo 'auto' (padrão).
    """
    import asyncpg  # type: ignore
    try:
        conn = await asyncpg.connect(dsn, timeout=10)
        try:
            row = await conn.fetchval(
                "SELECT 1 FROM tenants WHERE slug = '_platform' LIMIT 1"
            )
            return row is None  # None → não existe → primeiro boot
        finally:
            await conn.close()
    except Exception as exc:
        warn(f"Não foi possível verificar tenants: {exc} — assumindo primeiro boot.")
        return True


def _run_seed(module: str, label: str) -> None:
    """
    Executa um seed por subprocess.
    Os seeds são todos idempotentes (verificam existência antes de inserir),
    então é seguro rodá-los repetidamente — mas no modo 'auto' só chamamos
    no primeiro boot para evitar ruído nos logs de produção.
    """
    info(f"Rodando {label}...")
    result = subprocess.run(
        [sys.executable, "-m", module],
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        warn(f"{label} retornou erro (continuando — pode ser apenas dados já existentes).")
    else:
        ok(f"{label} pronto.")


async def run_seeds(target_dsn: str) -> None:
    """
    Roda seeds automaticamente — detecta o estado do banco e decide:
    - Banco vazio (primeiro boot) → executa todos os seeds
    - Banco já tem dados          → ignora silenciosamente
    Nenhuma configuração necessária.
    """
    first = await is_first_boot(target_dsn)
    if not first:
        ok("Banco já possui dados → seeds ignorados.")
        return

    info("Primeiro boot detectado → executando seeds iniciais.")
    _run_seed("scripts.create_super_admin", "Seed super admin + worker schedules")
    _run_seed("db.seeds.tenant", "Seed tenant demo (Amanda, Carlos, Marcos)")


# ── TPU auto-sync ─────────────────────────────────────────────────────────────

async def maybe_sync_tpu() -> None:
    """
    Verifica se as tabelas TPU estão vazias. Se sim, baixa classes e assuntos
    do CNJ agora (síncrono, antes do app subir) para que o campo Matéria
    já funcione na primeira requisição.
    """
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    engine = create_async_engine(DATABASE_URL, echo=False)
    try:
        async with engine.connect() as conn:
            count = await conn.scalar(text("SELECT COUNT(*) FROM tpu_assuntos"))
    except Exception as exc:
        warn(f"Não foi possível verificar tpu_assuntos: {exc} — pulando sync TPU.")
        return
    finally:
        await engine.dispose()

    if count and count > 0:
        ok(f"Tabelas TPU já populadas ({count} assuntos) — sync desnecessário.")
        return

    info("Tabelas TPU vazias — iniciando sync com CNJ (pode demorar ~15s)...")
    result = subprocess.run(
        [sys.executable, "-m", "scripts.sync_tpu"],
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        warn("Sync TPU retornou erro — o campo Matéria pode aparecer vazio.")
        warn("Rode manualmente: docker compose exec backend python -m scripts.sync_tpu")
    else:
        ok("Sync TPU concluído — classes e assuntos do CNJ disponíveis.")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    print(f"\n{BOLD}{'='*60}", flush=True)
    print(f"  🚀  db-prepare  (mode={MODE})", flush=True)
    print(f"{'='*60}{RESET}\n", flush=True)

    # ── Modo skip — workers não precisam reprocessar ──────────────────────────
    if DB_PREPARE == "no":
        info("DB_PREPARE=no → preparação de DB pulada (modo worker).")
        ok("Pronto.")
        return

    if not DATABASE_URL:
        err("DATABASE_URL não definida. Verifique o arquivo .env.")
        sys.exit(1)

    if MODE not in ("deploy", "reset"):
        err(f"Mode inválido: '{MODE}'. Use 'deploy' ou 'reset'.")
        sys.exit(1)

    if MODE == "reset" and _env("ENVIRONMENT", "development") == "production":
        err("Modo RESET bloqueado em ambiente de PRODUÇÃO. Use 'deploy'.")
        sys.exit(1)

    target_db  = _target_db(DATABASE_URL)
    target_dsn = _sync_dsn(DATABASE_URL)
    admin_dsn  = _admin_url(target_dsn)

    # ── 1. Aguarda Postgres ────────────────────────────────────────────────────
    step("1. Aguardando Postgres")
    await wait_for_postgres(admin_dsn, label="Postgres (admin)")

    # ── 2. Info do servidor ────────────────────────────────────────────────────
    step("2. Info do servidor")
    await log_server_info(admin_dsn)

    # ── 3. Cria database se necessário ────────────────────────────────────────
    step("3. Database")
    await ensure_database_exists(admin_dsn, target_db)

    # ── 4. pgvector ───────────────────────────────────────────────────────────
    step("4. pgvector")
    await ensure_pgvector(target_dsn)

    # ── 5. Migrações ──────────────────────────────────────────────────────────
    step("5. Migrações (Alembic)")
    run_migrations()

    # ── 6. Seeds (auto: só roda se banco está vazio) ──────────────────────────
    step("6. Seeds")
    await run_seeds(target_dsn)

    # ── 7. TPU sync (auto: só roda se tabelas estiverem vazias) ───────────────
    step("7. TPU (Classes e Assuntos CNJ)")
    await maybe_sync_tpu()

    # ── Pronto ─────────────────────────────────────────────────────────────────
    print(f"\n{BOLD}{GREEN}{'='*60}", flush=True)
    print(f"  🎉  Banco pronto! Iniciando aplicação...", flush=True)
    print(f"{'='*60}{RESET}\n", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
