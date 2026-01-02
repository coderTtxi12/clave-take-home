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

# Database connection parameters
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5433}"
DB_NAME="${DB_NAME:-restaurant_analytics}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"

# Load .env if exists
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Check if psql is available, otherwise use docker
if command -v psql &> /dev/null; then
    PSQL_CMD="psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME"
    # Check if database is reachable
    echo -e "${YELLOW}Checking database connection...${NC}"
    export PGPASSWORD=$DB_PASSWORD
    if ! $PSQL_CMD -c '\q' 2>/dev/null; then
        echo -e "${RED}ERROR: Cannot connect to PostgreSQL${NC}"
        echo -e "${RED}Make sure the database is running: docker-compose up -d${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Database connection successful${NC}"
    echo ""
    
    # Install functions
    echo -e "${YELLOW}Installing ETL functions...${NC}"
    $PSQL_CMD -f sql/etl_functions.sql
else
    # Use docker-compose exec instead
    echo -e "${YELLOW}psql not found, using Docker...${NC}"
    echo -e "${YELLOW}Checking database connection...${NC}"
    if ! docker-compose exec -T postgres psql -U $DB_USER -d $DB_NAME -c '\q' 2>/dev/null; then
        echo -e "${RED}ERROR: Cannot connect to PostgreSQL${NC}"
        echo -e "${RED}Make sure the database is running: docker-compose up -d${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Database connection successful${NC}"
    echo ""
    
    # Install functions
    echo -e "${YELLOW}Installing ETL functions...${NC}"
    docker-compose exec -T postgres psql -U $DB_USER -d $DB_NAME -f /sql/etl_functions.sql
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

