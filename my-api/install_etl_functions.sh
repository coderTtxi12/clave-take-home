#!/bin/bash

# Script para instalar funciones PostgreSQL para ETL
# Ejecutar después de aplicar migraciones de Alembic

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Installing ETL Functions${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# Get the project root directory (one level up from my-api/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

# Load .env from project root if exists
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# Determine database connection (Supabase or local)
if [ -n "$SUPABASE_DB_HOST" ]; then
    echo -e "${GREEN}Using Supabase database...${NC}"
    DB_HOST=$SUPABASE_DB_HOST
    DB_PORT=${SUPABASE_DB_PORT:-5432}
    DB_NAME=${SUPABASE_DB_NAME:-postgres}
    DB_USER=${SUPABASE_DB_USER:-postgres}
    DB_PASSWORD=$SUPABASE_DB_PASSWORD
    if [ -z "$DB_PASSWORD" ]; then
        echo -e "${RED}ERROR: SUPABASE_DB_PASSWORD must be set${NC}"
        exit 1
    fi
    USE_DOCKER=false
else
    echo -e "${GREEN}Using local PostgreSQL...${NC}"
    DB_HOST=${DB_HOST:-localhost}
    DB_PORT=${DB_PORT:-5433}
    DB_NAME=${DB_NAME:-${POSTGRES_DB:-restaurant_analytics}}
    DB_USER=${DB_USER:-${POSTGRES_USER:-postgres}}
    DB_PASSWORD=${DB_PASSWORD:-${POSTGRES_PASSWORD:-postgres}}
    USE_DOCKER=true
fi

# Check if psql is available, otherwise use Docker
USE_DOCKER_PSQL=false
if command -v psql &> /dev/null; then
    PSQL_CMD="psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME"
    echo -e "${GREEN}Using local psql client${NC}"
else
    # Use Docker with postgres image that includes psql
    if command -v docker &> /dev/null; then
        USE_DOCKER_PSQL=true
        echo -e "${YELLOW}psql not found, using Docker (postgres:15-alpine)${NC}"
    else
        echo -e "${RED}ERROR: Neither psql nor docker is installed${NC}"
        echo -e "${YELLOW}Please install PostgreSQL client tools or Docker${NC}"
        exit 1
    fi
fi

# Check database connection
echo -e "${YELLOW}Checking database connection...${NC}"
if [ "$USE_DOCKER_PSQL" = true ]; then
    if ! docker run --rm -e PGPASSWORD=$DB_PASSWORD postgres:15-alpine psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c '\q' 2>/dev/null; then
        echo -e "${RED}ERROR: Cannot connect to database${NC}"
        if [ "$USE_DOCKER" = true ]; then
            echo -e "${YELLOW}Make sure the database is running: docker-compose up -d postgres${NC}"
        else
            echo -e "${YELLOW}Verify your Supabase credentials in .env${NC}"
        fi
        exit 1
    fi
else
    export PGPASSWORD=$DB_PASSWORD
    if ! $PSQL_CMD -c '\q' 2>/dev/null; then
        echo -e "${RED}ERROR: Cannot connect to database${NC}"
        if [ "$USE_DOCKER" = true ]; then
            echo -e "${YELLOW}Make sure the database is running: docker-compose up -d postgres${NC}"
        else
            echo -e "${YELLOW}Verify your Supabase credentials in .env${NC}"
        fi
        exit 1
    fi
fi

echo -e "${GREEN}✓ Database connection successful${NC}"
echo ""

# Install functions
echo -e "${YELLOW}Installing ETL functions...${NC}"
if [ "$USE_DOCKER_PSQL" = true ]; then
    # Get absolute path to SQL file
    SQL_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/sql/etl_functions.sql"
    docker run --rm -i \
        -e PGPASSWORD=$DB_PASSWORD \
        -v "$SQL_FILE:/tmp/etl_functions.sql:ro" \
        postgres:15-alpine \
        psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f /tmp/etl_functions.sql
else
    export PGPASSWORD=$DB_PASSWORD
    $PSQL_CMD -f sql/etl_functions.sql
fi

echo ""
echo -e "${GREEN}✓ ETL functions installed successfully${NC}"
echo ""
echo -e "Functions installed:"
echo -e "  • get_location_id_by_source()"
echo -e "  • get_or_create_category()"
echo -e "  • validate_etl_data()"
echo ""
echo -e "Test with: ${GREEN}SELECT get_or_create_category('Test');${NC}"
echo ""

