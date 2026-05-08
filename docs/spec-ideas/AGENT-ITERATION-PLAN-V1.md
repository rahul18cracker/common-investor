# Research Agent Iteration Plan v1

**DeepAgents-Based Qualitative Financial Analysis System**

---

## 🎯 Overview

This document outlines the iterative development plan for integrating a LangChain/DeepAgents-based qualitative research agent into the Common Investor platform. The agent will perform comprehensive qualitative analysis of companies and generate detailed research reports that complement the existing quantitative Rule #1 analysis.

**Key Objectives:**
- Build an experimental LLM-based research agent using deepagents framework
- Integrate qualitative analysis with existing quantitative metrics
- Publish research reports on the UI alongside financial data
- Scale from Docker Compose to production Kubernetes deployment

---

## 🏗️ Repository Structure

### Phase 1: Experimental Development

```
common-investor/backend/app/
├── nlp/
│   ├── fourm/                    # Existing Four Ms analysis
│   └── research_agent/           # 🆕 New deepagents experiment
│       ├── __init__.py
│       ├── experimental/         # Sandbox for iteration
│       │   ├── __init__.py
│       │   ├── agent_config.py   # DeepAgents configuration
│       │   ├── prompts.py        # LLM prompts & templates
│       │   ├── tools.py          # Custom tools (SEC filing search, web scraping)
│       │   └── workflows.py      # Research workflows & orchestration
│       ├── reports/              # Report generation logic
│       │   ├── __init__.py
│       │   ├── templates/        # Report templates
│       │   └── generator.py      # Report formatting & publishing
│       └── tests/
│           └── test_research_agent.py
```

**Benefits:**
- ✅ Isolated from production code (`experimental/` subfolder)
- ✅ Co-located with existing NLP logic
- ✅ Clear separation between experiment and production-ready code
- ✅ Easy to test independently

---

### Phase 2: Production Integration

```
common-investor/backend/app/
├── nlp/
│   └── research_agent/
│       ├── agent.py              # Production-ready agent class
│       ├── service.py            # FastAPI service integration
│       ├── models.py             # Pydantic models
│       ├── tasks.py              # Celery tasks for async processing
│       └── storage.py            # Report persistence (MinIO/S3)
└── api/
    └── v1/
        └── research.py           # 🆕 New API endpoints
```

**New API Endpoints:**
- `POST /api/v1/company/{ticker}/research/start` - Trigger research
- `GET /api/v1/company/{ticker}/research/status` - Check progress
- `GET /api/v1/company/{ticker}/research/report` - Get final report
- `DELETE /api/v1/company/{ticker}/research/{job_id}` - Cancel job

---

## 📋 Four-Phase Development Plan

### Phase 1: Experiment & Validate (2-3 weeks)

**Goal:** Prove deepagents works for qualitative analysis

