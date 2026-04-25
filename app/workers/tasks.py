import asyncio

from app.workers.celery_app import celery

from app.scrapers.xkom import (
    search_xkom_and_get_price
)

from app.scrapers.morele import (
    search_morele_and_get_price
)

from app.scrapers.mediaexpert import (
    search_mediaexpert_and_get_price
)



@celery.task(
    name="app.workers.tasks.scrape_xkom",
    queue="xkom"
)
def scrape_xkom(query):

    return asyncio.run(
        search_xkom_and_get_price(
            query
        )
    )



@celery.task(
    name="app.workers.tasks.scrape_morele",
    queue="morele"
)
def scrape_morele(query):

    return asyncio.run(
        search_morele_and_get_price(
            query
        )
    )



@celery.task(
    name="app.workers.tasks.scrape_media",
    queue="mediaexpert"
)
def scrape_media(query):

    return asyncio.run(
        search_mediaexpert_and_get_price(
            query
        )
    )
