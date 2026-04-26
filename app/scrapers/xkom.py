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
            f"https://www.x-kom.pl/szukaj?q="
            f"{query.replace(' ','+')}"
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

    prices = soup.select(
        'span[aria-label*="Cena"]'
    )

    model = extract_model(
        query
    )


    for p in prices[:15]:

        text = p.get(
            "aria-label"
        )

        if not text:
            continue

        parent = p.find_parent()

        title = (
            parent.find_previous("h3")
            if parent else None
        )

        if not title:
            continue

        name = title.get_text(
            strip=True
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


        a = title.find("a")

        href = ""

        if a:
            href = a.get(
                "href",
                ""
            )

            if href.startswith("/"):
                href = (
                  "https://www.x-kom.pl"
                  + href
                )


        return {
            "price":
                text.replace(
                    "Cena:",
                    ""
                ).strip(),

            "url":
                href
        }

    return None
