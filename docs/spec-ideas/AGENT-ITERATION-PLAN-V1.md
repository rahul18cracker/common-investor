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
1. Setup experimental folder structure
2. Install dependencies (langchain, deepagents, openai, tiktoken)
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
