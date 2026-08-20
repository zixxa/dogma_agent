"""
Celery-обвязка вокруг parser.fetch_and_store().

Требуется брокер — Redis (у вас уже есть в стеке):
    pip install celery redis

Запуск (два отдельных процесса, аналогично uvicorn/bot из прошлого разговора):
    celery -A tasks worker --loglevel=info
    celery -A tasks beat --loglevel=info

Для локальной разработки можно объединить в один процесс (НЕ для продакшена):
    celery -A tasks worker --beat --loglevel=info
"""

import os

from celery import Celery
from celery.schedules import crontab

from parser import fetch_and_store

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "dogma_parser",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.timezone = "Europe/Moscow"

celery_app.conf.beat_schedule = {
    "scrape-dogma-flats": {
        "task": "tasks.scrape_dogma_flats",
        "schedule": crontab(minute="*/30"),
    },
}


@celery_app.task(
    name="tasks.scrape_dogma_flats",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def scrape_dogma_flats(self) -> dict:
    try:
        total = fetch_and_store()
    except Exception as exc:
        raise self.retry(exc=exc)

    return {"saved": total}