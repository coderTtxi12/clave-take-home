#!/bin/bash

# Script Maestro para Configurar Producción con Supabase
# Ejecuta en orden: migraciones, usuario readonly, funciones SQL, y ETL
# Uso: ./setup_production.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}================================================================================"
echo -e "  🚀 CONFIGURACIÓN DE PRODUCCIÓN - SUPABASE"
echo -e "================================================================================"
echo -e "${NC}"

# Get the project root directory (one level up from my-api/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

# Load .env from project root
if [ -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}Loading environment variables from $ENV_FILE...${NC}"
    set -a
    source "$ENV_FILE"
    set +a
    echo -e "${GREEN}✓ Environment variables loaded${NC}"
else
    echo -e "${RED}ERROR: .env file not found at $ENV_FILE${NC}"
    echo -e "${YELLOW}Please create .env file in project root with Supabase credentials${NC}"
    exit 1
fi

# Verify Supabase configuration
if [ -z "$SUPABASE_DB_HOST" ]; then
    echo -e "${RED}ERROR: SUPABASE_DB_HOST is not set${NC}"
    echo -e "${YELLOW}Please configure Supabase credentials in .env${NC}"
    exit 1
fi

if [ -z "$SUPABASE_DB_PASSWORD" ]; then
    echo -e "${RED}ERROR: SUPABASE_DB_PASSWORD is not set${NC}"
    echo -e "${YELLOW}Please configure Supabase password in .env${NC}"
    exit 1
fi

# Set database connection variables
export DB_HOST=$SUPABASE_DB_HOST
export DB_PORT=${SUPABASE_DB_PORT:-5432}
export DB_NAME=${SUPABASE_DB_NAME:-postgres}
export DB_USER=${SUPABASE_DB_USER:-postgres}
export DB_PASSWORD=$SUPABASE_DB_PASSWORD

echo ""
echo -e "${GREEN}Supabase Configuration:${NC}"
echo -e "  Host: ${DB_HOST}"
echo -e "  Port: ${DB_PORT}"
echo -e "  Database: ${DB_NAME}"
echo -e "  User: ${DB_USER}"
echo ""

# Check if psql is available, otherwise use Docker
USE_DOCKER_PSQL=false
if command -v psql &> /dev/null; then
    PSQL_CMD="psql"
    echo -e "${GREEN}Using local psql client${NC}"
else
    # Use Docker with postgres image that includes psql
    if command -v docker &> /dev/null; then
        PSQL_CMD="docker run --rm -i postgres:15-alpine psql"
        USE_DOCKER_PSQL=true
        echo -e "${YELLOW}psql not found, using Docker (postgres:15-alpine)${NC}"
    else
        echo -e "${RED}ERROR: Neither psql nor docker is installed${NC}"
        echo -e "${YELLOW}Please install one of:${NC}"
        echo -e "  Option 1: PostgreSQL client:"
        echo -e "    macOS: brew install postgresql"
        echo -e "    Ubuntu: sudo apt-get install postgresql-client"
        echo -e "  Option 2: Docker:"
        echo -e "    https://docs.docker.com/get-docker/"
        exit 1
    fi
fi

# Test database connection
echo -e "${YELLOW}Testing database connection...${NC}"
if [ "$USE_DOCKER_PSQL" = true ]; then
    # For Docker, we need to pass connection string as environment variable
    # First, pull the image if needed (silently)
    docker pull postgres:15-alpine > /dev/null 2>&1 || true
    
    # Test connection with verbose error output
    # Force IPv4 to avoid IPv6 issues
    echo -e "${YELLOW}Attempting connection via Docker (forcing IPv4)...${NC}"
    CONNECTION_OUTPUT=$(docker run --rm \
        --network host \
        -e PGPASSWORD="$DB_PASSWORD" \
        postgres:15-alpine \
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>&1)
    CONNECTION_EXIT_CODE=$?
    
    # If that fails, try without --network host (for Docker Desktop on Mac)
    if [ $CONNECTION_EXIT_CODE -ne 0 ]; then
        echo -e "${YELLOW}Retrying with default Docker network...${NC}"
        CONNECTION_OUTPUT=$(docker run --rm \
            -e PGPASSWORD="$DB_PASSWORD" \
            postgres:15-alpine \
            psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>&1)
        CONNECTION_EXIT_CODE=$?
    fi
    
    if [ $CONNECTION_EXIT_CODE -ne 0 ]; then
        echo -e "${RED}ERROR: Cannot connect to Supabase database${NC}"
        echo ""
        echo -e "${YELLOW}Connection details:${NC}"
        echo -e "  Host: $DB_HOST"
        echo -e "  Port: $DB_PORT"
        echo -e "  Database: $DB_NAME"
        echo -e "  User: $DB_USER"
        echo -e "  Password: ${DB_PASSWORD:0:3}*** (hidden)"
        echo ""
        if [ -n "$CONNECTION_OUTPUT" ]; then
            echo -e "${YELLOW}Error message:${NC}"
            echo "$CONNECTION_OUTPUT" | head -5
            echo ""
        fi
        echo -e "${YELLOW}Possible solutions:${NC}"
        echo ""
        echo -e "  1. ${BLUE}Enable 'Allow all IPs' in Supabase:${NC}"
        echo -e "     Settings > Database > Network Restrictions > 'Allow all IPs'"
        echo ""
        echo -e "  2. ${BLUE}Install psql locally (recommended):${NC}"
        echo -e "     macOS: ${GREEN}brew install postgresql${NC}"
        echo -e "     This avoids Docker network issues"
        echo ""
        echo -e "  3. ${BLUE}Check Docker network:${NC}"
        echo -e "     docker run --rm alpine ping -c 1 8.8.8.8"
        echo ""
        echo -e "  4. ${BLUE}Verify Supabase credentials:${NC}"
        echo -e "     - Host: $DB_HOST"
        echo -e "     - Password matches Supabase Dashboard"
        echo ""
        echo -e "  5. ${BLUE}Try connecting directly (if you install psql):${NC}"
        echo -e "     psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME"
        echo ""
        exit 1
    fi
