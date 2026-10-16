import asyncio

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.services.query_parser import (
    product_matches_query,
)


def parse_price(v):

    return float(
        v.replace(",", ".")
    )


async def search_morele_and_get_price(
    query
):

    print(
        "\n=== MORELE START ==="
    )

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        page = await browser.new_page()

        url = (
            "https://www.morele.net/"
            "wyszukiwarka/,,,,,,,p,0,,,,/1/"
            f"?q={query.replace(' ', '+')}"
        )

        print(
            "URL:",
            url
        )

        await page.goto(
            url
        )

        await page.wait_for_load_state(
            "domcontentloaded"
        )

        await asyncio.sleep(2)

        html = await page.content()

        await browser.close()

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    products = soup.select(
        "div.cat-product"
    )

    offers = []

    checked = 0

    for p in products:

        if checked >= 15:
            break

        name = p.get(
            "data-product-name",
            ""
        )

        price = p.get(
            "data-product-price"
        )

        if not name or not price:
            continue

        print(
            "[MORELE]",
            name
        )

        # -------------------------------------------------
        # GŁÓWNY FILTR PRODUKTU
        # -------------------------------------------------

        if not product_matches_query(
            name,
            query
        ):
            continue

        checked += 1

        # -------------------------------------------------
        # LINK
        # -------------------------------------------------

        link = p.select_one(
            "a"
        )

        href = ""

        if link:

            href = link.get(
                "href",
                ""
            )

        if href.startswith("/"):
            href = (
                "https://www.morele.net"
                + href
            )

        # -------------------------------------------------
        # CENA
        # -------------------------------------------------

        numeric = parse_price(
            price
        )

        offers.append(
            {
                "price":
                    f"{price.replace('.', ',')} zł",

                "url":
                    href,

                "numeric":
                    numeric
            }
        )

    if not offers:
        return None

    best = min(
        offers,
        key=lambda x:
            x["numeric"]
    )

    return {
        "price":
            best["price"],

        "url":
            best["url"]
    }
