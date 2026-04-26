import asyncio
import random
import re

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.services.query_parser import (
    detect_category,
    extract_model,
    match_model,
    is_valid_name
)


USER_AGENTS = [
"Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
"Mozilla/5.0 (X11; Linux x86_64)"
]


def parse_price(aria):

    if not aria:
        return None

    match = re.search(
      r"([\d\s]+)\s*złotych",
      aria
    )

    if not match:
        return None

    value = (
        match.group(1)
        .replace(" ","")
    )

    return f"{value},00 zł"



async def search_mediaexpert_and_get_price(
    query
):

    print(
      "\n=== MEDIA START ==="
    )

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

        url=(
        "https://www.mediaexpert.pl/search?"
        f"query[querystring]={query.replace(' ','+')}"
        "&sort=price_asc"
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

        await page.mouse.wheel(
            0,
            4000
        )

        await asyncio.sleep(1)

        final_url = page.url

        print(
          "FINAL URL:",
          final_url
        )

        html = await page.content()

        await browser.close()


    soup = BeautifulSoup(
      html,
      "html.parser"
    )


    if "/search?" not in final_url:

        price_el = soup.select_one(
           "div.main-price"
        )

        if not price_el:
            return None

        return {
            "price":
              parse_price(
                 price_el.get(
                   "aria-label"
                 )
              ),

            "url":
              final_url
        }


    products = soup.select(
      "div.offer-box"
    )

    model = extract_model(
        query
    )

    category = detect_category(
        query
    )


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

        href = name_el.get(
            "href",
            ""
        )

        if href.startswith("/"):
            href=(
             "https://www.mediaexpert.pl"
             + href
            )

        return {
            "price":
                price,

            "url":
                href
        }

    return None
