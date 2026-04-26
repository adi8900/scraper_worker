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
          "https://www.morele.net/"
          f"wyszukiwarka/?q="
          f"{query.replace(' ','+')}&d=0"
        )

        print("URL:",url)

        await page.goto(url)

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
    )[:15]

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


        link = product.select_one(
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


        return {
            "price":
                f"{price.replace('.',',')} zł",

            "url":
                href
        }

    return None
