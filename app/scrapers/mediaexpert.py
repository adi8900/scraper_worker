import random
import asyncio

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.services.query_parser import (
    extract_model,
    detect_category,
    match_model,
    is_valid_name,
    parse_price
)



USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
]



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
            ),
            viewport={
                "width":1366,
                "height":768
            },
            locale="pl-PL"
        )

        page = await context.new_page()


        url = (
            "https://www.mediaexpert.pl/search"
            f"?query[querystring]={query.replace(' ','+')}"
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


        for _ in range(3):

            await page.mouse.wheel(
                0,
                2500
            )

            await asyncio.sleep(
                1
            )


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

        return parse_price(
            price_el.get(
                "aria-label"
            )
        )


    products = soup.select(
        "div.offer-box"
    )


    category = detect_category(
        query
    )

    model = extract_model(
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

        name_lower = name.lower()


        print(
            "[MEDIA]",
            name
        )


        if not is_valid_name(
            name,
            query
        ):
            continue


        if category == "gpu":
            if not any(
                x in name_lower
                for x in [
                    "rtx",
                    "radeon",
                    "geforce"
                ]
            ):
                continue


        if category == "ram":
            if not any(
                x in name_lower
                for x in [
                    "ram",
                    "ddr"
                ]
            ):
                continue


        if category == "ssd":
            if not any(
                x in name_lower
                for x in [
                    "ssd",
                    "nvme",
                    "m.2"
                ]
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

        if price:
            return price



    for product in products:

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

        if price:
            return price


    return None
