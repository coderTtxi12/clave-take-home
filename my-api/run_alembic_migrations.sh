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
elif [ -d "../.venv" ]; then
    # También buscar en la raíz del proyecto
    source ../.venv/bin/activate
fi

# Verificar que alembic esté instalado
if ! command -v alembic &> /dev/null; then
    echo -e "${YELLOW}⚠${NC}  alembic not found. Installing dependencies..."
    if [ -f "requirements.txt" ]; then
        pip install -q alembic sqlalchemy psycopg2-binary python-dotenv || pip3 install -q alembic sqlalchemy psycopg2-binary python-dotenv
    else
        echo -e "${RED}ERROR: requirements.txt not found and alembic is not installed${NC}"
        echo -e "${YELLOW}Please install dependencies: pip install -r requirements.txt${NC}"
        exit 1
    fi
fi

# Get the project root directory (one level up from my-api/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

# Cargar variables de entorno desde .env en la raíz del proyecto
# Solo exporta líneas que son variables válidas (KEY=VALUE)
if [ -f "$ENV_FILE" ]; then
    # Use source with set -a to export variables safely
    # This only processes lines that match KEY=VALUE pattern
    set -a
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        # Only process lines that look like KEY=VALUE
        if [[ "$line" =~ ^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*= ]]; then
            eval "export $line" 2>/dev/null || true
        fi
    done < "$ENV_FILE"
    set +a
fi

# Set default database connection
# Prefer Supabase if configured, otherwise use local PostgreSQL
if [ -n "$SUPABASE_DB_HOST" ]; then
    echo -e "${YELLOW}Using Supabase database configuration...${NC}"
    export DB_HOST=${SUPABASE_DB_HOST}
    export DB_PORT=${SUPABASE_DB_PORT:-5432}
    export DB_NAME=${SUPABASE_DB_NAME:-postgres}
    export DB_USER=${SUPABASE_DB_USER:-postgres}
    export DB_PASSWORD=${SUPABASE_DB_PASSWORD}
    DB_USER_FOR_CHECK=$DB_USER
else
    echo -e "${YELLOW}Using local PostgreSQL configuration...${NC}"
    export POSTGRES_USER=${POSTGRES_USER:-postgres}
    export POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
    export POSTGRES_DB=${POSTGRES_DB:-restaurant_analytics}
    export DB_HOST=${DB_HOST:-localhost}
    export DB_PORT=${DB_PORT:-5433}
    export DB_NAME=${DB_NAME:-$POSTGRES_DB}
    export DB_USER=${DB_USER:-$POSTGRES_USER}
    export DB_PASSWORD=${DB_PASSWORD:-$POSTGRES_PASSWORD}
    DB_USER_FOR_CHECK=$POSTGRES_USER
    
    # Check if local database is running (only for local, not Supabase)
    echo -e "${YELLOW}Checking database connection...${NC}"
    if ! pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER_FOR_CHECK > /dev/null 2>&1; then
        echo -e "${YELLOW}Warning: Cannot connect to database. Starting docker-compose...${NC}"
        docker-compose up -d postgres
        echo "Waiting for PostgreSQL..."
        sleep 5
    fi
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

