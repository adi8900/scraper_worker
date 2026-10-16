import asyncio

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.services.query_parser import product_matches_query


def parse_price(value):
    return float(
        value
        .replace(",", ".")
        .replace(" ", "")
    )


async def search_morele_and_get_price(query):

    print("\n=== MORELE START ===")

    max_pages = 5
    offers = []

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        page = await browser.new_page()

        for page_number in range(1, max_pages + 1):

            url = (
                "https://www.morele.net/"
                "wyszukiwarka/,,,,,,,p,0,,,,/"
                f"{page_number}/"
                f"?q={query.replace(' ', '+')}"
            )

            print(
                f"\n[MORELE] STRONA {page_number}/{max_pages}"
            )

            print(
                "[MORELE] URL:",
                url
            )

            try:
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
            except Exception as e:
                print(
                    "[MORELE] Błąd page.goto():",
                    e
                )
                continue

            # Czekamy na produkty
            try:
                await page.wait_for_selector(
                    "div.cat-product",
                    timeout=15000,
                )
            except Exception:
                print(
                    "[MORELE] Brak cat-product "
                    "na stronie",
                    page_number
                )
                continue

            # Dajemy stronie chwilę na dociągnięcie danych
            await asyncio.sleep(2)

            html = await page.content()

            soup = BeautifulSoup(
                html,
                "html.parser",
            )

            products = soup.select(
                "div.cat-product"
            )

            print(
                "[MORELE] Produktów na stronie:",
                len(products)
            )

            # Jeżeli strona jest pusta, nie ma sensu
            # iść dalej
            if not products:
                print(
                    "[MORELE] Brak produktów - koniec."
                )
                break

            found_on_page = False

            for product in products:

                name = product.get(
                    "data-product-name",
                    "",
                )

                price = product.get(
                    "data-product-price",
                )

                if not name or not price:
                    continue

                print(
                    "[MORELE]",
                    name
                )

                # -----------------------------
                # FILTR PRODUKTU
                # -----------------------------

                if not product_matches_query(
                    name,
                    query,
                ):
                    continue

                found_on_page = True

                print(
                    "[MORELE] MATCH:",
                    name
                )

                # -----------------------------
                # LINK
                # -----------------------------

                link = product.select_one(
                    "a"
                )

                href = ""

                if link:
                    href = link.get(
                        "href",
                        "",
                    )

                if href.startswith("/"):
                    href = (
                        "https://www.morele.net"
                        + href
                    )

                # -----------------------------
                # CENA
                # -----------------------------

                try:
                    numeric = parse_price(
                        price
                    )
                except (
                    ValueError,
                    AttributeError,
                ):
                    print(
                        "[MORELE] Nieprawidłowa cena:",
                        price
                    )
                    continue

                offers.append(
                    {
                        "price": (
                            price.replace(
                                ".",
                                ",",
                            )
                            + " zł"
                        ),
                        "url": href,
                        "numeric": numeric,
                    }
                )

            # ---------------------------------
            # JEŻELI ZNALEŹLIŚMY PRODUKT
            # ---------------------------------

            if found_on_page:

                print(
                    "[MORELE] Znaleziono pasujący "
                    "produkt na stronie",
                    page_number
                )

                # Nie musimy koniecznie kończyć,
                # bo na następnych stronach może być
                # tańsza oferta.
                #
                # Ale możemy ograniczyć wyszukiwanie
                # do pierwszej strony zawierającej
                # właściwy produkt, jeśli sortowanie
                # jest po cenie.
                break

        await browser.close()

    # -----------------------------------------
    # BRAK OFERT
    # -----------------------------------------

    if not offers:

        print(
            "[MORELE] Nie znaleziono pasującego produktu"
        )

        return None

    # -----------------------------------------
    # NAJTAŃSZA OFERTA
    # -----------------------------------------

    best = min(
        offers,
        key=lambda x: x["numeric"],
    )

    print(
        "\n[MORELE] BEST:",
        best
    )

    return {
        "price": best["price"],
        "url": best["url"],
    }
