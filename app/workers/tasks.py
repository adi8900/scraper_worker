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

from app.scrapers.shop_a import search_shop_a_and_get_price
from app.scrapers.shop_b import search_shop_b_and_get_price
from app.scrapers.shop_c import search_shop_c_and_get_price
from app.scrapers.catalog import scrape_catalog_page

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

@celery.task(
    name="app.workers.tasks.scrape_shop_a",
    queue="shop_a"
)
def scrape_shop_a(query):
    return asyncio.run(
        search_shop_a_and_get_price(query)
    )

@celery.task(
    name="app.workers.tasks.scrape_shop_b",
    queue="shop_b"
)
def scrape_shop_b(query):
    return asyncio.run(
        search_shop_b_and_get_price(query)
    )


@celery.task(
    name="app.workers.tasks.scrape_shop_c",
    queue="shop_c"
)
def scrape_shop_c(query):
    return asyncio.run(
        search_shop_c_and_get_price(query)
    )

@celery.task(
    name="app.workers.tasks.scrape_catalog",
    queue="catalog",
)
def scrape_catalog(shop, page_number):
    return asyncio.run(
        scrape_catalog_page(shop, page_number)
    )