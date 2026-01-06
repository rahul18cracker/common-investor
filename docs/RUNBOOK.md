# Common Investor - Complete Run Guide

A comprehensive step-by-step guide to run the Common Investor application for Rule #1 financial analysis.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Detailed Setup](#detailed-setup)
4. [Using the Application](#using-the-application)
5. [API Testing](#api-testing)
6. [Troubleshooting](#troubleshooting)
7. [Development](#development)

---

## 🔧 Prerequisites

### Required Software
- **Docker Desktop** (or Docker Engine + Docker Compose)
  - Download: https://www.docker.com/products/docker-desktop/
  - Minimum version: Docker 20.10+, Compose 2.0+
- **Git** (to clone the repository)
- **Web Browser** (Chrome, Firefox, Safari, Edge)

### System Requirements
- **RAM**: 4GB minimum, 8GB recommended
- **Disk Space**: 2GB free space
- **Network**: Internet connection for SEC data ingestion

### Required Ports (must be free)
- `3000` - Frontend (Next.js)
- `8080` - Backend API (FastAPI)
- `5432` - PostgreSQL database
- `6379` - Redis cache
- `9000` - MinIO object storage
- `9001` - MinIO console
- `16686` - Jaeger tracing UI

---

## 🚀 Quick Start

### 1. Clone and Setup
```bash
# Clone the repository
git clone <repository-url>
cd common-investor

# Copy environment configuration
cp .env.example .env

# Edit .env file with your details (see configuration section below)
nano .env  # or use your preferred editor
```

### 2. Start All Services
```bash
# Build and start all containers
docker compose up -d --build

# Check all services are running
docker compose ps
```

### 3. Verify Installation
```bash
# Check API health
curl http://localhost:8080/api/v1/health

# Open UI in browser
open http://localhost:3000
```

**Expected Response**: `{"status": "ok"}` from API, and the Common Investor homepage should load.

---

## ⚙️ Detailed Setup

### Environment Configuration

Edit the `.env` file with the following required settings:

```bash
# SEC EDGAR API (REQUIRED)
SEC_USER_AGENT="CommonInvestor/1.0 your-email@example.com"

# Database
POSTGRES_USER=ci
POSTGRES_PASSWORD=ci_pass
POSTGRES_DB=ci_db

# Object Storage
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin

# Optional: External Price Feed
# PRICE_FEED_PROVIDER=alpha_vantage
# ALPHA_VANTAGE_API_KEY=your_key_here
```

**⚠️ Important**: Replace `your-email@example.com` with your actual email address. The SEC requires a valid User-Agent for API access.

### Step-by-Step Startup

#### 1. Start Infrastructure Services
```bash
# Start database and cache first
docker compose up -d postgres redis minio

# Wait for services to be ready (30-60 seconds)
docker compose logs postgres | grep "ready to accept connections"
```

#### 2. Run Database Migrations
```bash
# Start API container to run migrations
docker compose up -d api

# Check migration logs
docker compose logs api | grep "alembic"
```

#### 3. Start All Services
```bash
# Start remaining services
docker compose up -d

# Verify all containers are running
docker compose ps
```

**Expected Output**: All services should show "Up" status.

#### 4. Health Checks
```bash
# API Health
curl http://localhost:8080/api/v1/health
# Expected: {"status": "ok"}

# Database Connection
curl http://localhost:8080/api/v1/debug/modules
# Expected: JSON with module file paths

# Frontend
curl -I http://localhost:3000
# Expected: HTTP 200 OK
```

---

## 💼 Using the Application

### Web Interface (Recommended)

1. **Open Browser**: Navigate to http://localhost:3000
2. **Search Company**: Go to http://localhost:3000/company/MSFT
3. **Ingest Data**: Click the "Ingest" button to fetch SEC data
4. **Wait for Processing**: Ingestion takes 30-60 seconds
5. **Reload Page**: Click "Reload" to see the analysis

### Complete Workflow Example

#### Step 1: Ingest Company Data
```bash
# Start ingestion for Microsoft
curl -X POST http://localhost:8080/api/v1/company/MSFT/ingest

# Check ingestion status (wait 30-60 seconds)
curl http://localhost:8080/api/v1/company/MSFT
```

#### Step 2: View Financial Metrics
```bash
# Get growth metrics and ratios
curl http://localhost:8080/api/v1/company/MSFT/metrics

# Get time series data for charts
curl http://localhost:8080/api/v1/company/MSFT/timeseries
```

#### Step 3: Run Valuation Analysis
```bash
# Run default valuation scenario
curl -X POST http://localhost:8080/api/v1/company/MSFT/valuation \
  -H "Content-Type: application/json" \
  -d '{"mos_pct": 0.5, "g": 0.12, "pe_cap": 25, "discount": 0.15}'
```

#### Step 4: Analyze Four Ms
```bash
# Get Moat, Management, and MOS analysis
curl http://localhost:8080/api/v1/company/MSFT/fourm

# Extract business description from 10-K
curl -X POST http://localhost:8080/api/v1/company/MSFT/fourm/meaning/refresh
```

#### Step 5: Export Results
```bash
# Export metrics as CSV
curl http://localhost:8080/api/v1/company/MSFT/export/metrics.csv > msft_metrics.csv

# Export valuation as JSON
curl "http://localhost:8080/api/v1/company/MSFT/export/valuation.json?mos_pct=0.5" > msft_valuation.json
```

### Using the Web Interface

#### Dashboard Features
- **Company Search**: Enter ticker symbol (e.g., MSFT, AAPL, GOOGL)
- **Interactive Charts**: Revenue, EPS, ROIC, Coverage ratios over time
- **Valuation Sliders**: Adjust growth rate, PE cap, discount rate, MOS percentage
- **Four Ms Analysis**: 
  - **Meaning**: Business description from SEC filings
  - **Moat**: ROIC persistence and margin stability scores
  - **Management**: Capital allocation quality metrics
  - **Margin of Safety**: Dynamic MOS recommendations
- **Export Options**: Download CSV metrics or JSON valuations

#### Navigation
- **Home**: http://localhost:3000
- **Company Analysis**: http://localhost:3000/company/{TICKER}
- **Examples**: 
  - Microsoft: http://localhost:3000/company/MSFT
  - Apple: http://localhost:3000/company/AAPL
  - Google: http://localhost:3000/company/GOOGL

---

## 🧪 API Testing

### Core Endpoints

#### Company Management
```bash
# Search and basic info
GET /api/v1/company/{ticker}

# Ingest SEC data
POST /api/v1/company/{ticker}/ingest
```

#### Database Seeding
```bash
# List all companies in database
GET /api/v1/companies

# Check seeding status (how many companies loaded)
GET /api/v1/seed/status

# Seed database with default tickers (MSFT, AAPL, GOOGL, KO, PG, JNJ, V, BRK-B, CAT, COST, HD, UNH)
POST /api/v1/seed

# Seed database with specific tickers
POST /api/v1/seed
Content-Type: application/json
{"tickers": ["TSLA", "AMD", "NVDA"]}
```

**Example seeding workflow:**
```bash
# Check current status
curl http://localhost:8080/api/v1/seed/status | jq

# Seed with default tickers (runs in background)
curl -X POST http://localhost:8080/api/v1/seed | jq

# Seed with custom tickers
curl -X POST http://localhost:8080/api/v1/seed \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["TSLA", "AMD", "NVDA"]}' | jq

# List all loaded companies
curl http://localhost:8080/api/v1/companies | jq
```

**Note:** Auto-seeding runs on first startup if `AUTO_SEED=true` (default) and the database is empty. Set `AUTO_SEED=false` in `.env` to disable.

#### Financial Analysis
```bash
# Growth metrics (CAGR, ratios)
GET /api/v1/company/{ticker}/metrics

# Time series data for charts
GET /api/v1/company/{ticker}/timeseries

# Valuation scenarios
POST /api/v1/company/{ticker}/valuation
Content-Type: application/json
{
  "mos_pct": 0.5,
  "g": 0.12,
  "pe_cap": 25,
  "discount": 0.15
}
```

#### Four Ms Analysis
```bash
# Complete Four Ms analysis
GET /api/v1/company/{ticker}/fourm

# Refresh business description
POST /api/v1/company/{ticker}/fourm/meaning/refresh
```

#### Exports
```bash
# CSV metrics export
GET /api/v1/company/{ticker}/export/metrics.csv

# JSON valuation export
GET /api/v1/company/{ticker}/export/valuation.json?mos_pct=0.5
```

#### Alerts Management
```bash
# Create alert
POST /api/v1/company/{ticker}/alerts
Content-Type: application/json
{"rule_type": "price_below_mos", "threshold": 0.05}

# List alerts
GET /api/v1/company/{ticker}/alerts

# Toggle alert
PATCH /api/v1/alerts/{alert_id}
Content-Type: application/json
{"enabled": false}

# Delete alert
DELETE /api/v1/alerts/{alert_id}
```

### Sample API Workflow
```bash
# 1. Ingest company data
curl -X POST http://localhost:8080/api/v1/company/AAPL/ingest

# 2. Wait for processing (30-60 seconds)
sleep 60

# 3. Get company summary
curl http://localhost:8080/api/v1/company/AAPL | jq

# 4. Get financial metrics
curl http://localhost:8080/api/v1/company/AAPL/metrics | jq

# 5. Run valuation
curl -X POST http://localhost:8080/api/v1/company/AAPL/valuation \
  -H "Content-Type: application/json" \
  -d '{"mos_pct": 0.5}' | jq

# 6. Get Four Ms analysis
curl http://localhost:8080/api/v1/company/AAPL/fourm | jq

# 7. Extract business meaning
curl -X POST http://localhost:8080/api/v1/company/AAPL/fourm/meaning/refresh | jq
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Port Already in Use
```bash
# Check what's using the port
lsof -i :8080

# Kill the process or change ports in docker-compose.yml
```

#### 2. Database Connection Issues
```bash
# Check PostgreSQL logs
docker compose logs postgres

# Restart database
docker compose restart postgres

# Reset database (⚠️ destroys data)
docker compose down -v
docker compose up -d
```

#### 3. SEC API Rate Limiting
```bash
# Check API logs for rate limit errors
docker compose logs api | grep "429"

# Wait 10 minutes and retry
# Ensure SEC_USER_AGENT is properly set in .env
```

#### 4. Frontend Not Loading
```bash
# Check UI logs
docker compose logs ui

# Rebuild frontend
docker compose up -d --build ui

# Check if API is accessible from frontend
docker compose exec ui curl http://api:8080/api/v1/health
```

#### 5. Ingestion Failures
```bash
# Check worker logs
docker compose logs worker

# Check if company ticker is valid
curl "https://data.sec.gov/api/xbrl/company_tickers.json" | jq '.[] | select(.ticker=="MSFT")'

# Retry ingestion
curl -X POST http://localhost:8080/api/v1/company/MSFT/ingest
```

### Service Status Commands
```bash
# Check all services
docker compose ps

# View logs for specific service
docker compose logs api
docker compose logs ui
docker compose logs worker

# Restart specific service
docker compose restart api

# Rebuild and restart
docker compose up -d --build api
```

### Data Verification
```bash
# Check database contents
docker compose exec postgres psql -U ci -d ci_db -c "SELECT ticker, name FROM company LIMIT 5;"

# Check Redis cache
docker compose exec redis redis-cli keys "*"

# Check MinIO storage
open http://localhost:9001  # MinIO console
```

---

## 📦 Dependency Management

### Research Agent Experimental Dependencies

The Common Investor platform uses **separate requirements files** to isolate experimental research agent dependencies from core backend dependencies. This approach provides:

- **Clear separation** between stable backend and experimental agent code
- **Independent versioning** of dependencies to avoid conflicts
- **Optional installation** for experimentation without breaking production
- **Easy promotion path** when research agent moves to production

#### Requirements Files Structure

```
backend/
├── requirements.txt                    # Core backend dependencies (FastAPI, SQLAlchemy, Celery)
├── requirements-research-agent.txt     # Research agent experimental dependencies (LangChain, DeepAgents)
└── requirements-dev.txt                # Development tools (pytest, black, mypy) [future]
```

#### Installation Instructions

**Option 1: Install Core Backend Only**
```bash
# For standard backend development
cd backend
pip install -r requirements.txt
```

**Option 2: Install Backend + Research Agent**
```bash
# For research agent experimentation
cd backend
pip install -r requirements.txt
pip install -r requirements-research-agent.txt
```

**Option 3: Docker with Research Agent**
```bash
# Build with research agent dependencies
docker compose build --build-arg INSTALL_RESEARCH_AGENT=true

# Standard build (without research agent)
docker compose build
```

#### Research Agent Dependencies

Key packages in `requirements-research-agent.txt`:
- **langchain** - LLM application framework
- **phi-ai** - DeepAgents orchestration framework
- **openai** - OpenAI API client
- **tiktoken** - Token counting for cost tracking
- **jinja2** - Template rendering for reports
- **tenacity** - Retry logic for API resilience

#### Production Promotion Path

When research agent moves from experimental to production:

1. **Merge dependencies** into main requirements.txt:
   ```bash
   cat backend/requirements-research-agent.txt >> backend/requirements.txt
   ```

2. **Or keep separate** for modularity:
   - Update Dockerfile to install both by default
   - Maintain separate files for clear dependency tracking

#### Dependency Conflicts

If you encounter version conflicts between backend and research agent dependencies:

1. **Identify conflict**: Run `pip check` after installation
2. **Resolve in isolation**: Test research agent in separate virtual environment
3. **Update constraints**: Pin conflicting packages to compatible versions
4. **Document resolution**: Add comments in requirements files explaining version pins

---

## 👨‍💻 Development

### Running Tests
```bash
# Backend tests
docker compose exec api bash -lc "pytest -v"

# Frontend tests
docker compose exec ui bash -lc "npm run test:unit"

# Integration tests
docker compose exec api bash -lc "pytest tests/test_fourm_integration.py -v"
```

### Development Mode
```bash
# Run with hot reload for development
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Access containers for debugging
docker compose exec api bash
docker compose exec ui bash
```

### Monitoring and Observability
```bash
# Jaeger tracing UI
open http://localhost:16686

# MinIO console
open http://localhost:9001

# Database admin (if needed)
docker compose exec postgres psql -U ci -d ci_db
```

### Useful Development Commands
```bash
# View real-time logs
docker compose logs -f api

# Execute commands in containers
docker compose exec api python -c "from app.metrics.compute import cagr; print(cagr(100, 200, 5))"

# Database migrations
docker compose exec api bash -lc "alembic revision --autogenerate -m 'description'"
docker compose exec api bash -lc "alembic upgrade head"

# Clear all data and restart fresh
docker compose down -v
docker compose up -d --build
```

---

## 📊 Expected Results

After successful setup and ingestion, you should see:

### Web Interface
- **Dashboard**: Interactive charts showing revenue, EPS, ROIC trends
- **Valuation Panel**: Sticker price, MOS price, payback time, ten cap calculations
- **Four Ms Panel**: Moat/management scores, MOS recommendations, business descriptions
- **Export Links**: Working CSV and JSON downloads

### API Responses
- **Metrics**: CAGR calculations, ROIC series, owner earnings
- **Valuation**: Sticker price ~$25-50 range for quality companies
- **Four Ms**: Scores between 0-1, MOS recommendations 30-70%
- **Meaning**: Business descriptions extracted from 10-K Item 1

### Performance Expectations
- **Cold Start**: 2-3 minutes for full system startup
- **Ingestion**: 30-60 seconds per company
- **Analysis**: <2 seconds for metrics/valuation calculations
- **UI Load**: <3 seconds for cached data

---

## 🆘 Getting Help

### Log Locations
```bash
# Application logs
docker compose logs api
docker compose logs ui
docker compose logs worker

# System logs
docker compose logs postgres
docker compose logs redis
```

### Debug Endpoints
```bash
# Module status
curl http://localhost:8080/api/v1/debug/modules

# Health check
curl http://localhost:8080/api/v1/health
```

### Common Success Indicators
- ✅ All containers show "Up" status
- ✅ API health endpoint returns `{"status": "ok"}`
- ✅ Frontend loads without errors
- ✅ Company ingestion completes successfully
- ✅ Charts display financial data
- ✅ Valuation calculations return reasonable numbers

---

**🎉 Congratulations!** You now have a fully functional Rule #1 investing analysis platform running locally.