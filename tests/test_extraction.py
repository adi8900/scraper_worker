"""Integration tests: compare HTML and API using the same synthetic offers."""
import asyncio
import pytest

from app.scrapers.catalog import price_float, scrape_catalog_page


def test_pln_price_parser():
    assert price_float("1 299,99 zł") == 1299.99
    assert price_float("2\u202f499,00 zł") == 2499.0


@pytest.mark.parametrize("shop", ["a", "b", "c"])
def test_html_matches_api(shop):
    api = asyncio.run(scrape_catalog_page(shop, 1, method="api", query="ryzen 7500f"))
    html = asyncio.run(scrape_catalog_page(shop, 1, method="html", query="ryzen 7500f"))
    assert api["count"] == html["count"] == 1
    p_api = api["products"][0]
    p_html = html["products"][0]
    assert p_api["product_id"] == p_html["product_id"] == 1
    assert p_api["price"] == p_html["price"]
    assert p_api["specs"] == p_html["specs"]
    assert p_api["sku"] == p_html["sku"]
    assert p_html["url"].endswith("/product/1")
