from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.services.query_parser import (
    extract_model,
    match_model,
    is_valid_name
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

        # sort po cenie rosnąco
        url = (
            "https://www.x-kom.pl/szukaj?"
            f"q={query.replace(' ','+')}"
            "&sort_by=price_asc"
        )

        print("URL:", url)

        await page.goto(url)

        await page.wait_for_load_state(
            "domcontentloaded"
        )

        html = await page.content()

        await browser.close()


    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    products = soup.select(
        'a[href*="/p/"]'
    )

    model = extract_model(
        query
    )


    for product in products[:20]:

        name = product.get_text(
            strip=True
        )

        if not name:
            continue


        print(
            "[XKOM]",
            name
        )


        if not is_valid_name(
            name,
            query
        ):
            continue


        if model and not match_model(
            name,
            model
        ):
            continue


        href = product.get(
            "href",
            ""
        )


        if href.startswith("/"):
            href = (
                "https://www.x-kom.pl"
                + href
            )


        card = product
        price = None


        for _ in range(6):

            if not card:
                break

            price_el = card.select_one(
                'span[aria-label*="Cena"]'
            )

            if price_el:

                price = (
                    price_el
                    .get(
                        "aria-label"
                    )
                    .replace(
                        "Cena:",
                        ""
                    )
                    .strip()
                )

                break


            card = card.parent


        if not price:
            continue


        print(
            "LINK:",
            href
        )


        return {
            "price": price,
            "url": href
        }


    return None
