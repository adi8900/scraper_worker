import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    REDIS_URL = f"redis://{os.getenv('REDIS_HOST', 'redis')}:6379/0"

celery = Celery(
    "scraper", broker=REDIS_URL, backend=REDIS_URL,
    include=["app.workers.tasks"],
)
celery.conf.update(
    task_routes={
        "app.workers.tasks.scrape_shop": {"queue": "scraping"},
        "app.workers.tasks.scrape_shop_a": {"queue": "scraping"},
        "app.workers.tasks.scrape_shop_b": {"queue": "scraping"},
        "app.workers.tasks.scrape_shop_c": {"queue": "scraping"},
        "app.workers.tasks.scrape_catalog": {"queue": "catalog"},
    },
    worker_prefetch_multiplier=1,
    task_track_started=True,
    result_expires=3600,
)
