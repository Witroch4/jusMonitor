#!/usr/bin/env bash
# =============================================================================
# build.sh - Build e Push de Imagens Docker para PRODUÇÃO (JusMonitor)
# =============================================================================
# Uso: ./build.sh [TAG] [--no-deploy] [--backend-only] [--frontend-only]
# =============================================================================

set -euo pipefail

IMAGE_FRONTEND="witrocha/jusmonitor-frontend"
IMAGE_BACKEND="witrocha/jusmonitor-backend"
STACK_NAME="jusmonitor"

# Portainer config (carrega de .env se existir)
if [ -f ".env" ] && grep -qE '^PORTAINER_' ".env" 2>/dev/null; then
  eval "$(grep -E '^PORTAINER_' ".env" | sed 's/^/export /')"
fi

PORTAINER_URL="${PORTAINER_URL:-}"
PORTAINER_API_KEY="${PORTAINER_API_KEY:-}"
PORTAINER_ENDPOINT_ID="${PORTAINER_ENDPOINT_ID:-1}"

# Cores
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

show_help() {
  cat << EOF
${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════╗
║        🚀  JusMonitor - Build & Push para Produção           ║
╚══════════════════════════════════════════════════════════════╝${NC}

${BOLD}Uso:${NC} ./build.sh [TAG] [opções]

${BOLD}Argumentos:${NC}
  TAG                Tag da imagem (default: latest)

${BOLD}Opções:${NC}
  --no-deploy        Pula o force-update dos serviços em produção
  --backend-only     Build apenas do backend
  --frontend-only    Build apenas do frontend
  --help, -h         Mostra esta ajuda

${BOLD}Exemplos:${NC}
  ./build.sh                     # Build tudo, push e deploy
  ./build.sh v1.0.0              # Build com tag v1.0.0
  ./build.sh --frontend-only     # Só frontend
  ./build.sh --no-deploy         # Só build e push, sem deploy

${BOLD}Deploy automático (Portainer):${NC}
  Defina no .env:
    PORTAINER_URL=https://portainer.witdev.com.br
    PORTAINER_API_KEY=ptr_xxxxxxxxxxxx
    PORTAINER_ENDPOINT_ID=1

${BOLD}Imagens:${NC}
  Frontend: ${IMAGE_FRONTEND}
  Backend:  ${IMAGE_BACKEND}
EOF
}

# =============================================================================
# Force-update de um serviço Swarm via Portainer Docker Proxy API
# =============================================================================
force_update_service() {
  local service_name="${STACK_NAME}_${1}"
  local image="${2}"

  echo -e "  ${BLUE}→${NC} Buscando serviço: ${service_name}..."

  local services_json
  services_json=$(curl -sf -H "X-API-Key: ${PORTAINER_API_KEY}" \
    "${PORTAINER_URL}/api/endpoints/${PORTAINER_ENDPOINT_ID}/docker/services?filters=%7B%22name%22%3A%5B%22${service_name}%22%5D%7D" \
    2>/dev/null) || {
    echo -e "  ${RED}✗${NC} Erro ao listar serviços. Verifique PORTAINER_URL e PORTAINER_API_KEY."
    return 1
  }

  local service_id version current_spec
  service_id=$(echo "${services_json}" | jq -r --arg name "${service_name}" \
    '.[] | select(.Spec.Name == $name) | .ID' 2>/dev/null)

  if [ -z "${service_id}" ] || [ "${service_id}" = "null" ]; then
    echo -e "  ${RED}✗${NC} Serviço '${service_name}' não encontrado no Swarm."
    return 1
  fi

  local service_detail
  service_detail=$(curl -sf -H "X-API-Key: ${PORTAINER_API_KEY}" \
    "${PORTAINER_URL}/api/endpoints/${PORTAINER_ENDPOINT_ID}/docker/services/${service_id}" \
    2>/dev/null) || {
    echo -e "  ${RED}✗${NC} Erro ao obter detalhes do serviço ${service_name}."
    return 1
  }

  version=$(echo "${service_detail}" | jq '.Version.Index')
  current_spec=$(echo "${service_detail}" | jq '.Spec')

  local updated_spec
  updated_spec=$(echo "${current_spec}" | jq \
    --arg img "${image}" \
    '.TaskTemplate.ForceUpdate = ((.TaskTemplate.ForceUpdate // 0) + 1) |
     .TaskTemplate.ContainerSpec.Image = $img')

  local http_code
  http_code=$(curl -sf -o /dev/null -w "%{http_code}" \
    -X POST \
    -H "X-API-Key: ${PORTAINER_API_KEY}" \
    -H "Content-Type: application/json" \
    "${PORTAINER_URL}/api/endpoints/${PORTAINER_ENDPOINT_ID}/docker/services/${service_id}/update?version=${version}" \
    -d "${updated_spec}" \
    2>/dev/null) || http_code="000"

  if [ "${http_code}" = "200" ]; then
    echo -e "  ${GREEN}✓${NC} ${service_name} → atualizado para ${image} (force-update)"
    return 0
  else
    echo -e "  ${RED}✗${NC} Falha ao atualizar ${service_name} (HTTP ${http_code})"
    return 1
  fi
}

# =============================================================================
# Parse Arguments
# =============================================================================
TAG="latest"
NO_DEPLOY=false
BUILD_FRONTEND=true
BUILD_BACKEND=true

for arg in "$@"; do
  case "${arg}" in
    help|--help|-h)   show_help; exit 0 ;;
    --no-deploy)      NO_DEPLOY=true ;;
    --frontend-only)  BUILD_BACKEND=false ;;
    --backend-only)   BUILD_FRONTEND=false ;;
    *)                TAG="${arg}" ;;
  esac
