#!/usr/bin/env bash
# =============================================================================
# dev.sh - Script para gerenciar o ambiente de desenvolvimento do JusMonitor
# =============================================================================
#
# Tudo roda em Docker. Basta executar:
#   ./dev.sh           → Sobe tudo (frontend, backend, worker, redis, postgres)
#
# E abrir: http://localhost:3000
#
# =============================================================================

set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Configurações
# ─────────────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ─────────────────────────────────────────────────────────────────────────────
# Funções auxiliares
# ─────────────────────────────────────────────────────────────────────────────
log_info()    { echo -e "${BLUE}ℹ${NC}  $1"; }
log_success() { echo -e "${GREEN}✔${NC}  $1"; }
log_warn()    { echo -e "${YELLOW}⚠${NC}  $1"; }
log_error()   { echo -e "${RED}✖${NC}  $1"; }
log_header()  { echo -e "\n${BOLD}${CYAN}═══ $1 ═══${NC}\n"; }

# Verifica dependências necessárias
check_dependencies() {
  local missing=()
  if ! command -v docker &> /dev/null; then missing+=("docker"); fi
  if ! docker compose version &> /dev/null 2>&1 && ! command -v docker-compose &> /dev/null; then
    missing+=("docker-compose")
  fi
  if [ ${#missing[@]} -gt 0 ]; then
    log_error "Dependências faltando: ${missing[*]}"
    exit 1
  fi
}

# Comando Docker Compose
dc() {
  if docker compose version &> /dev/null 2>&1; then
    docker compose -f "$COMPOSE_FILE" "$@"
  else
    docker-compose -f "$COMPOSE_FILE" "$@"
  fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Comandos Principais
# ─────────────────────────────────────────────────────────────────────────────

cmd_up() {
  log_header "Subindo ambiente de desenvolvimento"

  # Configura a trap para parar os containers graciosamente ao pressionar Ctrl+C
  trap 'echo -e "\n"; log_warn "Interrompido. Parando containers graciosamente..."; dc stop; log_success "Containers parados."; exit 0' INT

  # Sobe containers
  dc up -d
  log_info "Aguardando serviços iniciarem..."
  sleep 3

  print_urls
  log_info "Exibindo logs (Ctrl+C para PARAR os containers graciosamente)..."

  # Exibe os logs e aguarda
  dc logs -f --tail=100
}

cmd_down() {
  log_header "Parando ambiente"
  dc down
  log_success "Ambiente parado."
}

cmd_restart() {
  log_header "Reiniciando ambiente"
  dc restart
  log_success "Ambiente reiniciado."
}

cmd_logs() {
  local service="${1:-}"
  dc logs -f --tail=200 $service
}

print_urls() {
  echo ""
  log_success "Ambiente de desenvolvimento pronto!"
  echo ""
  echo -e "  ${BOLD}${GREEN}URLs:${NC}"
  echo -e "  ${CYAN}🌐 Frontend${NC}        → ${BOLD}http://localhost:3000${NC}"
  echo -e "  ${CYAN}🔌 Backend API${NC}     → ${BOLD}http://localhost:8000${NC}"
  echo -e "  ${CYAN}📖 Swagger Docs${NC}    → ${BOLD}http://localhost:8000/docs${NC}"
  echo ""
  echo -e "  ${BOLD}Infraestrutura:${NC}"
  echo -e "  ${CYAN}🐘 PostgreSQL${NC}    → localhost:5433"
  echo -e "  ${CYAN}🔴 Redis${NC}         → localhost:6380"
  echo ""
  echo -e "  ${BOLD}Comandos úteis:${NC}"
  echo -e "    ./dev.sh logs              Ver logs de todos os serviços"
  echo -e "    ./dev.sh logs backend      Ver logs apenas do backend"
  echo -e "    ./dev.sh down              Parar tudo"
  echo -e "    ./dev.sh build             Rebuild das imagens docker"
  echo -e "    ./dev.sh clean             Remover containers e volumes de banco"
  echo ""
}

cmd_build() {
  log_header "Rebuildando imagens"
  dc build
  log_success "Imagens criadas."
}

cmd_clean() {
  log_header "Limpeza completa"
  log_warn "Isso vai PARAR os containers e REMOVER os volumes de banco (PostgreSQL/Redis)!"
  read -p "Tem certeza? (y/N): " confirm
  if [[ "$confirm" =~ ^[Yy]$ ]]; then
    dc down -v --remove-orphans
    log_success "Containers parados e volumes removidos."
  else
    log_info "Operação cancelada."
  fi
}

cmd_help() {
  echo -e "${BOLD}${CYAN}"
  echo "╔══════════════════════════════════════════════════════════════╗"
  echo "║          🚀  JusMonitor - Dev Environment                    ║"
  echo "╚══════════════════════════════════════════════════════════════╝"
  echo -e "${NC}"
  echo -e "  ${BOLD}Uso:${NC} ./dev.sh [comando]"
  echo ""
  echo -e "  ${BOLD}Comandos principais:${NC}"
  echo -e "    ${GREEN}(sem argumento)${NC}   Sobe e segue logs. Ctrl+C *para* os containers graciosamente"
  echo -e "    ${GREEN}down${NC}              Para todos os containers"
  echo -e "    ${GREEN}restart${NC}           Reinicia todos os containers"
  echo -e "    ${GREEN}logs [serviço]${NC}    Mostra logs e 'prende' a tela"
  echo -e "    ${GREEN}build${NC}             Rebuild das imagens do compose.yml"
  echo -e "    ${GREEN}clean${NC}             Remove containers + volumes (APAGA DE VEZ O BD)"
  echo ""
}

# ─────────────────────────────────────────────────────────────────────────────
# Execução
# ─────────────────────────────────────────────────────────────────────────────

check_dependencies

case "${1:-}" in
  up)       cmd_up ;;
  down)     cmd_down ;;
  restart)  cmd_restart ;;
  logs)     shift; cmd_logs "$@" ;;
  build)    cmd_build ;;
  clean)    cmd_clean ;;
  help|-h|--help) cmd_help ;;
  "")       cmd_up ;;
  *)
    log_error "Comando desconhecido: $1"
    cmd_help
    exit 1
    ;;
esac
