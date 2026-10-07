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

from app.services.product_matcher import (
    match_products
)


def price_to_float(v):

    return float(
        v.replace("zł", "")
         .replace(",", ".")
         .replace(" ", "")
         .replace("\u202f", "")
    )


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

        url = (
            "https://www.mediaexpert.pl/search?"
            f"query[querystring]={query.replace(' ', '+')}"
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

    # ---------------------------------------------------------
    # POJEDYNCZY PRODUKT
    # ---------------------------------------------------------

    if "/search?" not in final_url:

        price_el = soup.select_one(
            "div.main-price"
        )

        if not price_el:
            return None

        price = parse_price(
            price_el.get(
                "aria-label"
            )
        )

        if not price:
            return None

        return {
            "price": price,
            "url": final_url
        }

    # ---------------------------------------------------------
    # WYNIKI WYSZUKIWANIA
    # ---------------------------------------------------------

    products = soup.select(
        "div.offer-box"
    )

    model = extract_model(
        query
    )

    category = detect_category(
        query
    )

    candidates = []

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

        # -----------------------------
        # FILTR PARSERA
        # -----------------------------

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

        if not category_match(
            name,
            category
        ):
            continue

        # -----------------------------
        # CENA
        # -----------------------------

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

        # -----------------------------
        # URL
        # -----------------------------

        href = name_el.get(
            "href",
            ""
        )

        if href.startswith("/"):
            href = (
                "https://www.mediaexpert.pl"
                + href
            )

        candidates.append({
            "name": name,
            "price": price,
            "url": href
        })

    if not candidates:
        return None

    # Nie wysyłamy ogromnej listy do LLM.
    candidates = candidates[:20]

    print(
        "[MEDIA] Candidates:",
        len(candidates)
    )

    # ---------------------------------------------------------
    # OLLAMA
    # ---------------------------------------------------------

    matches = match_products(
        query,
        candidates
    )

    # ---------------------------------------------------------
    # FALLBACK
    # ---------------------------------------------------------

    if matches is None:

        print(
            "[MEDIA] Ollama unavailable - fallback"
        )

        valid_products = candidates

    else:

        valid_products = [
            candidates[i]
            for i in matches
        ]

    if not valid_products:
        return None

    # ---------------------------------------------------------
    # NAJTAŃSZY
    # ---------------------------------------------------------

    best = min(
        valid_products,
        key=lambda x:
            price_to_float(
                x["price"]
            )
    )

    print(
        "[MEDIA] BEST:",
        best
    )

    return {
        "price": best["price"],
        "url": best["url"]
    }
