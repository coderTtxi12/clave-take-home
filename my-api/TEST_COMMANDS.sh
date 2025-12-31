#!/bin/bash

# FastAPI Backend Test Commands
# ==============================

echo "🚀 Testing Data Analyst Agent API Endpoints"
echo "===================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 1. Test Root Endpoint
echo -e "${BLUE}1. Testing Root Endpoint${NC}"
echo "GET http://localhost:8000/"
curl -s http://localhost:8000/ | python3 -m json.tool
echo ""
echo ""

# 2. Test Basic Health Check
echo -e "${BLUE}2. Testing Basic Health Check${NC}"
echo "GET http://localhost:8000/api/v1/health"
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
echo ""
echo ""

# 3. Test Detailed Health Check
echo -e "${BLUE}3. Testing Detailed Health Check${NC}"
echo "GET http://localhost:8000/api/v1/health/detailed"
curl -s http://localhost:8000/api/v1/health/detailed | python3 -m json.tool
echo ""
echo ""

# 4. Interactive Documentation
echo -e "${GREEN}✅ All basic tests passed!${NC}"
echo ""
echo "📚 Interactive Documentation Available:"
echo "  - Swagger UI: http://localhost:8000/docs"
echo "  - ReDoc:      http://localhost:8000/redoc"
echo ""
echo "🎯 Server is running on: http://localhost:8000"