done

# Deploy possível?
CAN_DEPLOY=false
if [ "${NO_DEPLOY}" = false ] && [ -n "${PORTAINER_URL}" ] && [ -n "${PORTAINER_API_KEY}" ]; then
  CAN_DEPLOY=true
fi

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║${NC}  🚀 JusMonitor Build & Push — tag: ${BOLD}${TAG}${NC}"
if [ "${CAN_DEPLOY}" = true ]; then
  echo -e "${BOLD}${CYAN}║${NC}  🔄 Deploy automático: ${GREEN}ATIVO${NC}"
elif [ "${NO_DEPLOY}" = true ]; then
  echo -e "${BOLD}${CYAN}║${NC}  ⏭️  Deploy automático: ${YELLOW}DESATIVADO${NC} (--no-deploy)"
else
  echo -e "${BOLD}${CYAN}║${NC}  ⚠️  Deploy automático: ${YELLOW}SEM CONFIG${NC} (defina PORTAINER_URL)"
fi
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

STEP=0

# =============================================================================
# Build Frontend
# =============================================================================
if [ "${BUILD_FRONTEND}" = true ]; then
  STEP=$((STEP + 1))
  echo -e "==> [${STEP}] ${BOLD}Building frontend...${NC}"
  docker build \
    -f docker/frontend/Dockerfile.prod \
    --build-arg NEXT_PUBLIC_API_URL=https://jusmonitoria.witdev.com.br/api/v1 \
    -t "${IMAGE_FRONTEND}:latest" \
    .

  if [ "${TAG}" != "latest" ]; then
    docker tag "${IMAGE_FRONTEND}:latest" "${IMAGE_FRONTEND}:${TAG}"
  fi
  echo -e "  ${GREEN}✓${NC} Frontend build completo."
  echo ""

  STEP=$((STEP + 1))
  echo -e "==> [${STEP}] ${BOLD}Pushing frontend...${NC}"
  docker push "${IMAGE_FRONTEND}:latest"
  if [ "${TAG}" != "latest" ]; then
    docker push "${IMAGE_FRONTEND}:${TAG}"
  fi
  echo -e "  ${GREEN}✓${NC} Frontend push completo."
  echo ""
fi

# =============================================================================
# Build Backend
# =============================================================================
if [ "${BUILD_BACKEND}" = true ]; then
  STEP=$((STEP + 1))
  echo -e "==> [${STEP}] ${BOLD}Building backend...${NC}"
  docker build \
    -f docker/backend/Dockerfile.prod \
    -t "${IMAGE_BACKEND}:latest" \
    .

  if [ "${TAG}" != "latest" ]; then
    docker tag "${IMAGE_BACKEND}:latest" "${IMAGE_BACKEND}:${TAG}"
  fi
  echo -e "  ${GREEN}✓${NC} Backend build completo."
  echo ""

  STEP=$((STEP + 1))
  echo -e "==> [${STEP}] ${BOLD}Pushing backend...${NC}"
  docker push "${IMAGE_BACKEND}:latest"
  if [ "${TAG}" != "latest" ]; then
    docker push "${IMAGE_BACKEND}:${TAG}"
  fi
  echo -e "  ${GREEN}✓${NC} Backend push completo."
  echo ""
fi

# =============================================================================
# Deploy via Portainer
# =============================================================================
if [ "${CAN_DEPLOY}" = true ]; then
  echo "⌛ Aguardando 5s para propagação no registry..."
  sleep 5

  STEP=$((STEP + 1))
  echo ""
  echo -e "==> [${STEP}] ${BOLD}Force-update dos serviços em produção...${NC}"
  echo ""

  deploy_ok=0
  deploy_fail=0

  if [ "${BUILD_BACKEND}" = true ]; then
    if force_update_service "backend" "${IMAGE_BACKEND}:${TAG}"; then
      deploy_ok=$((deploy_ok + 1))
    else
      deploy_fail=$((deploy_fail + 1))
    fi
    if force_update_service "worker" "${IMAGE_BACKEND}:${TAG}"; then
      deploy_ok=$((deploy_ok + 1))
    else
      deploy_fail=$((deploy_fail + 1))
    fi
  fi

  if [ "${BUILD_FRONTEND}" = true ]; then
    if force_update_service "frontend" "${IMAGE_FRONTEND}:${TAG}"; then
      deploy_ok=$((deploy_ok + 1))
    else
      deploy_fail=$((deploy_fail + 1))
    fi
  fi

  echo ""
  if [ "${deploy_fail}" -eq 0 ]; then
    echo -e "  ${GREEN}🔄 Deploy: ${deploy_ok} serviço(s) atualizado(s) com sucesso${NC}"
  else
    echo -e "  ${YELLOW}⚠️  Deploy: ${deploy_ok} ok, ${deploy_fail} falha(s)${NC}"
  fi
fi

# =============================================================================
# Resumo
# =============================================================================
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║  ✅ Build & Push completo!                                   ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  📦 Imagens disponíveis:"
if [ "${BUILD_FRONTEND}" = true ]; then
  echo "     - ${IMAGE_FRONTEND}:latest"
  [ "${TAG}" != "latest" ] && echo "     - ${IMAGE_FRONTEND}:${TAG}"
fi
if [ "${BUILD_BACKEND}" = true ]; then
  echo "     - ${IMAGE_BACKEND}:latest"
  [ "${TAG}" != "latest" ] && echo "     - ${IMAGE_BACKEND}:${TAG}"
fi
echo ""
