#!/bin/bash

# ETL Data Loading Script
# Installs dependencies and loads all restaurant data into PostgreSQL

set -e  # Exit on error

echo "================================================================================"
echo "  RESTAURANT ANALYTICS - ETL DATA LOADER"
echo "================================================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Python 3 found: $(python3 --version)"

# Get the project root directory (one level up from my-api/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

# Load environment variables from .env file in project root if it exists
if [ -f "$ENV_FILE" ]; then
    echo ""
    echo "Loading environment variables from $ENV_FILE..."
    set -a  # Automatically export all variables
    source "$ENV_FILE"
    set +a  # Stop automatically exporting
    echo -e "${GREEN}✓${NC} Environment variables loaded from .env"
else
    echo ""
    echo -e "${YELLOW}⚠${NC}  No .env file found at $ENV_FILE, using defaults"
    export DB_HOST=localhost
    export DB_PORT=5433
    export DB_NAME=restaurant_analytics
    export DB_USER=postgres
    export DB_PASSWORD=postgres
fi

# Determine if using Supabase or local PostgreSQL
if [ -n "$SUPABASE_DB_HOST" ]; then
    echo ""
    echo -e "${GREEN}✓${NC} Using Supabase database: $SUPABASE_DB_HOST"
    export DB_HOST=${SUPABASE_DB_HOST}
    export DB_PORT=${SUPABASE_DB_PORT:-5432}
    export DB_NAME=${SUPABASE_DB_NAME:-postgres}
    export DB_USER=${SUPABASE_DB_USER:-postgres}
    export DB_PASSWORD=${SUPABASE_DB_PASSWORD}
    USE_SUPABASE=true
else
    echo ""
    echo -e "${GREEN}✓${NC} Using local PostgreSQL database"
    # Set defaults for local PostgreSQL
    export DB_HOST=${DB_HOST:-localhost}
    export DB_PORT=${DB_PORT:-5433}
    export DB_NAME=${DB_NAME:-${POSTGRES_DB:-restaurant_analytics}}
    export DB_USER=${DB_USER:-${POSTGRES_USER:-postgres}}
    export DB_PASSWORD=${DB_PASSWORD:-${POSTGRES_PASSWORD:-postgres}}
    USE_SUPABASE=false
    
    # Check if local PostgreSQL is running
    echo ""
    echo "Checking PostgreSQL..."
    if ! docker-compose ps | grep -q "postgres.*Up"; then
        echo -e "${YELLOW}⚠${NC}  PostgreSQL is not running"
        echo "Starting PostgreSQL..."
        docker-compose up -d postgres
        echo "Waiting for PostgreSQL to be ready..."
        sleep 5
    fi
    echo -e "${GREEN}✓${NC} PostgreSQL is running"
fi

# Check if migrations have been run
echo ""
echo "Checking database schema..."
if [ "$USE_SUPABASE" = true ]; then
    # For Supabase, use psql directly if available, or skip check
    if command -v psql &> /dev/null; then
        if ! PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1 FROM locations LIMIT 1;" &> /dev/null; then
            echo -e "${YELLOW}⚠${NC}  Database schema not found"
            echo "Running migrations..."
            ./run_alembic_migrations.sh upgrade head
        else
            echo -e "${GREEN}✓${NC} Database schema exists"
        fi
    else
        echo -e "${YELLOW}⚠${NC}  psql not found, skipping schema check"
        echo "Make sure to run migrations: ./run_alembic_migrations.sh upgrade head"
    fi
else
    # For local PostgreSQL, use docker-compose
    if ! docker-compose exec -T postgres psql -U postgres -d restaurant_analytics -c "SELECT 1 FROM locations LIMIT 1;" &> /dev/null; then
        echo -e "${YELLOW}⚠${NC}  Database schema not found"
        echo "Running migrations..."
        ./run_alembic_migrations.sh upgrade head
    else
        echo -e "${GREEN}✓${NC} Database schema exists"
    fi
fi

