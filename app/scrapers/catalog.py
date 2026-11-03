
import os
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


SHOPS = {
    "a": {
        "url": os.getenv("SHOP_A_URL", "http://ryzen:8090/shop-a"),
        "card": "article.product",
        "name": ".product-name",
        "price": ".price",
        "link": ".product-link",
    },
    "b": {
        "url": os.getenv("SHOP_B_URL", "http://ryzen:8090/shop-b"),
        "card": "div.offer-card",
        "name": ".offer-title",
        "price": ".offer-price",
        "link": ".offer-link",
    },
    "c": {
        "url": os.getenv("SHOP_C_URL", "http://ryzen:8090/shop-c"),
        "card": "li.catalog-item",
        "name": ".catalog-title",
        "price": ".catalog-price",
        "link": ".catalog-link",
    },
}


async def scrape_catalog_page(shop, page_number):
    shop = shop.lower()

    if shop not in SHOPS:
        raise ValueError(f"Nieznany sklep: {shop}")

    if page_number < 1:
        raise ValueError("Numer strony musi być dodatni")

    config = SHOPS[shop]

    url = config["url"] + "?" + urlencode({
        "page": page_number,
    })

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox"],
        )

        try:
            page = await browser.new_page()

            response = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000,
            )

            if response is None or response.status != 200:
                raise RuntimeError(
                    f"Błąd HTTP podczas pobierania {url}"
                )

            soup = BeautifulSoup(
                await page.content(),
                "html.parser",
            )

            products = []

            for card in soup.select(config["card"]):
                name_el = card.select_one(config["name"])
                price_el = card.select_one(config["price"])
                link_el = card.select_one(config["link"])

                if not name_el or not price_el or not link_el:
                    continue

                name = name_el.get_text(" ", strip=True)
                price_text = price_el.get_text(" ", strip=True)

                try:
                    price = float(
                        price_text
                        .replace("zł", "")
                        .replace("\xa0", "")
                        .replace("\u202f", "")
                        .replace(" ", "")
                        .replace(",", ".")
                    )
                except ValueError:
                    continue

                products.append({
                    "name": name,
                    "price": price,
                    "url": urljoin(
                        config["url"],
                        link_el.get("href", ""),
                    ),
                    "shop": shop,
                })

            return {
                "shop": shop,
                "page": page_number,
                "count": len(products),
                "products": products,
            }

        finally:
            await browser.close()
