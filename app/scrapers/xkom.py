import asyncio

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.services.query_parser import product_matches_query


def parse_price(v):
    return float(
        v.replace("zł", "")
         .replace(",", ".")
         .replace(" ", "")
         .replace("\u202f", "")
    )


async def search_xkom_and_get_price(query):

    print("\n=== XKOM START ===")

    max_pages = 5
    offers = []

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        page = await browser.new_page()

        for page_number in range(1, max_pages + 1):

            if page_number == 1:
                url = (
                    "https://www.x-kom.pl/szukaj?"
                    f"q={query.replace(' ', '+')}"
                    "&sort_by=price_asc"
                )
            else:
                url = (
                    "https://www.x-kom.pl/szukaj?"
                    f"page={page_number}"
                    "&sort_by=price_asc"
                    f"&q={query.replace(' ', '+')}"
                )

            print(
                f"\n[XKOM] STRONA {page_number}/{max_pages}"
            )

            print(
                "[XKOM] URL:",
                url
            )

            try:
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=30000
                )
            except Exception as e:
                print(
                    "[XKOM] Błąd page.goto():",
                    e
                )
                continue

            await asyncio.sleep(2)

            html = await page.content()

            soup = BeautifulSoup(
                html,
                "html.parser"
            )

            cards = soup.select(
                'div[class*="sc-"]'
            )

            print(
                "[XKOM] Elementów na stronie:",
                len(cards)
            )

            if not cards:
                print(
                    "[XKOM] Brak wyników - koniec."
                )
                break

            found_on_page = False

            for card in cards:

                # -----------------------------------------
                # LINK PRODUKTU
                # -----------------------------------------

                link = card.select_one(
                    'a[href*="/p/"]'
                )

                # -----------------------------------------
                # CENA
                # -----------------------------------------

                price_el = card.select_one(
                    'span[aria-label*="Cena"]'
                )

                if not link or not price_el:
                    continue

                # -----------------------------------------
                # NAZWA
                # -----------------------------------------

                name = link.get_text(
                    strip=True
                )

                if not name:
                    continue

                print(
                    "[XKOM]",
                    name
                )

                # -----------------------------------------
                # FILTR PRODUKTU
                # -----------------------------------------

                if not product_matches_query(
                    name,
                    query
                ):
                    continue

                found_on_page = True

                print(
                    "[XKOM] MATCH:",
                    name
                )

                # -----------------------------------------
                # URL
                # -----------------------------------------

                href = link.get(
                    "href",
                    ""
                )

                if href.startswith("/"):
                    href = (
                        "https://www.x-kom.pl"
                        + href
                    )

                # -----------------------------------------
                # CENA
                # -----------------------------------------

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
                    print(
                        "[XKOM] Nieprawidłowa cena:",
                        price
                    )
                    continue

                offers.append(
                    {
                        "price": price,
                        "url": href,
                        "numeric": numeric
                    }
                )

            if found_on_page:
                print(
                    "[XKOM] Znaleziono pasujący "
                    "produkt na stronie",
                    page_number
                )

            # Jeżeli strona ma mniej elementów niż
            # typowa strona wyników, prawdopodobnie
            # doszliśmy do końca.
            #
            # Nie przerywamy jednak tutaj na sztywno,
            # bo selektor sc-* może obejmować dodatkowe
            # elementy.

        await browser.close()

    # -----------------------------------------
    # BRAK OFERT
    # -----------------------------------------

    if not offers:

        print(
            "[XKOM] Nie znaleziono pasującego produktu"
        )

        return None

    # -----------------------------------------
    # NAJTAŃSZA OFERTA
    # -----------------------------------------

    best = min(
        offers,
        key=lambda x: x["numeric"]
    )

    print(
        "\n[XKOM] BEST:",
        best
    )

    return {
        "price": best["price"],
        "url": best["url"]
    }
