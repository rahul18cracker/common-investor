from app.workers.celery_app import celery_app
from app.ingest.sec import ingest_companyfacts_richer_by_ticker
from app.alerts.engine import snapshot_price_for_ticker, evaluate_alerts

def enqueue_ingest(ticker: str):
    ingest_company.delay(ticker)

@celery_app.task(name="app.workers.tasks.ingest_company")
def ingest_company(ticker: str):
    res = ingest_companyfacts_richer_by_ticker(ticker)
    print(f"Ingested {res}")

@celery_app.task(name="app.workers.tasks.snapshot_prices")
def snapshot_prices(tickers: list[str]):
    for t in tickers:
        snapshot_price_for_ticker(t)

@celery_app.task(name="app.workers.tasks.run_alerts_eval")
def run_alerts_eval():
    return evaluate_alerts()