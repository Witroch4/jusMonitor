#!/bin/bash

# JusMonitor - Script de Seed
# Popula o banco de dados com dados de demonstração

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
  ____                _
 / ___|  ___  ___  __| |
 \___ \ / _ \/ _ \/ _` |
  ___) |  __/  __/ (_| |
 |____/ \___|\___|\__,_|
                        
EOF
echo -e "${NC}"

# Verificar se Docker está rodando
if ! docker info > /dev/null 2>&1; then
    print_error "Docker não está rodando. Por favor, inicie o Docker primeiro."
    exit 1
fi

# Verificar se PostgreSQL está rodando
if ! docker-compose ps postgres | grep -q "Up"; then
    print_warning "PostgreSQL não está rodando. Iniciando..."
    docker-compose up -d postgres redis
    sleep 3
    
    # Aguardar PostgreSQL estar pronto
    print_info "Aguardando PostgreSQL inicializar..."
    until docker-compose exec -T postgres pg_isready -U jusmonitor &>/dev/null; do
        echo -n "."
        sleep 1
    done
    echo ""
    print_success "PostgreSQL está pronto!"
fi

# Parse argumentos
SEED_ALL=0
SEED_TENANT=0
SEED_CRM=0
SEED_CASES=0
SEED_AI=0
RESET=0

if [ $# -eq 0 ]; then
    # Sem argumentos, perguntar o que fazer
    echo "O que deseja popular?"
    echo ""
    echo "1) Tudo (tenant, usuários, leads, clientes, processos, IA)"
    echo "2) Apenas tenant e usuários"
    echo "3) Apenas CRM (leads e clientes)"
    echo "4) Apenas processos e movimentações"
    echo "5) Apenas configurações de IA"
    echo ""
    read -p "Escolha uma opção (1-5): " -n 1 -r
    echo ""
    
    case $REPLY in
        1) SEED_ALL=1 ;;
        2) SEED_TENANT=1 ;;
        3) SEED_CRM=1 ;;
        4) SEED_CASES=1 ;;
        5) SEED_AI=1 ;;
        *)
            print_error "Opção inválida."
            exit 1
            ;;
    esac
    
    echo ""
    read -p "Deseja resetar os dados existentes antes? (s/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        RESET=1
    fi
else
    # Parse argumentos da linha de comando
    while [[ $# -gt 0 ]]; do
        case $1 in
            --all)
                SEED_ALL=1
                shift
                ;;
            --tenant)
                SEED_TENANT=1
                shift
                ;;
            --crm)
                SEED_CRM=1
                shift
                ;;
            --cases)
                SEED_CASES=1
                shift
                ;;
            --ai)
                SEED_AI=1
                shift
                ;;
            --reset)
                RESET=1
                shift
                ;;
            -h|--help)
                echo "Uso: $0 [opções]"
                echo ""
                echo "Opções:"
                echo "  --all       Popular tudo (tenant, CRM, processos, IA)"
                echo "  --tenant    Popular apenas tenant e usuários"
                echo "  --crm       Popular apenas leads e clientes"
                echo "  --cases     Popular apenas processos e movimentações"
                echo "  --ai        Popular apenas configurações de IA"
                echo "  --reset     Resetar dados existentes antes de popular"
                echo "  -h, --help  Mostrar esta ajuda"
                echo ""
                echo "Exemplos:"
                echo "  $0 --all                    # Popular tudo"
                echo "  $0 --tenant --crm           # Popular tenant e CRM"
                echo "  $0 --all --reset            # Resetar e popular tudo"
                exit 0
                ;;
            *)
                print_error "Opção desconhecida: $1"
                exit 1
                ;;
        esac
    done
fi

# Construir comando
CMD="python -m cli.seed"

if [ $SEED_ALL -eq 1 ]; then
    CMD="$CMD --all"
elif [ $SEED_TENANT -eq 1 ]; then
    CMD="$CMD --tenant"
elif [ $SEED_CRM -eq 1 ]; then
    CMD="$CMD --crm"
elif [ $SEED_CASES -eq 1 ]; then
    CMD="$CMD --cases"
elif [ $SEED_AI -eq 1 ]; then
    CMD="$CMD --ai"
fi

if [ $RESET -eq 1 ]; then
    CMD="$CMD --reset"
    print_warning "ATENÇÃO: Dados existentes serão removidos!"
    sleep 2
fi

# Executar seed
echo ""
print_info "Executando: $CMD"
echo ""

if docker-compose run --rm backend $CMD; then
    echo ""
    print_success "Banco de dados populado com sucesso!"
    echo ""
    
    # Mostrar credenciais de acesso
    if [ $SEED_ALL -eq 1 ] || [ $SEED_TENANT -eq 1 ]; then
        print_info "=========================================="
        print_info "CREDENCIAIS DE ACESSO"
        print_info "=========================================="
        echo ""
        echo -e "  ${GREEN}Tenant:${NC} Demo Law Firm"
        echo -e "  ${GREEN}URL:${NC} http://localhost:3000"
        echo ""
        echo -e "  ${BLUE}Admin:${NC}"
        echo -e "    Email: ${GREEN}admin@demo.com${NC}"
        echo -e "    Senha: ${GREEN}admin123${NC}"
        echo ""
        echo -e "  ${BLUE}Advogado:${NC}"
        echo -e "    Email: ${GREEN}advogado@demo.com${NC}"
        echo -e "    Senha: ${GREEN}advogado123${NC}"
        echo ""
        echo -e "  ${BLUE}Assistente:${NC}"
        echo -e "    Email: ${GREEN}assistente@demo.com${NC}"
        echo -e "    Senha: ${GREEN}assistente123${NC}"
        echo ""
    fi
    
    # Mostrar estatísticas
    if [ $SEED_ALL -eq 1 ] || [ $SEED_CRM -eq 1 ]; then
        print_info "Dados populados:"
        echo "  • 20 leads em diferentes estágios"
        echo "  • 10 clientes com histórico"
        echo "  • 15 processos com movimentações"
        echo "  • 100+ eventos na timeline"
        echo "  • Embeddings gerados para busca semântica"
        echo ""
    fi
    
    print_info "Para acessar o sistema:"
    echo "  1. Certifique-se que os serviços estão rodando: docker-compose up -d"
    echo "  2. Acesse: http://localhost:3000"
    echo "  3. Faça login com as credenciais acima"
    echo ""
    
else
    echo ""
    print_error "Erro ao popular banco de dados."
    print_info "Verifique os logs para mais detalhes: docker-compose logs backend"
    exit 1
fi
