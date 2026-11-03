
import os
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

SHOP_C_URL = os.getenv(
    "SHOP_C_URL",
    "http://ryzen:8090/shop-c"
)


async def search_shop_c_and_get_price(query):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )

        try:
            page = await browser.new_page()

            params = urlencode({"q": query})
            url = f"{SHOP_C_URL}?{params}"

            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000
            )

            soup = BeautifulSoup(
                await page.content(),
                "html.parser"
            )

            offers = []

            for card in soup.select("li.catalog-item"):
                name_el = card.select_one(".catalog-title")
                price_el = card.select_one(".catalog-price")
                link_el = card.select_one(".catalog-link")

                if not name_el or not price_el:
                    continue

                name = name_el.get_text(" ", strip=True)
                price_text = price_el.get_text(" ", strip=True)

                terms = query.lower().split()

                if not all(term in name.lower() for term in terms):
                    continue

                try:
                    numeric_price = float(
                        price_text
                        .replace("zł", "")
                        .replace("\xa0", "")
                        .replace("\u202f", "")
                        .replace(" ", "")
                        .replace(",", ".")
                    )
                except ValueError:
                    continue

                offers.append({
                    "price": price_text,
                    "numeric_price": numeric_price,
                    "url": urljoin(
                        SHOP_C_URL,
                        link_el.get("href", "")
                    ) if link_el else url
                })

            if not offers:
                return None

            cheapest = min(
                offers,
                key=lambda item: item["numeric_price"]
            )

            return {
                "price": cheapest["price"],
                "url": cheapest["url"]
            }

        finally:
            await browser.close()
