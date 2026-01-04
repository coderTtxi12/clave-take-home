# Natural Language Dashboard Generator

A production-ready AI-powered dashboard that transforms natural language queries into dynamic visualizations from restaurant analytics data. Built for the Clave Engineering Take-Home Assessment.

## 🎯 Overview

This system allows restaurant owners to ask questions in plain English like:
- *"Show me sales comparison between Downtown and Airport locations"*
- *"What were my top 5 selling products last week?"*
- *"Graph hourly sales for Friday vs Saturday at all stores"*

**The system automatically:**
1. Parses the natural language query
2. Generates Python code to query the database
3. Executes the code in a secure sandbox
4. Creates appropriate visualizations (charts, tables, metrics)
5. Returns interactive widgets to the dashboard

---

## 🏗️ Architecture

### System Components

```
┌─────────────────┐
│   Frontend       │  Next.js Dashboard (TypeScript)
│   (Port 3000)    │  - Natural language input
└────────┬────────┘  - Dynamic visualization rendering
         │
         │ HTTP/REST
         ▼
┌─────────────────┐
│   Backend API   │  FastAPI (Python)
│   (Port 8000)   │  - Query processing
└────────┬────────┘  - Session management
         │
         │ OpenAI API
         ▼
┌─────────────────┐
│  Coding Agent   │  Agentic Loop
│                 │  - Code generation
│                 │  - Tool execution
│                 │  - Context compression
└────────┬────────┘
         │
         │ Code Execution
         ▼
┌─────────────────┐
│ Code Executor   │  Isolated Docker Container
│ (Port 8001)     │  - Secure code execution
│                 │  - Database access
└────────┬────────┘
         │
         │ SQL Queries
         ▼
┌─────────────────┐
│   Supabase      │  PostgreSQL Database
│   (Production)  │  - Normalized restaurant data
└─────────────────┘
```

### Data Flow

1. **User Query** → Frontend sends natural language query
2. **LLM Processing** → Backend uses OpenAI to interpret query
3. **Code Generation** → Agent generates Python code with database queries
4. **Code Execution** → Isolated executor runs code safely
5. **Data Retrieval** → Executor queries Supabase database
6. **Visualization** → Results formatted as charts/tables
7. **Response** → Frontend renders interactive widgets

---

## 🤖 The Coding Agent: Core Innovation

### Why a Coding Agent?

Traditional approaches map queries directly to SQL, but this is brittle:
- **Limited flexibility**: Can't handle complex data transformations
- **No iteration**: Can't refine queries based on results
- **Fixed patterns**: Struggles with ambiguous or novel requests

**My solution**: An agentic system that **generates and executes Python code** dynamically.

### How It Works

The coding agent uses a **ReAct (Reasoning + Acting) loop**:

```
┌─────────────────────────────────────────────────────────┐
│ 1. User Query: "Compare sales by location"            │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 2. LLM Reasoning:                                       │
│    - Need to query orders table                        │
│    - Group by location                                  │
│    - Calculate total sales                             │
│    - Compare results                                   │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Code Generation:                                     │
│    ```python                                            │
│    import pandas as pd                                  │
│    from db_helper import get_db_connection              │
│                                                         │
│    conn = get_db_connection()                           │
│    df = pd.read_sql("""                                 │
│        SELECT location_name,                            │
│               SUM(total_amount) as sales                │
│        FROM orders                                      │
│        GROUP BY location_name                           │
│    """, conn)                                           │
│    print(df.to_json())                                  │
│    ```                                                  │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 4. Code Execution (Isolated Sandbox)                    │
│    - Runs in Docker container                           │
│    - Limited permissions                                │
│    - Database read-only access                         │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Result Processing:                                   │
│    - Parse JSON output                                  │
│    - Determine chart type (bar, line, pie, etc.)        │
│    - Generate visualization                             │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 6. Response to User:                                    │
│    - Interactive chart widget                           │
│    - Text summary                                       │
│    - Data table (if applicable)                         │
└─────────────────────────────────────────────────────────┘
```

### Agentic Loop Details

The agent can iterate multiple times:

1. **Initial Query** → Generate code
2. **Execute Code** → Get results
3. **Analyze Results** → If incomplete or error:
   - **Refine code** based on error messages
   - **Adjust query** based on data structure
   - **Retry execution**
4. **Final Output** → Return visualization

**Why this works better:**
- **Adaptive**: Adjusts approach based on actual data
- **Self-correcting**: Fixes errors automatically
- **Flexible**: Can handle unexpected data structures
- **Powerful**: Full Python ecosystem available (pandas, matplotlib, etc.)

