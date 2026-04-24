from celery_app import celery
import asyncio

from scraper import (
    search_xkom_and_get_price,
    search_morele_and_get_price,
    search_mediaexpert_and_get_price
)

@celery.task
def scrape_xkom(query):
    return asyncio.run(search_xkom_and_get_price(query))

@celery.task
def scrape_morele(query):
    return asyncio.run(search_morele_and_get_price(query))

@celery.task
def scrape_media(query):
    return asyncio.run(search_mediaexpert_and_get_price(query))
