from celery import Celery
import os

REDIS_HOST = os.getenv("REDIS_HOST", "192.168.1.133")

celery = Celery(
    "scraper",
    broker=f"redis://{REDIS_HOST}:6379/0",
    backend=f"redis://{REDIS_HOST}:6379/0"
)

celery.conf.task_routes = {
    "tasks.scrape_xkom": {"queue": "xkom"},
    "tasks.scrape_morele": {"queue": "morele"},
    "tasks.scrape_media": {"queue": "mediaexpert"},
}

import tasks