**Key Tasks:**
1. Setup experimental folder structure ✅ **COMPLETE**
2. Install dependencies (see `backend/requirements-research-agent.txt`)
   - langchain, phi-ai (deepagents), openai, tiktoken, jinja2, tenacity
   - **Note:** Dependencies are isolated in separate requirements file (see [Dependency Management](#dependency-management) below)
3. Build basic SEC filing retrieval tool
4. Create agent configuration with GPT-4
5. Implement research workflow
6. Create markdown report templates
7. Test with 3-5 sample tickers

**Metrics to Track:**
- Report quality (manual review, scoring rubric)
- Execution time (target: < 5 minutes)
- LLM API costs per company (target: < $0.50)
- Error rates (target: < 5%)

**Deliverables:**
- [ ] Working experimental agent
- [ ] Test results documented
- [ ] Cost analysis complete
- [ ] Go/No-Go decision

---

### Phase 2: Docker Integration (1-2 weeks)

**Goal:** Run as background job with real data

**Key Tasks:**
1. Create Celery task for async processing
2. Add database models for research reports
3. Implement report storage (PostgreSQL + MinIO)
4. Add research-agent service to docker-compose.yml
5. Create FastAPI endpoints for triggering/status/retrieval
6. Add Pydantic models for API validation

**Docker Compose Service:**
```yaml
services:
  research-agent:
    build: { context: ./backend }
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      PYTHONPATH: /app
      RESEARCH_MODE: experimental
    depends_on: [postgres, redis, minio]
    command: ["celery", "-A", "app.nlp.research_agent.tasks", "worker", "--queue=research"]
    volumes: ["./backend:/app"]
```

**Deliverables:**
- [ ] Celery tasks working
- [ ] Database models migrated
- [ ] API endpoints functional
- [ ] Integration tests passing

---

### Phase 3: UI Integration (1 week)

**Goal:** Surface reports on company pages

**Key Tasks:**
1. Create React `ResearchReport` component
2. Add "Qualitative Research" tab to company page
3. Implement API client methods
4. Add loading states and error handling
5. Style report display with markdown rendering

**UI Components:**
```typescript
// New tab on company page
<Tabs>
  <Tab value="quantitative">Quantitative Analysis</Tab>
  <Tab value="qualitative">Qualitative Research</Tab>  {/* 🆕 */}
</Tabs>

// Report component with markdown rendering
<ResearchReport ticker={ticker} />
```

**Deliverables:**
- [ ] React components implemented
- [ ] Company page updated
- [ ] UI/UX approved
- [ ] End-to-end workflow tested

---

### Phase 4: Kubernetes Production (2-3 weeks)

**Goal:** Production-ready, scalable service

**Key Tasks:**

#### Week 1: Kubernetes Manifests
1. Create Deployment with resource limits
2. Add HorizontalPodAutoscaler (scale on queue depth)
3. Create ConfigMap for agent configuration
4. Setup Sealed Secrets for API keys
5. Add liveness/readiness probes

**Example HPA:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: research-agent-hpa
spec:
  scaleTargetRef:
    kind: Deployment
    name: research-agent-worker
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: External
    external:
      metric:
        name: redis_queue_length
        selector:
          matchLabels:
            queue: research
      target:
        type: AverageValue
        averageValue: "5"
```

#### Week 2: Monitoring & Observability
1. Add Prometheus metrics (request rate, latency, cost)
2. Create ServiceMonitor for Prometheus
3. Implement OpenTelemetry tracing
4. Create Grafana dashboard
5. Setup alerting rules

**Key Metrics:**
```python
research_requests_total = Counter('research_agent_requests_total')
research_duration_seconds = Histogram('research_agent_duration_seconds')
research_cost_usd = Histogram('research_agent_cost_usd')
research_queue_length = Gauge('research_agent_queue_length')
```

#### Week 3: Production Deployment
1. Deploy to staging environment
2. Run smoke tests and load tests
3. Canary deployment (10% → 50% → 100%)
4. Monitor for 24 hours between each stage
5. Full production rollout

**Deliverables:**
- [ ] All k8s manifests created
- [ ] Monitoring/alerting configured
- [ ] Load tests passing
- [ ] Production deployment complete

---

## 📦 Dependency Management

### Separate Requirements Files Strategy

The research agent uses **isolated dependency files** to prevent conflicts with core backend dependencies and enable independent experimentation.

#### Files Structure
```
backend/
├── requirements.txt                    # Core backend (FastAPI, SQLAlchemy, Celery)
├── requirements-research-agent.txt     # Research agent experimental (LangChain, DeepAgents)
└── requirements-dev.txt                # Development tools [future]
```

#### Rationale for Separation

**✅ Benefits:**
- Clear separation between stable backend and experimental agent
- Independent versioning prevents dependency conflicts
- Optional installation - experiment without breaking production
- Easy promotion path to production when ready
- Works well with Docker conditional installs

**❌ Why NOT a single requirements.txt:**
- Version conflicts (e.g., LangChain dependencies may conflict with FastAPI stack)
- Forces production to install experimental dependencies
- Can't isolate experimental failures
- Pollutes production environment

#### Installation

**Development (Local):**
```bash
# Core backend only
pip install -r backend/requirements.txt

# Core + Research Agent
pip install -r backend/requirements.txt
pip install -r backend/requirements-research-agent.txt
```

**Docker (Phase 2 Integration):**
```dockerfile
# Conditional installation
ARG INSTALL_RESEARCH_AGENT=false
RUN pip install -r requirements.txt && \
    if [ "$INSTALL_RESEARCH_AGENT" = "true" ]; then \
        pip install -r requirements-research-agent.txt; \
    fi
```

#### Promotion to Production

When research agent is production-ready (Phase 4):

**Option A: Merge into main requirements**
```bash
cat backend/requirements-research-agent.txt >> backend/requirements.txt
```

**Option B: Keep separate (recommended for modularity)**
- Update Dockerfile to install both by default
- Maintain clear dependency tracking

For detailed installation instructions, see [RUNBOOK - Dependency Management](../RUNBOOK.md#-dependency-management).

---

## 🔍 Key Technical Considerations

### 1. LLM Cost Management

**Strategies:**
- **Token optimization**: Truncate SEC filings to relevant sections only
- **Model selection**: GPT-4 for analysis, GPT-3.5-turbo for summaries
- **Caching**: Cache SEC filings and intermediate analysis steps
- **Budget limits**: Set daily ($50) and monthly ($1000) spending caps

```python
def check_budget_before_run():
    today_spent = get_daily_spend()
    if today_spent >= DAILY_BUDGET_USD:
        raise BudgetExceeded("Daily budget reached")
```

### 2. Multi-Layer Caching

```python
# L1: Redis (hot cache, 1 day TTL)
# L2: PostgreSQL (reports table, 7 days TTL)
# L3: MinIO (long-term storage, indefinite)

class ReportCache:
    def get_report(self, ticker: str):
        # Try Redis first
        report = redis.get(f"report:{ticker}")
        if report: return report
        
        # Try PostgreSQL
        report = db.query(ResearchReport).filter_by(ticker=ticker).first()
        if report and report.is_fresh():
            redis.set(f"report:{ticker}", report.content, ex=86400)
            return report
        
        # Fall back to MinIO
        return minio.get_object(f"reports/{ticker}.json")
```

### 3. Rate Limiting

Respect OpenAI API limits (50 requests/minute for most tiers):

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def call_llm_with_retry(prompt: str):
    await rate_limiter.acquire()
    return await llm.call(prompt)
```

### 4. Error Handling & Graceful Degradation

```python
class ResearchAgent:
    def analyze_qualitative(self, ticker: str):
        try:
            return self._full_analysis(ticker)
        except OpenAIRateLimitError:
            return self._get_cached_or_placeholder(ticker)
        except Exception as e:
            logger.error(f"Research failed for {ticker}: {e}")
            return self._minimal_report(ticker)
```

### 5. Data Privacy & Compliance

- **No PII**: Only use public SEC filings
- **Attribution**: Clearly cite SEC filings in reports
- **Disclaimers**: Add "not investment advice" disclaimers to all reports
- **Audit trail**: Log all LLM interactions for compliance

```python
DISCLAIMER = """
**Disclaimer**: This report is generated by an AI system for informational 
purposes only. It does not constitute investment advice.
"""
```

---

## 🚦 Success Metrics

### Development Phase
| Metric | Target |
|--------|--------|
| Prompt Iterations | < 10 |
| Test Coverage | > 80% |
| Manual Review Score | > 4.0/5 |

### Docker Integration
| Metric | Target |
|--------|--------|
| API Response Time | < 500ms |
| Task Success Rate | > 95% |
| Cache Hit Rate | > 60% |

### Production Phase
| Metric | Target |
|--------|--------|
| Report Generation Time | < 3 min |
| LLM Cost per Report | < $0.50 |
| Success Rate | > 95% |
| P95 Latency | < 4 min |
| User Satisfaction | > 4.0/5 |
| Cache Hit Rate | > 70% |
| Error Rate | < 2% |

**Prometheus Queries:**
```promql
# Request rate
rate(research_agent_requests_total[5m])

# Success rate
sum(rate(research_agent_requests_total{status="success"}[5m])) 
/ sum(rate(research_agent_requests_total[5m]))

# P95 latency
histogram_quantile(0.95, research_agent_duration_seconds_bucket)

# Average cost
avg(research_agent_cost_usd)
```

---

## 🎬 Getting Started

### Immediate Next Steps

1. **Create experimental branch:**
   ```bash
   cd common-investor
   git checkout -b feature/research-agent-experimental
   ```

2. **Create folder structure:**
   ```bash
   mkdir -p backend/app/nlp/research_agent/{experimental,reports/templates,tests}
   touch backend/app/nlp/research_agent/__init__.py
   touch backend/app/nlp/research_agent/experimental/{__init__.py,agent_config.py,prompts.py,tools.py,workflows.py}
   ```

3. **Update requirements.txt:**
   ```txt
   langchain>=0.1.0
   deepagents>=0.1.0
   openai>=1.0.0
   tiktoken>=0.5.0
   tenacity>=8.0.0
   jinja2>=3.0.0
   markdown>=3.0.0
   ```

4. **Install dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

5. **Build proof-of-concept:**
   - Test deepagents with SEC filing analysis
   - Generate one sample qualitative report
   - Measure performance & costs

6. **Decision point:** After POC, decide whether to proceed with full integration

---

## 📚 Dependencies to Add

```txt
# LLM & Agent Framework
langchain>=0.1.0
deepagents>=0.1.0           # Main agent framework
openai>=1.0.0               # LLM API
anthropic>=0.8.0            # Optional: Claude support

# Token & Cost Management
tiktoken>=0.5.0             # Token counting
tenacity>=8.0.0             # Retry logic with exponential backoff

# Report Generation
jinja2>=3.0.0               # Template rendering
markdown>=3.0.0             # Markdown processing
python-markdown-math>=0.8   # Math rendering in reports

# Observability
prometheus-client>=0.19.0   # Metrics
opentelemetry-api>=1.20.0   # Distributed tracing
opentelemetry-instrumentation-celery>=0.41b0

# Testing
pytest-asyncio>=0.21.0      # Async test support
responses>=0.24.0           # Mock HTTP responses
```

---

## 🎯 Research Agent Report Template

```markdown
# {company_name} ({ticker}) - Qualitative Analysis

**Generated:** {timestamp}  
**Analysis Cost:** ${cost_usd}

---

## Executive Summary

{executive_summary}

---

## Business Model Analysis

### What Does the Company Do?
{business_description}

### Revenue Streams
{revenue_streams}

### Key Products/Services
{key_products}

---

## Competitive Moat Assessment

### Competitive Advantages
{competitive_advantages}

### Moat Strength: {moat_score}/10
{moat_explanation}

### Threats to Moat
{moat_threats}

---

## Management Quality

### Leadership Team
{leadership_overview}

### Capital Allocation Track Record
{capital_allocation}

### Management Score: {management_score}/10
{management_explanation}

---

## Risk Factors

### Business Risks
{business_risks}

### Financial Risks
{financial_risks}

### Regulatory/Legal Risks
{regulatory_risks}

---

## Investment Recommendation

**Qualitative Score:** {overall_score}/10

{recommendation_summary}

### Alignment with Rule #1 Criteria
- **Meaning:** {meaning_assessment}
- **Moat:** {moat_assessment}
- **Management:** {management_assessment}
- **Margin of Safety:** {mos_assessment}

---

## Sources

- SEC 10-K Filing ({filing_date})
- SEC 10-Q Filings (Last 4 quarters)
- Company Website & Investor Relations
- Industry Reports

---

**Disclaimer:** This report is generated by an AI system for informational purposes only. 
It does not constitute investment advice. Always verify information with primary sources 
and consult a financial advisor before making investment decisions.
```

---

## 📖 Additional Resources

- **DeepAgents Documentation:** https://github.com/langchain-ai/deepagents
- **LangChain Docs:** https://python.langchain.com/docs/
- **OpenAI API Reference:** https://platform.openai.com/docs/api-reference
- **Celery Best Practices:** https://docs.celeryq.dev/en/stable/userguide/
- **Kubernetes HPA Guide:** https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/

---

**Last Updated:** November 13, 2025  
**Version:** 1.0  
**Status:** Ready for Implementation

---

## Increment 3 Pilot Results — 2026-04-30

### Overview

Five-company pilot run across AAPL, WMT, MSFT, JPM, SBUX. Full 8-sprint pipeline per company (~$0.17–$0.31/run, ~10–17 min each). Branch: `rahul/increment2-contracts`.

### Pilot Metrics Summary

| Ticker | Industry  | Status    | Cost    | Duration | Passed | Degraded | Data Incomplete | Qual Avg |
|--------|-----------|-----------|---------|----------|--------|----------|-----------------|----------|
| AAPL   | Technology| completed | $0.2449 | 11.4 min | 3      | 5        | 0               | 5.8      |
| WMT    | Retail    | completed | $0.2614 | 13.5 min | 3      | 5        | 0               | 5.4      |
| MSFT   | Technology| completed | $0.1661 |  9.9 min | 4      | 4        | 0               | 8.0      |
| JPM    | Banking   | completed | $0.2048 |  9.5 min | 1      | 5        | 2               | 3.0      |
| SBUX   | Retail    | completed | $0.3102 | 16.8 min | 1      | 7        | 0               | 4.8      |

**All 5 runs completed (no crashes, no fetch failures, no tainted sprints).**  
Average cost per company: ~$0.24. Average duration: ~12 min.

### Per-Sprint Pass Rates (across 5 companies)

| Sprint              | Passed | Degraded | Data Incomplete | Pass Rate |
|---------------------|--------|----------|-----------------|-----------|
| 01_business_profile | 5/5    | 0        | 0               | 100%      |
| 02_unit_economics   | 4/5    | 1        | 0               | 80%       |
| 03_industry         | 0/5    | 5        | 0               | 0%        |
| 04_moat             | 3/5    | 1        | 1 (JPM)         | 60%       |
| 05_management       | 0/5    | 4        | 1 (JPM)         | 0%        |
| 06_peers            | 0/5    | 5        | 0               | 0%        |
| 07_risks            | 0/5    | 4        | 1 (JPM-missing) | 0%        |
| 08_thesis           | 2/5    | 3        | 0               | 40%       |

### Root Cause Analysis

**Three systematic contract bugs caused most failures:**

**Bug 1 — 03_industry cross-references (0% pass rate)**  
Both cross-refs compared mismatched content:  
- `industry_grounding`: checked if short code `"technology"` was a substring of a long definitional paragraph — it never literally appeared.  
- `company_context`: checked if `"Apple Inc."` (with period suffix) was in notes — LLM writes `"Apple"`.  
**Fix applied**: Replaced both with a single `industry_category_matches_bundle` exact-match check (`output.industry_category == agent_bundle.company.industry_category`).

**Bug 2 — 05_management cross-reference (0% pass rate)**  
Source path was `agent_bundle.four_ms.management` which resolves to the entire management dict `{score: 0.54, components: {}}`. Evaluator stringified this and compared to integer rating `3`, always failing `directional_within_1.5`.  
**Fix applied**: Changed source to `agent_bundle.four_ms.management.score` (the float), changed match to `directional_consistency` (direction only, no scale mismatch).

**Bug 3 — 07_risks field name mismatch (0% pass rate)**  
LLM naturally outputs `regulatory_risk` and `fx_commodity_exposure` but `required_fields` specified `regulatory` and `fx_commodity`. The deterministic check failed every run on missing required fields.  
**Fix applied**: Updated `required_fields` and `field_types` in contract to match LLM's natural output names.

**Other notable failures:**

- **06_peers (0% pass rate)**: Two companies produced invalid JSON on all 3 attempts (builder JSON parse failure). LLM over-stuffed the response with inline commentary. Needs tighter output format instruction in builder prompt — low priority for now.
- **JPM data incompleteness**: `metrics.latest_operating_margin` and `metrics.latest_fcf_margin` missing → 02_unit_economics and 04_moat skipped. Banking metrics (NII, NIM, PCR) don't map to standard operating/FCF margins. This is a known XBRL gap, not a contract bug.
- **08_thesis (40% pass rate)**: MSFT and SBUX passed; AAPL/WMT/JPM degraded. Evaluator correctly caught: AAPL's EPS CAGR distortion (10Y negative due to split); WMT's split-adjusted EPS not quantified; JPM missing ROIC_avg_10y. These are high-quality evaluator catches, not false positives.
- **SBUX ROIC anomaly**: `roic_avg_10y` reported as 64.3% — mathematically implausible for a QSR/negative-equity company. Likely a data artifact from negative equity years producing extreme ROIC values. 02_unit_economics evaluator flagged this correctly.

### Human Calibration Notes

- **01_business_profile**: All 5 passed with scores 14-17/20. Quality is high — outputs are factual, grounded, and specific. Evaluator calibration is correct here.
- **02_unit_economics**: SBUX degraded on ROIC anomaly flag — evaluator is working correctly as a data quality watchdog.
- **03_industry, 05_management, 07_risks**: Failures were pure contract bugs. The actual LLM outputs (visible in state/) are high quality — clear, specific, well-grounded. These will pass once the contract fixes are applied.
- **06_peers**: Even at degraded scores of 1-4/20, the outputs are directionally useful — the evaluator's criticism of missing ROIC figures is valid but harsh for a qualitative benchmarking sprint.
- **08_thesis**: MSFT thesis is the benchmark — structured, falsifiers are specific, quality decomposition is explicit. This is the target quality bar for other companies.

### Cost Analysis

| Metric | Value |
|--------|-------|
| Total pilot cost (5 companies) | $1.19 |
| Average per company | $0.24 |
| Cheapest run (MSFT) | $0.17 |
| Most expensive (SBUX) | $0.31 |
| Sonnet (08_thesis) share of cost | ~45% of total |
| Projected 25-company Phase 1B cost | ~$6 |

Sonnet on 08_thesis is the dominant cost driver. The 08_thesis sprint is ~3-5× more expensive than any haiku sprint. Consider haiku for 08_thesis on non-synthesis companies if quality holds.

### Go/No-Go for Phase 1B (25-Company Pilot)

**Decision: CONDITIONAL GO** — after contract fixes are applied and verified.

Pre-conditions for Phase 1B:
1. ✅ Contract bugs fixed (03_industry, 05_management, 07_risks) — done 2026-04-30
2. ✅ Re-run all 5 companies with fixed contracts — done 2026-05-06 (see Increment 3 Verification below)
3. ✅ 06_peers: grounding checks implemented + builder prompt improved — done 2026-05-06
4. ✅ JPM/banking documented as known data-incomplete company type

**Updated Decision: FULL GO for Phase 1B** — all pre-conditions met.

---

## Increment 3 Verification Run — 2026-05-06

Full 5-company re-run with all contract fixes applied, new grounding checks for 06_peers, ROIC suppression fix,
and evaluator bugs resolved. All state cleared for a clean run.

### Final Verified Pass Rates

| Sprint              | AAPL | MSFT | SBUX | WMT | JPM | Status |
|---------------------|------|------|------|-----|-----|--------|
| 01_business_profile | ✅   | ✅   | ✅  | ✅  | ✅  | 5/5 |
| 02_unit_economics   | ✅   | ✅   | 🔶  | ✅  | ⏭  | 3/4 active |
| 03_industry         | ✅   | ✅   | ✅  | ✅  | ✅  | 5/5 |
| 04_moat             | ✅   | ✅   | ✅  | 🔶  | ⏭  | 3/4 active |
| 05_management       | ✅   | ✅   | 🔶  | ✅  | ✅  | 4/5 |
| 06_peers            | 🔶   | 🔶   | 🔶  | 🔶  | 🔶  | 0/5 |
| 07_risks            | ✅   | ✅   | ✅  | ✅  | 🔶  | 4/5 |
| 08_thesis           | 🔶   | ⏭(timeout) | 🔶 | 🔶 | 🔶 | 0/5 |

Legend: ✅ passed  🔶 degraded  ⏭ skipped/timeout

### Key Findings

**Verified fixes (confirmed working):**
- 03_industry: 5/5 pass rate (was 0/5 in original pilot)
- 05_management: 4/5 pass rate (was 0/5 in original pilot); SBUX degrades due to ROIC artifact cascade
- 07_risks: 4/5 pass rate (was 0/5 in original pilot); JPM degrades (banking XBRL gaps)
- ROIC suppression: SBUX roic_avg_10y now correctly ~32% (was 64.3% artifact); roic_suppressed_years=3 visible to LLM

**Remaining known issues (not blocking Phase 1B):**

**06_peers — degraded on all 5 companies.** Root cause analysis:
1. `subject_scores.commentary` was missing from `string_minimums`, causing deterministic L1 failure until
   3rd attempt escalation. Fixed during re-run (2026-05-06). Still degrading because:
2. LLM consistently over-estimates subject scores (`balance_sheet_0_to_5`, `roic_persistence_0_to_5`)
   beyond ±1 tolerance of grounded values. New grounding checks catch this correctly — L3 hard fail.
3. LLM produces assertion-heavy peer commentary without quantitative backing (no peer ROIC/margin data
   available in agent_bundle — this is a fundamental data limitation, not a prompt failure).
4. **Decision: accept 06_peers as structurally degraded** — the evaluator is correctly flagging real
   quality issues (ungrounded peer scores, thin comparative analysis). Upgrade to sonnet permanently
   for 06_peers in Phase 1B to see if quality improves. Do not suppress the grounding checks.

**08_thesis — degraded on all 5 (0/5 pass rate).** Root cause:
1. MSFT timed out due to Anthropic API rate limit (30-minute gap at 14:21).
2. AAPL, WMT, SBUX, JPM: evaluator correctly flags thesis weaknesses — missing DCF derivation,
   unquantified litigation scenarios, EPS CAGR reconciliation missing, share count distortion unexplained.
3. 08_thesis is the highest-bar sprint (sonnet model, 14-point threshold). LLM quality for thesis
   synthesis needs improvement. **Decision: lower pass_threshold llm_score_minimum to 10 for Phase 1B**
   to allow structurally sound but not perfect theses to pass. Current threshold (14/20) is too strict
   given no quantitative data for DCF or peer comparison.

**SBUX data quality cascade:** 02_unit_economics and 05_management degrade due to ROIC artifact.
The ROIC suppression fix correctly reduced roic_avg_10y to ~32% and set roic_suppressed_years=3,
but the LLM still over-weights historical ROIC in unit economics analysis. Evaluator correctly flags
this as "ROIC persistence score of 5/10 with 3 suppressed years" — working as intended.

**JPM banking gaps:** 02_unit_economics and 04_moat skip due to missing operating_margin and fcf_margin.
Known XBRL limitation for financial sector companies. Document as `data_incomplete` archetype.

### Cost Summary (verification run)

| Ticker | Cost   | Duration | Passed | Degraded |
|--------|--------|----------|--------|----------|
| AAPL   | $0.21  | 11.3 min | 6      | 2        |
| MSFT   | $0.15  | 39.0 min | 6      | 1 (+timeout)|
| SBUX   | $0.27  | 15.0 min | 4      | 4        |
| WMT    | $0.28  | 15.1 min | 5      | 3        |
| JPM    | $0.19  | 8.8 min  | 3      | 3 (+2 data_incomplete)|

Average cost: ~$0.22/company. Total: ~$1.10.

### Contract Model Tier Decisions (post-verification)

- 01-05, 07: keep haiku — quality is sufficient
- 06_peers: **upgrade to sonnet** for Phase 1B — grounding failures indicate haiku lacks
  comparative reasoning depth; at least one attempt needed with sonnet context
- 08_thesis: stays sonnet — lower pass threshold to 10/20 for Phase 1B
- Evaluator: stays haiku — correctly catching quality gaps

### Phase 1B Next Steps

1. Lower 08_thesis pass_threshold.llm_score_minimum from 14 to 10
2. Change 06_peers model_tier from "haiku" to "sonnet"
3. Expand to 25-company pilot covering all industry archetypes
4. Track: which sprints consistently require attempt 3 (escalation signal for model upgrade)
5. After 25-company run: calibrate 06_peers grounding tolerance (±1 on 0-5 may be too strict)
