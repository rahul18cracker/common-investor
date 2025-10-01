# Common Investor - Quick Start Guide

## 🚀 30-Second Setup

```bash
# 1. Setup environment
cp .env.example .env
# Edit .env: Set SEC_USER_AGENT="CommonInvestor/1.0 your-email@example.com"

# 2. Start everything
docker compose up -d --build

# 3. Verify (wait 2-3 minutes for startup)
curl http://localhost:8080/api/v1/health
# Expected: {"status": "ok"}
```

## 🎯 Try It Out

### Web Interface
1. Open: http://localhost:3000/company/MSFT
2. Click "Ingest" button
3. Wait 60 seconds, click "Reload"
4. Explore the dashboard!

### API Testing
```bash
# Ingest company data
curl -X POST http://localhost:8080/api/v1/company/MSFT/ingest

# Wait 60 seconds, then get analysis
curl http://localhost:8080/api/v1/company/MSFT/metrics
curl http://localhost:8080/api/v1/company/MSFT/fourm
```

## 🔧 Common Commands

```bash
# Check status
docker compose ps

# View logs
docker compose logs api
docker compose logs ui

# Restart
docker compose restart api

# Clean restart
docker compose down -v && docker compose up -d --build
```

## 📊 What You'll See

- **Revenue/EPS Charts**: Historical financial trends
- **ROIC Analysis**: Return on invested capital over time
- **Valuation Tools**: Sticker price, MOS, payback time calculations
- **Four Ms Analysis**: Moat, management, meaning, margin of safety
- **Export Options**: CSV metrics, JSON valuations

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| Port in use | `lsof -i :8080` then kill process |
| API not responding | `docker compose restart api` |
| Frontend not loading | `docker compose restart ui` |
| Database issues | `docker compose restart postgres` |
| SEC rate limits | Wait 10 minutes, check .env file |

## 📖 Full Documentation

For detailed setup, API documentation, and troubleshooting: [docs/RUNBOOK.md](docs/RUNBOOK.md)

---

**Need help?** Check the logs: `docker compose logs api`
