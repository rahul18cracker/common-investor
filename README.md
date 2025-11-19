# Common Investor — Rule #1 Financial Analysis Platform

A comprehensive financial analysis application implementing Phil Town's Rule #1 investing methodology. Analyze public companies using the Four Ms framework (Meaning, Moat, Management, Margin of Safety) with data sourced directly from SEC EDGAR filings.

## ✨ Features

- **📊 Financial Analysis**: Complete Rule #1 methodology implementation
- **📈 Interactive Dashboards**: Revenue, EPS, ROIC, and coverage ratio charts
- **🎯 Valuation Tools**: Sticker price, MOS, payback time, ten cap calculations
- **🏰 Four Ms Analysis**: Automated moat/management scoring + SEC filing extraction
- **📤 Export Options**: CSV metrics and JSON valuation exports
- **🔔 Alert System**: MOS threshold notifications
- **🏗️ Modern Architecture**: FastAPI + Next.js + PostgreSQL + Redis

## 🚀 Quick Start

### Option 1: 30-Second Setup
```bash
cp .env.example .env
# Edit .env: Set SEC_USER_AGENT="CommonInvestor/1.0 your-email@example.com"
docker compose up -d --build

# Access the application
# UI:  http://localhost:3000
# API: http://localhost:8080/api/v1/health
```

### Option 2: Try It Now
1. **Web Interface**: http://localhost:3000/company/MSFT
2. **Click "Ingest"** to fetch Microsoft's SEC data
3. **Wait 60 seconds**, then click "Reload"
4. **Explore** the complete financial analysis!

## 📖 Documentation

- **[Quick Start Guide](QUICK_START.md)** - Get running in 30 seconds
- **[Complete Run Guide](docs/RUNBOOK.md)** - Detailed setup, API docs, troubleshooting
- **[Functional Specifications](../docs/)** - Business logic and technical requirements

## 🏗️ Architecture

**Modular Monolith** ready for microservices:
- **Backend**: FastAPI + Python 3.11
- **Frontend**: Next.js + React + TypeScript
- **Database**: PostgreSQL with pgvector
- **Cache**: Redis
- **Workers**: Celery for background processing
- **Observability**: Jaeger tracing
- **Storage**: MinIO (S3-compatible)

## 🎯 Rule #1 Methodology

### Four Ms Framework
1. **Meaning** - Circle of competence analysis
2. **Moat** - Competitive advantage assessment (ROIC, margins)
3. **Management** - Capital allocation quality
4. **Margin of Safety** - Conservative valuation buffer

### Big Five Numbers
1. **ROIC** - Return on Invested Capital (target ≥15%)
2. **Revenue Growth** - CAGR across multiple windows
3. **EPS Growth** - Diluted earnings per share growth
4. **Owner Earnings** - Free cash flow (CFO - CapEx)
5. **Debt Ratios** - Interest coverage and leverage

### Valuation Methods
- **Sticker Price** - 10-year EPS projection discounted at 15%
- **MOS Price** - Sticker Price × (1 - MOS%)
- **Payback Time** - Years for owner earnings to return investment
- **Ten Cap** - Owner Earnings ÷ 0.10 valuation

## 🔧 Development

```bash
# Run tests
docker compose exec api pytest -v
docker compose exec ui npm run test:unit

# Development mode with hot reload
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Access containers
docker compose exec api bash
docker compose exec ui bash

# Install experimental research agent dependencies (optional)
cd backend
pip install -r requirements-research-agent.txt
```

### 📦 Dependency Management

The project uses **separate requirements files** for modularity:
- `backend/requirements.txt` - Core backend dependencies (FastAPI, SQLAlchemy, Celery)
- `backend/requirements-research-agent.txt` - Experimental LLM research agent (LangChain, DeepAgents)

See [RUNBOOK - Dependency Management](docs/RUNBOOK.md#-dependency-management) for detailed installation instructions.

## 📊 Sample Analysis Output

```json
{
  "valuation": {
    "sticker": 285.67,
    "mos_price": 142.84,
    "payback_years": 8,
    "ten_cap_price": 320.50
  },
  "fourm": {
    "moat": {"roic_avg": 0.18, "score": 0.85},
    "management": {"score": 0.72},
    "mos_recommendation": {"recommended_mos": 0.45}
  }
}
```

## 🆘 Support

- **Logs**: `docker compose logs api`
- **Health Check**: `curl http://localhost:8080/api/v1/health`
- **Debug Info**: `curl http://localhost:8080/api/v1/debug/modules`

---

**⚠️ Disclaimer**: This tool is for educational purposes only. Not investment advice. Always verify with primary sources (SEC filings).