# Check if ETL functions are installed (only for local, Supabase may have different setup)
if [ "$USE_SUPABASE" = false ]; then
    echo ""
    echo "Checking ETL functions..."
    if ! docker-compose exec -T postgres psql -U postgres -d restaurant_analytics -c "SELECT 1 FROM pg_proc WHERE proname = 'get_or_create_category';" &> /dev/null | grep -q "1 row"; then
        echo -e "${YELLOW}⚠${NC}  ETL functions not found"
        echo "Installing ETL functions..."
        ./install_etl_functions.sh
    else
        echo -e "${GREEN}✓${NC} ETL functions installed"
    fi
else
    echo ""
    echo -e "${YELLOW}⚠${NC}  ETL functions check skipped for Supabase"
    echo "Make sure ETL functions are installed in Supabase if needed"
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo ""
    echo "Activating virtual environment..."
    source .venv/bin/activate
    echo -e "${GREEN}✓${NC} Virtual environment activated"
fi

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
python3 -m pip install -q psycopg2-binary python-dotenv > /dev/null 2>&1 || pip3 install -q psycopg2-binary python-dotenv > /dev/null 2>&1
echo -e "${GREEN}✓${NC} Dependencies installed"

# Check if data files exist
echo ""
echo "Checking data files..."

DATA_DIR="../data/sources"
FILES_MISSING=false

if [ ! -f "$DATA_DIR/toast_pos_export.json" ]; then
    echo -e "${RED}✗ Missing: toast_pos_export.json${NC}"
    FILES_MISSING=true
else
    echo -e "${GREEN}✓${NC} Found: toast_pos_export.json"
fi

if [ ! -f "$DATA_DIR/doordash_orders.json" ]; then
    echo -e "${RED}✗ Missing: doordash_orders.json${NC}"
    FILES_MISSING=true
else
    echo -e "${GREEN}✓${NC} Found: doordash_orders.json"
fi

if [ ! -d "$DATA_DIR/square" ]; then
    echo -e "${RED}✗ Missing: square directory${NC}"
    FILES_MISSING=true
else
    for file in catalog.json locations.json orders.json payments.json; do
        if [ ! -f "$DATA_DIR/square/$file" ]; then
            echo -e "${RED}✗ Missing: square/$file${NC}"
            FILES_MISSING=true
        else
            echo -e "${GREEN}✓${NC} Found: square/$file"
        fi
    done
fi

if [ "$FILES_MISSING" = true ]; then
    echo ""
    echo -e "${RED}Some data files are missing. Aborting.${NC}"
    exit 1
fi

# Ask about clearing existing data
echo ""
echo "================================================================================"
if [ "$1" == "--clear" ] || [ "$1" == "-c" ]; then
    echo -e "${YELLOW}⚠  WARNING: This will DELETE all existing data!${NC}"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
        echo "Aborted."
        exit 0
    fi
    CLEAR_FLAG="--clear"
else
    echo "This will load data from JSON files into PostgreSQL."
    echo ""
    echo "Options:"
    echo "  • Normal load: Appends data (may create duplicates if re-run)"
    echo "  • Clear load:  Deletes all existing data first (use --clear flag)"
    echo ""
    read -p "Continue with normal load? (yes/no): " -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
        echo "Aborted."
        exit 0
    fi
    CLEAR_FLAG=""
fi

echo "================================================================================"
echo ""

# Run ETL
echo -e "${BLUE}Starting ETL process...${NC}"
echo ""

cd scripts

# Use venv Python if available, otherwise use system Python
if [ -d "../.venv" ]; then
    PYTHON_CMD="../.venv/bin/python3"
else
    PYTHON_CMD="python3"
fi

$PYTHON_CMD load_all_data.py $CLEAR_FLAG

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "================================================================================"
    echo -e "${GREEN}✓ ETL COMPLETED SUCCESSFULLY${NC}"
    echo "================================================================================"
    echo ""
    echo "Next steps:"
    echo "  1. View data in pgAdmin: http://localhost:5050"
    echo "     Email: admin@admin.com | Password: admin"
    echo ""
    echo "  2. Query the data:"
    echo "     docker-compose exec postgres psql -U postgres -d restaurant_analytics"
    echo ""
    echo "  3. Build your analytics/dashboard on top of the clean data!"
    echo ""
else
    echo ""
    echo "================================================================================"
    echo -e "${RED}✗ ETL FAILED${NC}"
    echo "================================================================================"
    exit 1
fi

