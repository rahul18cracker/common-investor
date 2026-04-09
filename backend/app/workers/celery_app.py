from celery import Celery

from app.core.config import settings

celery_app = Celery("ci", broker=settings.redis_url, backend=settings.redis_url, include=["app.workers.tasks"])

celery_app.conf.beat_schedule = {
    "snapshot-popular": {
        "task": "app.workers.tasks.snapshot_prices",
        "schedule": 6 * 60 * 60,
        "args": (["MSFT", "AAPL", "AMZN"],),
    },
    "evaluate-alerts-daily": {"task": "app.workers.tasks.run_alerts_eval", "schedule": 24 * 60 * 60},
}
