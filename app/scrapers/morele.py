from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import asyncio

from app.services.query_parser import (
    extract_model,
    match_model,
    is_valid_name
)



async def search_morele_and_get_price(query):

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
            "https://www.morele.net/wyszukiwarka/"
            f"?q={query.replace(' ','+')}"
            "&d=0"
            "&sort=price_asc"
        )

        print(
            "URL:",
            url
        )

        await page.goto(
            url,
            wait_until="domcontentloaded"
        )

        await asyncio.sleep(
            2
        )

        html = await page.content()

        await browser.close()



    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    products = soup.select(
        "div.cat-product"
    )[:10]


    model = extract_model(
        query
    )


    for product in products:

        name = product.get(
            "data-product-name",
            ""
        )

        price = product.get(
            "data-product-price"
        )


        print(
            "[MORELE]",
            name
        )


        if not name or not price:
            continue


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


        return (
            f"{price.replace('.',',')} zł"
        )


    return None
