from celery import Celery
import os


REDIS_HOST = os.getenv(
    "REDIS_HOST",
    "redis"
)


celery = Celery(
    "scraper",
    broker=f"redis://{REDIS_HOST}:6379/0",
    backend=f"redis://{REDIS_HOST}:6379/0",
    include=[
        "app.workers.tasks"
    ]
)


celery.conf.task_routes = {
    "app.workers.tasks.scrape_xkom": {
        "queue":"xkom"
    },

    "app.workers.tasks.scrape_morele": {
        "queue":"morele"
    },

    "app.workers.tasks.scrape_media": {
        "queue":"mediaexpert"
    }
}