---

## 🧠 Context Compression: Managing Long Conversations

### The Problem

As users ask multiple questions, the conversation history grows:
- Each message adds tokens to the LLM context
- OpenAI has token limits (e.g., 60,000 tokens)
- Long histories become expensive and slow
- **But**: We need to remember past context for follow-up questions

### The Solution: Intelligent Compression

Instead of truncating history, we **compress it intelligently**:

```
┌─────────────────────────────────────────────────────────┐
│ Before Compression:                                      │
│ - 50 messages                                            │
│ - 45,000 tokens                                          │
│ - Full conversation history                              │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼ (When >70% of token limit)
┌─────────────────────────────────────────────────────────┐
│ Compression Process:                                    │
│ 1. Identify compressible messages (early in history)   │
│ 2. Send to LLM with compression prompt                 │
│ 3. Extract structured snapshot:                        │
│    - Overall goal                                        │
│    - Key knowledge                                       │
│    - File system state                                   │
│    - Recent actions                                      │
│    - Current plan                                        │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ After Compression:                                      │
│ - 2 messages (snapshot + acknowledgment)                │
│ - ~2,000 tokens                                          │
│ - All essential context preserved                        │
│ - Recent messages kept in full                           │
└─────────────────────────────────────────────────────────┘
```

### Why This Approach?

**Traditional truncation** (keep last N messages):
- ❌ Loses important early context
- ❌ User might reference something from earlier
- ❌ Agent "forgets" its own decisions

**My compression approach**:
- ✅ Preserves essential information
- ✅ Maintains user goals and constraints
- ✅ Keeps recent context in full detail
- ✅ Reduces token usage by ~95%

### Compression Threshold

We compress when usage exceeds **70% of token limit** (42,000 / 60,000 tokens):
- **Why 70%?** Leaves room for new queries and responses
- **What gets compressed?** Early messages (oldest first)
- **What stays?** Recent messages and tool results

---

## 📊 Data Architecture

### Source Data

The system processes **6 JSON files** from 3 different POS systems:

| Source | Files | Challenge |
|--------|-------|-----------|
| **Toast POS** | `toast_pos_export.json` | Single nested structure |
| **DoorDash** | `doordash_orders.json` | Delivery-specific fields |
| **Square POS** | 4 files (catalog, orders, payments, locations) | Split across multiple files |

**Data Quality Issues:**
- Inconsistent product names ("Hash Browns" vs "Hashbrowns")
- Typos ("Griled Chiken", "expresso")
- Category variations ("🍔 Burgers" vs "Burgers")
- Different date/time formats

### Normalized Schema

We designed a unified schema that handles all sources:

```
locations (id, name, address, ...)
    │
    ├── orders (id, location_id, order_date, order_type, ...)
    │       │
    │       ├── order_items (id, order_id, product_id, quantity, price, ...)
    │       │
    │       └── payments (id, order_id, payment_type, amount, ...)
    │
    └── products (id, location_id, name, category, normalized_name, ...)
```

**Why this design?**
- **Normalized**: Reduces data duplication
- **Flexible**: Handles different order types (dine-in, delivery, pickup)
- **Queryable**: Optimized for analytics queries
- **Extensible**: Easy to add new data sources

### ETL Process

1. **Extract**: Parse JSON files with source-specific logic
2. **Transform**: 
   - Normalize product names (fuzzy matching)
   - Standardize dates/times
   - Convert currencies
   - Handle missing fields
3. **Load**: Insert into Supabase with referential integrity

**ETL Functions** (PostgreSQL):
- `normalize_product_name()`: Fuzzy matching for product names
- `calculate_order_totals()`: Aggregations
- `detect_duplicate_orders()`: Data quality checks

---

## 🚀 Easy Setup (Local Development)

### Prerequisites

- Docker & Docker Compose
- Git

### Quick Start

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd clave-take-home

# 2. Create .env file (copy from .env.example)
cp .env.example .env
# Edit .env with your:
# - Supabase credentials (if using production DB)
# - OpenAI API key

# 3. Start all services
docker-compose up -d

# 4. Run database migrations
cd my-api
./run_alembic_migrations.sh

# 5. Install ETL functions
./install_etl_functions.sh

# 6. Load data
./load_data.sh

# 7. Access the application
# Frontend: http://localhost:3000
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | Next.js dashboard |
| Backend API | 8000 | FastAPI server |
| Code Executor | 8001 | Isolated Python executor |
| Redis | 6379 | Session storage |
| PostgreSQL | 5432 | Local database (if not using Supabase) |

