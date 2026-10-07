import asyncio

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
        v.replace(",", ".")
    )


async def search_morele_and_get_price(
    query
):

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
            "wyszukiwarka/,,,,,,,p,0,,,,/1/"
            f"?q={query.replace(' ', '+')}"
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

        html = await page.content()

        await browser.close()

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    products = soup.select(
        "div.cat-product"
    )

    model = extract_model(
        query
    )

    category = detect_category(
        query
    )

    candidates = []

    for product in products:

        name = product.get(
            "data-product-name",
            ""
        )

        price = product.get(
            "data-product-price"
        )

        if not name or not price:
            continue

        print(
            "[MORELE]",
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
        # DODATKOWA OCHRONA GPU
        # -----------------------------

        if (
            category == "gpu"
            and not any(
                x in name.lower()
                for x in [
                    "rtx",
                    "geforce",
                    "radeon",
                    "arc"
                ]
            )
        ):
            continue

        # -----------------------------
        # LINK
        # -----------------------------

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

        # -----------------------------
        # CENA
        # -----------------------------

        numeric = parse_price(
            price
        )

        candidates.append({
            "name": name,
            "price": f"{price.replace('.', ',')} zł",
            "url": href,
            "numeric": numeric
        })

    if not candidates:
        return None

    # Maksymalnie 20 produktów do LLM.
    candidates = candidates[:20]

    print(
        "[MORELE] Candidates:",
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
            "[MORELE] Ollama unavailable - fallback"
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
        "[MORELE] BEST:",
        best
    )

    return {
        "price": best["price"],
        "url": best["url"]
    }
