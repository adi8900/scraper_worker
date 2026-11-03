import os
from celery import Celery

REDIS_HOST = os.getenv("REDIS_HOST", "redis")

celery = Celery(
    "scraper",
    broker=f"redis://{REDIS_HOST}:6379/0",
    backend=f"redis://{REDIS_HOST}:6379/0",
    include=["app.workers.tasks"]
)

celery.conf.task_routes = {
    "app.workers.tasks.scrape_xkom": {
        "queue": "xkom"
    },
    "app.workers.tasks.scrape_morele": {
        "queue": "morele"
    },
    "app.workers.tasks.scrape_media": {
        "queue": "mediaexpert"
    },
    "app.workers.tasks.scrape_shop_a": {
        "queue": "shop_a"
    },
    "app.workers.tasks.scrape_shop_b": {
        "queue": "shop_b"
    },
    "app.workers.tasks.scrape_shop_c": {
        "queue": "shop_c"
    },
}
