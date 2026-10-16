from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.services.query_parser import (
    product_matches_query,
)


def parse_price(v):
    return float(
        v.replace("zł", "")
         .replace(",", ".")
         .replace(" ", "")
         .replace("\u202f", "")
    )


async def search_xkom_and_get_price(query):

    print("\n=== XKOM START ===")

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
            "https://www.x-kom.pl/szukaj?"
            f"q={query.replace(' ', '+')}"
            "&sort_by=price_asc"
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

        html = await page.content()

        await browser.close()

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    cards = soup.select(
        'div[class*="sc-"]'
    )

    best = None
    best_price = None
    checked = 0

    for card in cards:

        if checked >= 15:
            break

        # -------------------------------------------------
        # LINK PRODUKTU
        # -------------------------------------------------

        link = card.select_one(
            'a[href*="/p/"]'
        )

        # -------------------------------------------------
        # CENA
        # -------------------------------------------------

        price_el = card.select_one(
            'span[aria-label*="Cena"]'
        )

        if not link or not price_el:
            continue

        # -------------------------------------------------
        # NAZWA
        # -------------------------------------------------

        name = link.get_text(
            strip=True
        )

        if not name:
            continue

        print(
            "[XKOM]",
            name
        )

        # -------------------------------------------------
        # DOPASOWANIE PRODUKTU
        # -------------------------------------------------

        if not product_matches_query(
            name,
            query
        ):
            continue

        checked += 1

        # -------------------------------------------------
        # URL
        # -------------------------------------------------

        href = link.get(
            "href",
            ""
        )

        if href.startswith("/"):
            href = (
                "https://www.x-kom.pl"
                + href
            )

        # -------------------------------------------------
        # CENA
        # -------------------------------------------------

        price = (
            price_el
            .get("aria-label")
            .replace(
                "Cena:",
                ""
            )
            .strip()
        )

        try:
            numeric = parse_price(
                price
            )
        except (
            ValueError,
            AttributeError
        ):
            continue

        # -------------------------------------------------
        # NAJTAŃSZA OFERTA
        # -------------------------------------------------

        if (
            best_price is None
            or numeric < best_price
        ):

            best_price = numeric

            best = {
                "price": price,
                "url": href
            }

    print(
        "BEST:",
        best
    )

    return best
