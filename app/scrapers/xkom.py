import re

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

        url = (
            "https://www.x-kom.pl/szukaj"
            f"?q={query.replace(' ','+')}"
            "&sort_by=price_asc"
        )

        print("URL:", url)

        await page.goto(
            url,
            wait_until="domcontentloaded"
        )

        html = await page.content()

        await browser.close()


    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    prices = soup.select(
        'span[aria-label*="Cena"]'
    )

    model = extract_model(
        query
    )


    for price_box in prices[:8]:

        text = price_box.get(
            "aria-label"
        )

        if not text:
            continue


        parent = price_box.find_parent()

        title = (
            parent.find_previous(
                "h3"
            )
            if parent
            else None
        )

        name = (
            title.get_text(
                strip=True
            )
            if title
            else ""
        )


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


        return (
            text
            .replace(
                "Cena:",
                ""
            )
            .strip()
        )


    return None
