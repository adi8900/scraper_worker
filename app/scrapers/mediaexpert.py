import asyncio
import random

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.services.query_parser import (
    USER_AGENTS,
    product_matches_query,
    parse_price,
)


def price_to_float(v):
    return float(
        v.replace("zł", "")
         .replace(",", ".")
         .replace(" ", "")
         .replace("\u202f", "")
    )


async def search_mediaexpert_and_get_price(query):

    print("\n=== MEDIA START ===")

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

        context = await browser.new_context(
            user_agent=random.choice(
                USER_AGENTS
            )
        )

        page = await context.new_page()

        for page_number in range(1, max_pages + 1):

            url = (
                "https://www.mediaexpert.pl/search?"
                "query[menu_item]="
                f"&query[querystring]={query.replace(' ', '+')}"
            )

            if page_number > 1:
                url += (
                    f"&page={page_number}"
                )

            print(
                f"\n[MEDIA] STRONA {page_number}/{max_pages}"
            )

            print(
                "[MEDIA] URL:",
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
                    "[MEDIA] Błąd page.goto():",
                    e
                )
                continue

            await asyncio.sleep(2)

            # -----------------------------------------
            # PRZEWIŃ, ŻEBY DOCIĄGNĄĆ ZAWARTOŚĆ
            # -----------------------------------------

            await page.mouse.wheel(
                0,
                4000
            )

            await asyncio.sleep(1)

            final_url = page.url

            print(
                "[MEDIA] FINAL URL:",
                final_url
            )

            html = await page.content()

            soup = BeautifulSoup(
                html,
                "html.parser"
            )

            # -----------------------------------------
            # BEZPOŚREDNIA STRONA PRODUKTU
            # -----------------------------------------

            if "/search?" not in final_url:

                name_el = soup.select_one(
                    "h1"
                )

                if not name_el:
                    print(
                        "[MEDIA] Brak nazwy produktu "
                        "na stronie docelowej"
                    )
                    continue

                name = name_el.get_text(
                    strip=True
                )

                print(
                    "[MEDIA] PRODUKT:",
                    name
                )

                if not product_matches_query(
                    name,
                    query
                ):
                    print(
                        "[MEDIA] Produkt nie pasuje:",
                        name
                    )
                    continue

                price_el = soup.select_one(
                    "div.main-price"
                )

                if not price_el:
                    continue

                price = parse_price(
                    price_el.get(
                        "aria-label"
                    )
                )

                if not price:
                    continue

                offers.append(
                    {
                        "price": price,
                        "url": final_url,
                        "numeric": price_to_float(
                            price
                        )
                    }
                )

                print(
                    "[MEDIA] MATCH:",
                    name
                )

                # Po redirectcie nie ma sensu
                # przechodzić dalej po stronach.
                break

            # -----------------------------------------
            # WYNIKI WYSZUKIWANIA
            # -----------------------------------------

            products = soup.select(
                "div.offer-box"
            )

            print(
                "[MEDIA] Produktów na stronie:",
                len(products)
            )

            if not products:
                print(
                    "[MEDIA] Brak produktów - koniec."
                )
                break

            found_on_page = False

            for product in products:

                name_el = product.select_one(
                    "h3.name a"
                )

                if not name_el:
                    continue

                name = name_el.get_text(
                    strip=True
                )

                print(
                    "[MEDIA]",
                    name
                )

                # -------------------------------------
                # FILTR PRODUKTU
                # -------------------------------------

                if not product_matches_query(
                    name,
                    query
                ):
                    continue

                found_on_page = True

                print(
                    "[MEDIA] MATCH:",
                    name
                )

                # -------------------------------------
                # CENA
                # -------------------------------------

                price_el = product.select_one(
                    "div.main-price"
                )

                if not price_el:
                    continue

                price = parse_price(
                    price_el.get(
                        "aria-label"
                    )
                )

                if not price:
                    continue

                # -------------------------------------
                # LINK
                # -------------------------------------

                href = name_el.get(
                    "href",
                    ""
                )

                if href.startswith("/"):
                    href = (
                        "https://www.mediaexpert.pl"
                        + href
                    )

                offers.append(
                    {
                        "price": price,
                        "url": href,
                        "numeric": price_to_float(
                            price
                        )
                    }
                )

            if found_on_page:
                print(
                    "[MEDIA] Znaleziono pasujące "
                    "produkty na stronie",
                    page_number
                )

        await browser.close()

    # -----------------------------------------
    # BRAK OFERT
    # -----------------------------------------

    if not offers:

        print(
            "[MEDIA] Nie znaleziono pasującego produktu"
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
        "\n[MEDIA] BEST:",
        best
    )

    return {
        "price": best["price"],
        "url": best["url"]
    }
