from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.services.query_parser import (
    extract_model,
    detect_category,
    category_match,
    match_model,
    is_valid_name
)

from app.services.product_matcher import (
    match_products
)


def parse_price(v):

    return float(
        v.replace("zł", "")
         .replace(",", ".")
         .replace(" ", "")
         .replace("\u202f", "")
    )


async def search_xkom_and_get_price(
    query
):

    print(
        "\n=== XKOM START ==="
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
            "https://www.x-kom.pl/szukaj?"
            f"q={query.replace(' ', '+')}"
            "&sort_by=price_asc"
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

        html = await page.content()

        await browser.close()

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    cards = soup.select(
        'div[class*="sc-"]'
    )

    model = extract_model(
        query
    )

    category = detect_category(
        query
    )

    candidates = []

    for card in cards:

        link = card.select_one(
            'a[href*="/p/"]'
        )

        price_el = card.select_one(
            'span[aria-label*="Cena"]'
        )

        if not link or not price_el:
            continue

        name = link.get_text(
            strip=True
        )

        if not name:
            continue

        print(
            "[XKOM]",
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
        # LINK
        # -----------------------------

        href = link.get(
            "href",
            ""
        )

        if href.startswith("/"):
            href = (
                "https://www.x-kom.pl"
                + href
            )

        # -----------------------------
        # CENA
        # -----------------------------

        price = (
            price_el
            .get("aria-label")
            .replace(
                "Cena:",
                ""
            )
            .strip()
        )

        numeric = parse_price(
            price
        )

        candidates.append({
            "name": name,
            "price": price,
            "url": href,
            "numeric": numeric
        })

    if not candidates:
        return None

    # Maksymalnie 20 produktów do LLM.
    candidates = candidates[:20]

    print(
        "[XKOM] Candidates:",
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
            "[XKOM] Ollama unavailable - fallback"
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
            x["numeric"]
    )

    print(
        "BEST:",
        best
    )

    return {
        "price": best["price"],
        "url": best["url"]
    }
