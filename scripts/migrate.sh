#!/bin/bash

# JusMonitor - Script de Migrations
# Gerencia migrations do banco de dados com Alembic

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
  __  __ _                 _   _                 
 |  \/  (_) __ _ _ __ __ _| |_(_) ___  _ __  ___ 
 | |\/| | |/ _` | '__/ _` | __| |/ _ \| '_ \/ __|
 | |  | | | (_| | | | (_| | |_| | (_) | | | \__ \
 |_|  |_|_|\__, |_|  \__,_|\__|_|\___/|_| |_|___/
           |___/                                  
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
    docker-compose up -d postgres
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

# Habilitar extensão pgvector
print_info "Habilitando extensão pgvector..."
docker-compose exec -T postgres psql -U jusmonitor -d jusmonitor -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || true

# Parse comando
COMMAND=${1:-"upgrade"}

case $COMMAND in
    upgrade|up)
        print_info "Aplicando migrations..."
        docker-compose run --rm backend alembic upgrade head
        
        if [ $? -eq 0 ]; then
            print_success "Migrations aplicadas com sucesso!"
        else
            print_error "Erro ao aplicar migrations."
            exit 1
        fi
        ;;
        
    downgrade|down)
        STEPS=${2:-1}
        print_warning "Revertendo $STEPS migration(s)..."
        read -p "Tem certeza? Esta operação pode causar perda de dados. (s/N): " -n 1 -r
        echo ""
        
        if [[ $REPLY =~ ^[Ss]$ ]]; then
            docker-compose run --rm backend alembic downgrade -$STEPS
            
            if [ $? -eq 0 ]; then
                print_success "Migration(s) revertida(s) com sucesso!"
            else
                print_error "Erro ao reverter migrations."
                exit 1
            fi
        else
            print_info "Operação cancelada."
        fi
        ;;
        
    create|new)
        if [ -z "$2" ]; then
            print_error "Por favor, forneça uma mensagem para a migration."
            echo "Uso: $0 create \"mensagem da migration\""
            exit 1
        fi
        
        MESSAGE="$2"
        print_info "Criando nova migration: $MESSAGE"
        docker-compose run --rm backend alembic revision --autogenerate -m "$MESSAGE"
        
        if [ $? -eq 0 ]; then
            print_success "Migration criada com sucesso!"
            print_info "Revise o arquivo gerado em backend/alembic/versions/"
            print_warning "IMPORTANTE: Sempre revise migrations auto-geradas antes de aplicar!"
        else
            print_error "Erro ao criar migration."
            exit 1
        fi
        ;;
        
    history|log)
        print_info "Histórico de migrations:"
        echo ""
        docker-compose run --rm backend alembic history
        ;;
        
    current)
        print_info "Migration atual:"
        echo ""
        docker-compose run --rm backend alembic current
        ;;
        
    heads)
        print_info "Heads das migrations:"
        echo ""
        docker-compose run --rm backend alembic heads
        ;;
        
    show)
        if [ -z "$2" ]; then
            print_error "Por favor, forneça o ID da migration."
            echo "Uso: $0 show <revision_id>"
            exit 1
        fi
        
        REVISION="$2"
        print_info "Detalhes da migration $REVISION:"
        echo ""
        docker-compose run --rm backend alembic show "$REVISION"
        ;;
        
    sql)
        print_info "Gerando SQL das migrations pendentes..."
        docker-compose run --rm backend alembic upgrade head --sql
        ;;
        
    reset)
        print_error "ATENÇÃO: Esta operação irá APAGAR TODOS OS DADOS do banco!"
        read -p "Tem ABSOLUTA certeza? Digite 'RESET' para confirmar: " CONFIRM
        
        if [ "$CONFIRM" = "RESET" ]; then
            print_warning "Resetando banco de dados..."
            
            # Dropar e recriar banco
            docker-compose exec -T postgres psql -U jusmonitor -c "DROP DATABASE IF EXISTS jusmonitor;"
            docker-compose exec -T postgres psql -U jusmonitor -c "CREATE DATABASE jusmonitor;"
            docker-compose exec -T postgres psql -U jusmonitor -d jusmonitor -c "CREATE EXTENSION IF NOT EXISTS vector;"
            
            # Aplicar migrations
            docker-compose run --rm backend alembic upgrade head
            
            print_success "Banco de dados resetado!"
            print_info "Execute './scripts/seed.sh' para popular com dados de teste."
        else
            print_info "Operação cancelada."
        fi
        ;;
        
    -h|--help|help)
        echo "Uso: $0 <comando> [argumentos]"
        echo ""
        echo "Comandos:"
        echo "  upgrade, up              Aplicar todas as migrations pendentes"
        echo "  downgrade, down [N]      Reverter N migrations (padrão: 1)"
        echo "  create, new <mensagem>   Criar nova migration"
        echo "  history, log             Ver histórico de migrations"
        echo "  current                  Ver migration atual"
        echo "  heads                    Ver heads das migrations"
        echo "  show <revision>          Ver detalhes de uma migration"
        echo "  sql                      Gerar SQL das migrations (sem aplicar)"
        echo "  reset                    RESETAR banco de dados (CUIDADO!)"
        echo "  help                     Mostrar esta ajuda"
        echo ""
        echo "Exemplos:"
        echo "  $0 upgrade                           # Aplicar migrations"
        echo "  $0 create \"adiciona campo email\"     # Criar migration"
        echo "  $0 downgrade 2                       # Reverter 2 migrations"
        echo "  $0 history                           # Ver histórico"
        ;;
        
    *)
        print_error "Comando desconhecido: $COMMAND"
        echo "Execute '$0 help' para ver comandos disponíveis."
        exit 1
        ;;
esac