### Database Setup

**Option A: Local PostgreSQL (Docker)**
- Already included in `docker-compose.yml`
- No additional setup needed

**Option B: Supabase (Production)**
1. Create project at [supabase.com](https://supabase.com)
2. Get connection string from Settings → Database
3. Update `.env` with Supabase credentials
4. Use `docker-compose.prod.yml` instead

---

## 📝 Key Scripts

### Database Migrations

```bash
./my-api/run_alembic_migrations.sh
```

**What it does:**
- Runs Alembic migrations to create/update schema
- Handles both local PostgreSQL and Supabase
- Automatically detects database type from `.env`

**Why Alembic?**
- Version control for schema changes
- Reproducible deployments
- Rollback capability

### ETL Functions Installation

```bash
./my-api/install_etl_functions.sh
```

**What it does:**
- Installs PostgreSQL functions for data normalization
- Functions: `normalize_product_name()`, `calculate_order_totals()`, etc.

**Why PostgreSQL functions?**
- **Performance**: Runs close to data (no network overhead)
- **Consistency**: Same logic for ETL and queries
- **Reusability**: Can be called from Python or SQL

### Data Loading

```bash
./my-api/load_data.sh
```

**What it does:**
1. Parses all 6 JSON files
2. Cleans and normalizes data
3. Inserts into database
4. Validates data integrity

**ETL Process:**
- **Toast**: Single file → orders, items, payments
- **DoorDash**: Orders → normalized format
- **Square**: 4 files → unified schema

---

## 🛠️ Technology Stack

### Frontend
- **Next.js 14** (App Router) - React framework
- **TypeScript** - Type safety
- **Recharts** - Chart library
- **Tailwind CSS** - Styling

### Backend
- **FastAPI** - Python web framework
- **OpenAI API** - LLM for code generation
- **SQLAlchemy** - ORM for database
- **Alembic** - Database migrations

### Infrastructure
- **Docker** - Containerization
- **Supabase** - PostgreSQL database (production)
- **Redis** - Session management
- **Docker Compose** - Local development

### Why These Choices?

**FastAPI over Flask/Django:**
- Async support for concurrent requests
- Automatic API documentation
- Type hints for better IDE support

**Next.js App Router:**
- Server components for better performance
- Built-in API routes (though we use separate backend)
- Excellent TypeScript support

**Supabase:**
- Real PostgreSQL (not a toy database)
- Easy to evaluate schema design
- Production-ready from day one

---

## 🎨 Design Decisions

### 1. Separate Code Executor Service

**Why?** Security and isolation.

- Code execution is **dangerous** (arbitrary Python code)
- Isolated Docker container prevents:
  - File system access
  - Network access (except database)
  - Resource exhaustion
- **Alternative considered**: In-process execution → Rejected (too risky)

### 2. Agentic Loop vs Direct SQL

**Why agentic?** Flexibility and adaptability.

- Can handle ambiguous queries
- Self-corrects errors
- Can use full Python ecosystem (pandas, matplotlib)
- **Alternative considered**: Query templates → Too rigid

### 3. Context Compression

**Why compress instead of truncate?** Preserves important context.

- User goals and constraints remembered
- Agent's own decisions preserved
- Recent context kept in full
- **Alternative considered**: Simple truncation → Loses too much

### 4. Normalized Database Schema

**Why normalized?** Data integrity and query flexibility.

- Single source of truth for products/locations
- Easy to add new data sources
- Efficient for analytics queries
- **Alternative considered**: Denormalized → Too much duplication

---

## 📈 What Makes This Production-Ready

1. **Error Handling**: Comprehensive try/catch with user-friendly messages
2. **Security**: Isolated code execution, input validation
3. **Scalability**: Stateless API, Redis for sessions
4. **Monitoring**: Structured logging, health checks
5. **Database**: Proper migrations, indexes, constraints
6. **Documentation**: Code comments, API docs, README

---

## 🔮 Future Improvements

Given more time, we would:

1. **Caching**: Cache query results for common questions
2. **Query Optimization**: Analyze and optimize generated SQL
3. **Multi-user Support**: User authentication and data isolation
4. **Advanced Visualizations**: More chart types, custom styling
5. **Query History**: Save and replay previous queries
6. **Data Refresh**: Automated ETL pipeline for new data

---

**Built with ❤️ for Clave Engineering Assessment**
