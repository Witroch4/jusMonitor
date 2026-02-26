#!/bin/bash

# JusMonitor - Script de Desenvolvimento
# Inicia todos os serviços necessários para desenvolvimento local

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
     _           __  __             _ _             
    | |_   _ ___|  \/  | ___  _ __ (_) |_ ___  _ __ 
 _  | | | | / __| |\/| |/ _ \| '_ \| | __/ _ \| '__|
| |_| | |_| \__ \ |  | | (_) | | | | | || (_) | |   
 \___/ \__,_|___/_|  |_|\___/|_| |_|_|\__\___/|_|   
                                                     
EOF
echo -e "${NC}"
print_info "Iniciando ambiente de desenvolvimento..."
echo ""

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    print_error "Docker não está instalado. Por favor, instale o Docker primeiro."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose não está instalado. Por favor, instale o Docker Compose primeiro."
    exit 1
fi

# Verificar se arquivos .env existem
if [ ! -f "backend/.env" ]; then
    print_warning "Arquivo backend/.env não encontrado. Copiando de .env.example..."
    cp backend/.env.example backend/.env
    print_warning "Por favor, edite backend/.env com suas credenciais antes de continuar."
    exit 1
fi

if [ ! -f "frontend/.env.local" ]; then
    print_warning "Arquivo frontend/.env.local não encontrado. Copiando de .env.example..."
    cp frontend/.env.example frontend/.env.local
    print_info "Arquivo frontend/.env.local criado com valores padrão."
fi

# Parar containers existentes
print_info "Parando containers existentes..."
docker-compose down 2>/dev/null || true

# Iniciar serviços de infraestrutura (PostgreSQL e Redis)
print_info "Iniciando PostgreSQL e Redis..."
docker-compose up -d postgres redis

# Aguardar PostgreSQL estar pronto
print_info "Aguardando PostgreSQL inicializar..."
sleep 5

# Verificar se PostgreSQL está pronto
until docker-compose exec -T postgres pg_isready -U jusmonitor &>/dev/null; do
    echo -n "."
    sleep 1
done
echo ""
print_success "PostgreSQL está pronto!"

# Verificar se Redis está pronto
print_info "Verificando Redis..."
until docker-compose exec -T redis redis-cli ping &>/dev/null; do
    echo -n "."
    sleep 1
done
echo ""
print_success "Redis está pronto!"

# Aplicar migrations
print_info "Aplicando migrations do banco de dados..."
docker-compose exec -T postgres psql -U jusmonitor -d jusmonitor -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || true
docker-compose run --rm backend alembic upgrade head

if [ $? -eq 0 ]; then
    print_success "Migrations aplicadas com sucesso!"
else
    print_error "Erro ao aplicar migrations. Verifique os logs."
    exit 1
fi

# Perguntar se deseja popular banco com dados de teste
echo ""
read -p "Deseja popular o banco com dados de demonstração? (s/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Ss]$ ]]; then
    print_info "Populando banco de dados..."
    docker-compose run --rm backend python -m cli.seed --all
    print_success "Banco de dados populado!"
    echo ""
    print_info "Credenciais de acesso:"
    echo -e "  Email: ${GREEN}admin@demo.com${NC}"
    echo -e "  Senha: ${GREEN}admin123${NC}"
    echo ""
fi

# Iniciar backend e frontend
print_info "Iniciando backend e frontend..."
docker-compose up -d backend frontend

# Aguardar serviços iniciarem
print_info "Aguardando serviços iniciarem..."
sleep 5

# Verificar se serviços estão rodando
print_info "Verificando status dos serviços..."
echo ""

# Backend
if curl -s http://localhost:8000/health/live > /dev/null 2>&1; then
    print_success "Backend API está rodando em http://localhost:8000"
    print_info "  Swagger UI: http://localhost:8000/docs"
    print_info "  ReDoc: http://localhost:8000/redoc"
else
    print_warning "Backend ainda está inicializando..."
fi

# Frontend
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    print_success "Frontend está rodando em http://localhost:3000"
else
    print_warning "Frontend ainda está inicializando..."
fi

echo ""
print_success "Ambiente de desenvolvimento iniciado com sucesso!"
echo ""
print_info "Comandos úteis:"
echo "  docker-compose logs -f          # Ver logs de todos os serviços"
echo "  docker-compose logs -f backend  # Ver logs do backend"
echo "  docker-compose logs -f frontend # Ver logs do frontend"
echo "  docker-compose down             # Parar todos os serviços"
echo "  docker-compose restart backend  # Reiniciar backend"
echo ""
print_info "Para parar o ambiente, execute: docker-compose down"
echo ""