else
    export PGPASSWORD=$DB_PASSWORD
    CONNECTION_OUTPUT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>&1)
    CONNECTION_EXIT_CODE=$?
    
    if [ $CONNECTION_EXIT_CODE -ne 0 ]; then
        echo -e "${RED}ERROR: Cannot connect to Supabase database${NC}"
        echo ""
        if [ -n "$CONNECTION_OUTPUT" ]; then
            echo -e "${YELLOW}Error message:${NC}"
            echo "$CONNECTION_OUTPUT" | head -5
            echo ""
        fi
        echo -e "${YELLOW}Please verify:${NC}"
        echo -e "  1. Your Supabase credentials in .env are correct"
        echo -e "  2. Your IP is allowed in Supabase (Settings > Database > Network Restrictions)"
        echo -e "  3. Your Supabase project is active"
        exit 1
    fi
fi
echo -e "${GREEN}✓ Database connection successful${NC}"
echo ""

# ============================================================================
# STEP 1: Run Migrations
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}STEP 1: Running Database Migrations${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if Python dependencies are installed
if ! command -v alembic &> /dev/null && ! python3 -m alembic --help &> /dev/null 2>&1; then
    echo -e "${YELLOW}Installing Python dependencies...${NC}"
    if [ -f "requirements.txt" ]; then
        pip3 install -q -r requirements.txt || pip install -q -r requirements.txt
    else
        echo -e "${YELLOW}Installing minimal dependencies for migrations...${NC}"
        pip3 install -q alembic sqlalchemy psycopg2-binary python-dotenv || \
        pip install -q alembic sqlalchemy psycopg2-binary python-dotenv
    fi
fi

./run_alembic_migrations.sh upgrade head

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Migrations failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Migrations completed${NC}"
echo ""

# ============================================================================
# STEP 2: Create Read-Only User
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}STEP 2: Creating Read-Only User${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}Creating read-only user for code executor...${NC}"

# Read the SQL file and replace database name if needed
SQL_FILE="sql/create_readonly_user.sql"
TEMP_SQL=$(mktemp)

# Replace restaurant_analytics with actual database name
sed "s/restaurant_analytics/$DB_NAME/g" "$SQL_FILE" > "$TEMP_SQL"

# Execute SQL (suppress NOTICE messages)
if [ "$USE_DOCKER_PSQL" = true ]; then
    # For Docker, copy SQL file into container and execute
    # Try with --network host first, fallback to default network
    if docker run --rm \
        --network host \
        -e PGPASSWORD="$DB_PASSWORD" \
        -v "$TEMP_SQL:/tmp/create_user.sql:ro" \
        postgres:15-alpine \
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f /tmp/create_user.sql 2>&1 | grep -v "NOTICE" || true; then
        : # Success
    else
        # Fallback to default network
        docker run --rm \
            -e PGPASSWORD="$DB_PASSWORD" \
            -v "$TEMP_SQL:/tmp/create_user.sql:ro" \
            postgres:15-alpine \
            psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f /tmp/create_user.sql 2>&1 | grep -v "NOTICE" || true
    fi
else
    export PGPASSWORD=$DB_PASSWORD
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$TEMP_SQL" 2>&1 | grep -v "NOTICE" || true
fi

# Clean up temp file
rm "$TEMP_SQL"

echo -e "${GREEN}✓ Read-only user created${NC}"
echo ""

# ============================================================================
# STEP 3: Install ETL Functions
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}STEP 3: Installing ETL Functions${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

./install_etl_functions.sh

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: ETL functions installation failed${NC}"
    exit 1
fi

echo ""

# ============================================================================
# STEP 4: Load Data (ETL)
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}STEP 4: Loading Data (ETL)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

read -p "Do you want to load data now? (yes/no): " -r
echo ""

if [[ $REPLY =~ ^[Yy]es$ ]]; then
    ./load_data.sh
    if [ $? -ne 0 ]; then
        echo -e "${RED}ERROR: Data loading failed${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}Skipping data load. You can run it later with: ./load_data.sh${NC}"
fi

echo ""

# ============================================================================
# Summary
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ PRODUCTION SETUP COMPLETED SUCCESSFULLY${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${GREEN}What was done:${NC}"
echo -e "  ✓ Database migrations applied"
echo -e "  ✓ Read-only user created (code_executor_readonly)"
echo -e "  ✓ ETL functions installed"
if [[ $REPLY =~ ^[Yy]es$ ]]; then
    echo -e "  ✓ Data loaded from JSON files"
fi
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Start production services:"
echo -e "     ${BLUE}docker-compose -f docker-compose.prod.yml up -d${NC}"
echo ""
echo -e "  2. Verify services are running:"
echo -e "     ${BLUE}docker-compose -f docker-compose.prod.yml ps${NC}"
echo ""
echo -e "  3. Check API health:"
echo -e "     ${BLUE}curl http://localhost:8000/health${NC}"
echo ""
echo -e "  4. Access dashboard:"
echo -e "     ${BLUE}http://localhost:3000${NC}"
echo ""

