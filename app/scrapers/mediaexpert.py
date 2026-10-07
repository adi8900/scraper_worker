import asyncio
import random

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.services.query_parser import (
    USER_AGENTS,
    extract_model,
    detect_category,
    category_match,
    match_model,
    is_valid_name,
    parse_price
)


def price_to_float(v):
    return float(
        v.replace("zł", "")
         .replace(",", ".")
         .replace(" ", "")
         .replace("\u202f", "")
         .replace("\xa0", "")
    )


async def search_mediaexpert_and_get_price(query):

    print("\n=== MEDIA START ===")

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS)
        )

        page = await context.new_page()

        url = (
            "https://www.mediaexpert.pl/search?"
            f"query[querystring]={query.replace(' ', '+')}"
            "&sort=price_asc"
        )

        print("URL:", url)

        await page.goto(url)

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

        print("FINAL URL:", final_url)

        html = await page.content()

        await browser.close()

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # --------------------------------------------------
    # SINGLE PRODUCT PAGE
    # --------------------------------------------------

    if "/search?" not in final_url:

        price_el = soup.select_one(
            "div.main-price"
        )

        if not price_el:
            return None

        aria = price_el.get(
            "aria-label"
        )

        print(
            "[MEDIA] SINGLE PRICE ARIA:",
            repr(aria)
        )

        price = parse_price(
            aria
        )

        if not price:
            return None

        return {
            "price": price,
            "url": final_url
        }

    # --------------------------------------------------
    # SEARCH RESULTS
    # --------------------------------------------------

    # NIE ograniczamy tutaj do pierwszych 15.
    # Najpierw filtrujemy, potem wybieramy najtańsze.
    products = soup.select(
        "div.offer-box"
    )

    print(
        "[MEDIA] FOUND PRODUCTS:",
        len(products)
    )

    model = extract_model(
        query
    )

    category = detect_category(
        query
    )

    print(
        "[MEDIA] MODEL:",
        model
    )

    print(
        "[MEDIA] CATEGORY:",
        category
    )

    offers = []

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
            "[MEDIA] CHECK:",
            name
        )

        # ----------------------------------------------
        # NAME FILTER
        # ----------------------------------------------

        if not is_valid_name(
            name,
            query
        ):
            print(
                "[MEDIA] REJECT: invalid name"
            )
            continue

        # ----------------------------------------------
        # MODEL FILTER
        # ----------------------------------------------

        if model and not match_model(
            name,
            model
        ):
            print(
                "[MEDIA] REJECT: model"
            )
            continue

        # ----------------------------------------------
        # CATEGORY FILTER
        # ----------------------------------------------

        if not category_match(
            name,
            category
        ):
            print(
                "[MEDIA] REJECT: category"
            )
            continue

        # ----------------------------------------------
        # PRICE
        # ----------------------------------------------

        price_el = product.select_one(
            "div.main-price"
        )

        if not price_el:
            print(
                "[MEDIA] REJECT: no price element"
            )
            continue

        aria = price_el.get(
            "aria-label"
        )

        print(
            "[MEDIA] PRICE ARIA:",
            repr(aria)
        )

        price = parse_price(
            aria
        )

        print(
            "[MEDIA] PARSED PRICE:",
            repr(price)
        )

        if not price:
            print(
                "[MEDIA] REJECT: price parser"
            )
            continue

        # ----------------------------------------------
        # URL
        # ----------------------------------------------

        href = name_el.get(
            "href",
            ""
        )

        if href.startswith("/"):
            href = (
                "https://www.mediaexpert.pl"
                + href
            )

        offers.append({
            "price": price,
            "url": href,
            "name": name
        })

    # --------------------------------------------------
    # NO VALID OFFERS
    # --------------------------------------------------

    if not offers:

        print(
            "[MEDIA] NO VALID OFFERS"
        )

        return None

    # --------------------------------------------------
    # SORT BY PRICE
    # --------------------------------------------------

    offers.sort(
        key=lambda x: price_to_float(
            x["price"]
        )
    )

    print(
        "[MEDIA] VALID OFFERS:"
    )

    for offer in offers[:15]:

        print(
            "[MEDIA]",
            offer["price"],
            offer["name"]
        )

    # Najtańsza poprawna oferta
    return {
        "price": offers[0]["price"],
        "url": offers[0]["url"]
    }
