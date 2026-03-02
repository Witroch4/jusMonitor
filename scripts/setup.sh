#!/bin/bash

# JusMonitorIA Setup Script
# This script helps set up the development environment

set -e

echo "🚀 JusMonitorIA Setup Script"
echo "=========================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Setup backend environment
echo "📦 Setting up backend environment..."
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo "✅ Created backend/.env from example"
    echo "⚠️  Please edit backend/.env with your configuration"
else
    echo "ℹ️  backend/.env already exists"
fi
echo ""

# Setup frontend environment
echo "📦 Setting up frontend environment..."
if [ ! -f frontend/.env.local ]; then
    cp frontend/.env.example frontend/.env.local
    echo "✅ Created frontend/.env.local from example"
else
    echo "ℹ️  frontend/.env.local already exists"
fi
echo ""

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p docker/postgres
mkdir -p docs
echo "✅ Directories created"
echo ""

# Start Docker services
echo "🐳 Starting Docker services..."
docker-compose up -d postgres redis
echo "✅ Database and Redis started"
echo ""

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 10

# Check if we should run migrations
read -p "Do you want to run database migrations now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔄 Running database migrations..."
    docker-compose run --rm backend alembic upgrade head
    echo "✅ Migrations completed"
fi
echo ""

# Start all services
echo "🚀 Starting all services..."
docker-compose up -d
echo "✅ All services started"
echo ""

echo "✨ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Edit backend/.env with your API keys and configuration"
echo "2. Edit frontend/.env.local if needed"
echo "3. Access the application:"
echo "   - Frontend: http://localhost:3000"
echo "   - Backend API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo ""
echo "📚 Useful commands:"
echo "   - View logs: docker-compose logs -f"
echo "   - Stop services: docker-compose down"
echo "   - Restart services: docker-compose restart"
echo ""
