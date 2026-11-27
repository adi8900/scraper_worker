"""Celery tasks. All execution nodes consume the same queue for horizontal scaling."""
import asyncio

from app.workers.celery_app import celery
from app.scrapers.catalog import scrape_catalog_page, search_shop


@celery.task(name="app.workers.tasks.scrape_shop", queue="scraping")
def scrape_shop(shop, query, method="html"):
    return asyncio.run(search_shop(shop, query, method))


@celery.task(name="app.workers.tasks.scrape_catalog", queue="catalog")
def scrape_catalog(shop, page_number, method="html"):
    return asyncio.run(scrape_catalog_page(shop, page_number, method))


# Compatibility names for existing clients; the queues still share workers.
@celery.task(name="app.workers.tasks.scrape_shop_a", queue="scraping")
def scrape_shop_a(query):
    return asyncio.run(search_shop("a", query))


@celery.task(name="app.workers.tasks.scrape_shop_b", queue="scraping")
def scrape_shop_b(query):
    return asyncio.run(search_shop("b", query))


@celery.task(name="app.workers.tasks.scrape_shop_c", queue="scraping")
def scrape_shop_c(query):
    return asyncio.run(search_shop("c", query))
