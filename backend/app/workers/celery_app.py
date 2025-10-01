from celery import Celery
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
celery_app = Celery(
    "ci",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['app.workers.tasks']
)

celery_app.conf.beat_schedule = {
    "snapshot-popular": {
        "task": "app.workers.tasks.snapshot_prices",
        "schedule": 6*60*60,
        "args": (["MSFT","AAPL","AMZN"],)
    },
    "evaluate-alerts-daily": {
        "task": "app.workers.tasks.run_alerts_eval",
        "schedule": 24*60*60
    }
}