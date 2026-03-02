#!/bin/bash

# JusMonitorIA - Script de Testes
# Executa todos os testes do projeto (backend e frontend)

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para imprimir mensagens coloridas
print_info() {
    echo -e "${BLUE}ℹ ${1}${NC}"
}

print_success() {
    echo -e "${GREEN}✓ ${1}${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ ${1}${NC}"
}

print_error() {
    echo -e "${RED}✗ ${1}${NC}"
}

# Banner
echo -e "${BLUE}"
cat << "EOF"
  _____         _            
 |_   _|__  ___| |_ ___  ___ 
   | |/ _ \/ __| __/ _ \/ __|
   | |  __/\__ \ ||  __/\__ \
   |_|\___||___/\__\___||___/
                              
EOF
echo -e "${NC}"

# Variáveis
BACKEND_FAILED=0
FRONTEND_FAILED=0
COVERAGE_THRESHOLD=80

# Parse argumentos
RUN_BACKEND=1
RUN_FRONTEND=1
RUN_COVERAGE=0
RUN_UNIT=0
RUN_INTEGRATION=0
RUN_PROPERTY=0
VERBOSE=0

while [[ $# -gt 0 ]]; do
    case $1 in
        --backend-only)
            RUN_FRONTEND=0
            shift
            ;;
        --frontend-only)
            RUN_BACKEND=0
            shift
            ;;
        --coverage)
            RUN_COVERAGE=1
            shift
            ;;
        --unit)
            RUN_UNIT=1
            shift
            ;;
        --integration)
            RUN_INTEGRATION=1
            shift
            ;;
        --property)
            RUN_PROPERTY=1
            shift
            ;;
        -v|--verbose)
            VERBOSE=1
            shift
            ;;
        -h|--help)
            echo "Uso: $0 [opções]"
            echo ""
            echo "Opções:"
            echo "  --backend-only      Executar apenas testes do backend"
            echo "  --frontend-only     Executar apenas testes do frontend"
            echo "  --coverage          Gerar relatório de cobertura"
            echo "  --unit              Executar apenas testes unitários"
            echo "  --integration       Executar apenas testes de integração"
            echo "  --property          Executar apenas property-based tests"
            echo "  -v, --verbose       Modo verbose"
            echo "  -h, --help          Mostrar esta ajuda"
            exit 0
            ;;
        *)
            print_error "Opção desconhecida: $1"
            exit 1
            ;;
    esac
done

# Verificar se Docker está rodando
if ! docker info > /dev/null 2>&1; then
    print_error "Docker não está rodando. Por favor, inicie o Docker primeiro."
    exit 1
fi

# ============================================
# TESTES DO BACKEND
# ============================================

if [ $RUN_BACKEND -eq 1 ]; then
    echo ""
    print_info "=========================================="
    print_info "EXECUTANDO TESTES DO BACKEND"
    print_info "=========================================="
    echo ""

    # Verificar se container backend existe
    if ! docker-compose ps backend | grep -q "Up"; then
        print_warning "Container backend não está rodando. Iniciando..."
        docker-compose up -d postgres redis
        sleep 3
    fi

    # Construir comando pytest
    PYTEST_CMD="pytest"
    
    if [ $VERBOSE -eq 1 ]; then
        PYTEST_CMD="$PYTEST_CMD -v"
    fi

    if [ $RUN_COVERAGE -eq 1 ]; then
        PYTEST_CMD="$PYTEST_CMD --cov=app --cov-report=html --cov-report=term --cov-fail-under=$COVERAGE_THRESHOLD"
    fi

    # Selecionar tipo de teste
    if [ $RUN_UNIT -eq 1 ]; then
        PYTEST_CMD="$PYTEST_CMD tests/unit/"
    elif [ $RUN_INTEGRATION -eq 1 ]; then
        PYTEST_CMD="$PYTEST_CMD tests/integration/"
    elif [ $RUN_PROPERTY -eq 1 ]; then
        PYTEST_CMD="$PYTEST_CMD tests/property/"
    fi

    # Executar testes
    print_info "Executando: $PYTEST_CMD"
    echo ""

    if docker-compose run --rm backend $PYTEST_CMD; then
        print_success "Testes do backend passaram!"
    else
        print_error "Testes do backend falharam!"
        BACKEND_FAILED=1
    fi

    # Mostrar localização do relatório de cobertura
    if [ $RUN_COVERAGE -eq 1 ]; then
        echo ""
        print_info "Relatório de cobertura gerado em: backend/htmlcov/index.html"
        print_info "Para visualizar: open backend/htmlcov/index.html (macOS) ou xdg-open backend/htmlcov/index.html (Linux)"
    fi
fi

# ============================================
# TESTES DO FRONTEND
# ============================================

if [ $RUN_FRONTEND -eq 1 ]; then
    echo ""
    print_info "=========================================="
    print_info "EXECUTANDO TESTES DO FRONTEND"
    print_info "=========================================="
    echo ""

    # Linting
    print_info "Executando linting..."
    if docker-compose run --rm frontend npm run lint; then
        print_success "Linting passou!"
    else
        print_error "Linting falhou!"
        FRONTEND_FAILED=1
    fi

    echo ""

    # Type checking
    print_info "Verificando tipos TypeScript..."
    if docker-compose run --rm frontend npm run type-check 2>/dev/null || docker-compose run --rm frontend npx tsc --noEmit; then
        print_success "Type checking passou!"
    else
        print_error "Type checking falhou!"
        FRONTEND_FAILED=1
    fi

    echo ""

    # Verificar formatação
    print_info "Verificando formatação..."
    if docker-compose run --rm frontend npm run format:check 2>/dev/null || docker-compose run --rm frontend npx prettier --check .; then
        print_success "Formatação está correta!"
    else
        print_warning "Formatação precisa de ajustes. Execute: npm run format"
    fi
fi

# ============================================
# RESUMO
# ============================================

echo ""
print_info "=========================================="
print_info "RESUMO DOS TESTES"
print_info "=========================================="
echo ""

if [ $RUN_BACKEND -eq 1 ]; then
    if [ $BACKEND_FAILED -eq 0 ]; then
        print_success "Backend: PASSOU"
    else
        print_error "Backend: FALHOU"
    fi
fi

if [ $RUN_FRONTEND -eq 1 ]; then
    if [ $FRONTEND_FAILED -eq 0 ]; then
        print_success "Frontend: PASSOU"
    else
        print_error "Frontend: FALHOU"
    fi
fi

echo ""

# Exit code
if [ $BACKEND_FAILED -eq 1 ] || [ $FRONTEND_FAILED -eq 1 ]; then
    print_error "Alguns testes falharam!"
    exit 1
else
    print_success "Todos os testes passaram!"
    exit 0
fi
