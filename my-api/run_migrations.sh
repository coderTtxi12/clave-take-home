#!/bin/bash

# Restaurant Analytics Database Migration Script
# This script runs all migrations in order

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Database connection parameters
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-restaurant_analytics}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"

# Migration directory
MIGRATIONS_DIR="./migrations"

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Restaurant Analytics Migrations${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# Check if PostgreSQL is reachable
echo -e "${YELLOW}Checking database connection...${NC}"
export PGPASSWORD=$DB_PASSWORD
if ! psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c '\q' 2>/dev/null; then
    echo -e "${RED}ERROR: Cannot connect to PostgreSQL${NC}"
    echo -e "${RED}Make sure the database is running: docker-compose up -d${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Database connection successful${NC}"
echo ""

# Create database if it doesn't exist
echo -e "${YELLOW}Checking if database exists...${NC}"
if ! psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
    echo -e "${YELLOW}Creating database: $DB_NAME${NC}"
    psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME;"
    echo -e "${GREEN}✓ Database created${NC}"
else
    echo -e "${GREEN}✓ Database exists${NC}"
fi
echo ""

# Enable required PostgreSQL extensions
echo -e "${YELLOW}Enabling PostgreSQL extensions...${NC}"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;" 2>/dev/null || true
echo -e "${GREEN}✓ Extensions enabled${NC}"
echo ""

# Run migrations in order
echo -e "${YELLOW}Running migrations...${NC}"
echo ""

MIGRATION_FILES=(
    "001_create_core_tables.sql"
    "002_create_order_items_and_payments.sql"
    "003_create_indexes_and_views.sql"
    "004_seed_reference_data.sql"
)

for migration in "${MIGRATION_FILES[@]}"; do
    migration_path="$MIGRATIONS_DIR/$migration"
    
    if [ ! -f "$migration_path" ]; then
        echo -e "${RED}ERROR: Migration file not found: $migration_path${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Running: $migration${NC}"
    
    if psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$migration_path" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $migration completed${NC}"
    else
        echo -e "${RED}✗ $migration failed${NC}"
        echo -e "${RED}Check the error messages above${NC}"
        exit 1
    fi
    echo ""
done

# Verify migration success
echo -e "${YELLOW}Verifying migrations...${NC}"

# Count tables
TABLE_COUNT=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';" | xargs)
echo -e "Tables created: ${GREEN}$TABLE_COUNT${NC}"

# Count materialized views
MV_COUNT=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM pg_matviews WHERE schemaname = 'public';" | xargs)
echo -e "Materialized views created: ${GREEN}$MV_COUNT${NC}"

# Count locations
LOCATION_COUNT=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM locations;" | xargs)
echo -e "Locations seeded: ${GREEN}$LOCATION_COUNT${NC}"

# Count categories
CATEGORY_COUNT=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM categories;" | xargs)
echo -e "Categories seeded: ${GREEN}$CATEGORY_COUNT${NC}"

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Migration completed successfully!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "Database: ${GREEN}$DB_NAME${NC}"
echo -e "Host: ${GREEN}$DB_HOST:$DB_PORT${NC}"
echo -e "User: ${GREEN}$DB_USER${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Load data from JSON sources"
echo -e "2. Run: ${GREEN}SELECT refresh_all_materialized_views();${NC}"
echo -e "3. Start building your API and dashboard"
echo ""
echo -e "${YELLOW}To connect to the database:${NC}"
echo -e "${GREEN}psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME${NC}"
echo ""

# Optional: pgAdmin access info
if [ "$1" == "--show-pgadmin" ]; then
    echo -e "${YELLOW}pgAdmin Access:${NC}"
    echo -e "URL: ${GREEN}http://localhost:5050${NC}"
    echo -e "Email: ${GREEN}admin@restaurant.local${NC}"
    echo -e "Password: ${GREEN}admin${NC}"
    echo -e ""
    echo -e "${YELLOW}To start pgAdmin:${NC}"
    echo -e "${GREEN}docker-compose --profile tools up -d${NC}"
    echo ""
fi

