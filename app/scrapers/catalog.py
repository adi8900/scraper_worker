"""Uniform extraction interface for three intentionally different test-store HTML layouts."""
import os
import json
import re
import time
from urllib.parse import urlencode, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


BASE = os.getenv("SHOP_BASE_URL", "http://test-shops:8080").rstrip("/")
PUBLIC_BASE = os.getenv("SHOP_PUBLIC_BASE_URL", "http://localhost:8090").rstrip("/")
SHOPS = {
    "a": {"url": os.getenv("SHOP_A_URL", BASE + "/shop-a"),
          "card": "article.product", "name": ".product-name",
          "price": ".price", "link": ".product-link"},
    "b": {"url": os.getenv("SHOP_B_URL", BASE + "/shop-b"),
          "card": "div.offer-card", "name": ".offer-title",
          "price": ".offer-price", "link": ".offer-link"},
    "c": {"url": os.getenv("SHOP_C_URL", BASE + "/shop-c"),
          "card": "li.catalog-item", "name": ".catalog-title",
          "price": ".catalog-price", "link": ".catalog-link"},
}


def price_float(raw):
    value = re.sub(r"[^\d,.]", "", raw.replace("\xa0", "").replace("\u202f", ""))
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    return round(float(value), 2)


def public_url(shop, listing_id):
    return f"{PUBLIC_BASE}/shop-{shop}/product/{listing_id}"


async def scrape_catalog_page(shop, page_number, method="html", query="", per_page=40):
    shop = shop.lower()
    if shop not in SHOPS:
        raise ValueError(f"Nieznany sklep: {shop}")
    if page_number < 1 or not 1 <= per_page <= 100:
        raise ValueError("Nieprawidłowy numer strony lub rozmiar strony")
    if method not in ("html", "api"):
        raise ValueError("Dozwolone metody: html, api")

    started = time.perf_counter()
    url = SHOPS[shop]["url"]
    arguments = urlencode({"page": page_number, "per_page": per_page, "q": query})
    products = []

    if method == "api":
        endpoint = f"{url.split('/shop-')[0]}/api/shop-{shop}/products?{arguments}"
        async with httpx.AsyncClient(timeout=35) as client:
            response = await client.get(endpoint)
            response.raise_for_status()
            data = response.json()
        for item in data["products"]:
            products.append({
                "product_id": int(item["product_id"]),
                "listing_id": int(item["id"]),
                "name": item["name"], "category": item.get("category"),
                "sku": item.get("sku"),
                "price": float(item["price"]), "shop": shop,
                "url": public_url(shop, item["id"]),
                "specs": item.get("specs", {}),
            })
        total = data.get("total")
    else:
        address = url + "?" + arguments
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True, args=["--no-sandbox"])
            try:
                page = await browser.new_page()
                response = await page.goto(address, wait_until="domcontentloaded", timeout=35000)
                if response is None or response.status != 200:
                    raise RuntimeError(f"HTTP {response.status if response else 'missing'}: {address}")
                soup = BeautifulSoup(await page.content(), "html.parser")
                config = SHOPS[shop]
                for card in soup.select(config["card"]):
                    title = card.select_one(config["name"])
                    price = card.select_one(config["price"])
                    link = card.select_one(config["link"])
                    if not title or not price or not link:
                        continue
                    try:
                        product_id = int(card["data-product-id"])
                        listing_id = int(card["data-listing-id"])
                        numeric = price_float(price.get_text(" ", strip=True))
                    except (KeyError, ValueError, TypeError):
                        continue
                    products.append({
                        "product_id": product_id, "listing_id": listing_id,
                        "name": title.get_text(" ", strip=True),
                        "sku": card.get("data-sku"),
                        "specs": json.loads(card.get("data-specs", "{}")),
                        "price": numeric, "shop": shop,
                        "url": public_url(shop, listing_id),
                    })
            finally:
                await browser.close()
        total = None

    return {
        "shop": shop, "page": page_number, "method": method,
        "count": len(products), "total": total, "products": products,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
    }


async def search_shop(shop, query, method="html"):
    result = await scrape_catalog_page(shop, 1, method=method, query=query, per_page=100)
    return {"shop": shop, "offers": result["products"],
            "count": result["count"], "method": method,
            "duration_ms": result["duration_ms"]}
