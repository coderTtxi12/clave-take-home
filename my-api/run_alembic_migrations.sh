#!/bin/bash

# Script para ejecutar migraciones con Alembic
# Uso: ./run_alembic_migrations.sh [upgrade|downgrade|current|history]

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Restaurant Analytics - Alembic${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# Activar virtual environment si existe
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Cargar variables de entorno desde .env
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set default database connection
export POSTGRES_USER=${POSTGRES_USER:-postgres}
export POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
export POSTGRES_DB=${POSTGRES_DB:-restaurant_analytics}
export DB_HOST=${DB_HOST:-localhost}
export DB_PORT=${DB_PORT:-5433}

# Check if database is running
echo -e "${YELLOW}Checking database connection...${NC}"
if ! pg_isready -h $DB_HOST -p $DB_PORT -U $POSTGRES_USER > /dev/null 2>&1; then
    echo -e "${YELLOW}Warning: Cannot connect to database. Starting docker-compose...${NC}"
    docker-compose up -d
    echo "Waiting for PostgreSQL..."
    sleep 5
fi

# Run alembic command
COMMAND=${1:-upgrade}
TARGET=${2:-head}

case $COMMAND in
    upgrade)
        echo -e "${YELLOW}Running migrations (upgrade to $TARGET)...${NC}"
        alembic upgrade $TARGET
        echo -e "${GREEN}✓ Migrations completed${NC}"
        ;;
    downgrade)
        echo -e "${YELLOW}Downgrading migrations (downgrade to $TARGET)...${NC}"
        alembic downgrade $TARGET
        echo -e "${GREEN}✓ Downgrade completed${NC}"
        ;;
    current)
        echo -e "${YELLOW}Current database version:${NC}"
        alembic current
        ;;
    history)
        echo -e "${YELLOW}Migration history:${NC}"
        alembic history
        ;;
    revision)
        echo -e "${YELLOW}Creating new migration...${NC}"
        MESSAGE=${2:-"auto_migration"}
        alembic revision --autogenerate -m "$MESSAGE"
        echo -e "${GREEN}✓ Migration created${NC}"
        ;;
    *)
        echo "Usage: $0 {upgrade|downgrade|current|history|revision} [target/message]"
        echo ""
        echo "Examples:"
        echo "  $0 upgrade head        # Apply all migrations"
        echo "  $0 upgrade +1          # Apply next migration"
        echo "  $0 downgrade -1        # Revert last migration"
        echo "  $0 current             # Show current version"
        echo "  $0 history             # Show migration history"
        echo "  $0 revision add_users  # Create new migration"
        exit 1
        ;;
esac

echo ""

