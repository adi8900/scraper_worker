import json
import re
import random
import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
]

# ===== HELPERY =====

def extract_model(query):
    match = re.search(r"\b\d{3,5}[a-zA-Z]*\b", query.lower())
    return match.group(0) if match else None


def is_reasonable(price_str):
    try:
        price = float(
            price_str.replace("zł", "").replace(",", ".").replace(" ", "").strip()
        )
    except:
        return False

    return 100 < price < 20000


def is_valid_name(name):
    name = name.lower()
    blacklist = ["laptop", "komputer", "zestaw", "smx"]
    return not any(x in name for x in blacklist)


# ===== PARSERY =====

def parse_mediaexpert_price(text):
    match = re.search(r"(\d+)[,.](\d+)\s*zł", text)
    if match:
        return f"{match.group(1)},{match.group(2).zfill(2)} zł"
    return None


# ===== SEARCH =====

async def launch_browser(p):
    return await p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-setuid-sandbox",
        ]
    )


async def search_xkom_and_get_price(query):
    print("\n=== XKOM START ===")

    async with async_playwright() as p:
        browser = await launch_browser(p)
        page = await browser.new_page()

        url = f"https://www.x-kom.pl/szukaj?q={query.replace(' ', '+')}"
        print("URL:", url)

        await page.goto(url, timeout=30000)
        await page.wait_for_load_state("domcontentloaded")

        try:
            await page.wait_for_selector('span[aria-label*="Cena"]', timeout=8000)
        except:
            print("❌ XKOM brak selektora")
            await browser.close()
            return None

        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    prices = soup.select('span[aria-label*="Cena"]')

    print("ZNALEZIONE CENY:", len(prices))

    model = extract_model(query)

    for p in prices[:10]:
        text = p.get("aria-label")

        if not text or "zł" not in text:
            continue

        parent = p.find_parent()
        title = parent.find_previous("h3") if parent else None
        name = title.get_text(strip=True) if title else ""

        print("NAME:", name)

        if not name:
            continue

        if not is_valid_name(name):
            print("❌ blacklist")
            continue

        if model and model not in name.lower():
            print("❌ model mismatch")
            continue

        print("✅ XKOM:", name)
        return text.replace("Cena:", "").strip()

    print("⚠️ XKOM fallback")
    return None


async def search_morele_and_get_price(query):
    print("\n=== MORELE START ===")

    async with async_playwright() as p:
        browser = await launch_browser(p)
        page = await browser.new_page()

        url = f"https://www.morele.net/wyszukiwarka/?q={query.replace(' ', '+')}&d=0"
        print("URL:", url)

        await page.goto(url, timeout=30000)
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    products = soup.select('div.cat-product')[:10]

    print("ZNALEZIONE:", len(products))

    model = extract_model(query)

    for p in products:
        name = p.get("data-product-name", "")
        price = p.get("data-product-price")

        print("NAME:", name)

        if not name or not price:
            continue

        if not is_valid_name(name):
            print("❌ blacklist")
            continue

        if model and model not in name.lower():
            print("❌ model mismatch")
            continue

        print("✅ MORELE:", name)
        return f"{price.replace('.', ',')} zł"

    print("⚠️ MORELE fallback")
    return None

async def search_mediaexpert_and_get_price(query):
    print("\n=== MEDIA START ===")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1366, "height": 768},
            locale="pl-PL"
        )

        page = await context.new_page()

        url = f"https://www.mediaexpert.pl/search?query[querystring]={query.replace(' ', '+')}"
        print("URL:", url)

        await page.goto(url, timeout=30000)
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        final_url = page.url
        print("FINAL URL:", final_url)

        # =========================
        # 🔥 CASE 1: STRONA PRODUKTU
        # =========================
        if "/search?" not in final_url:
            print("➡️ PRODUCT PAGE")

            try:
                await page.wait_for_selector("div.main-price", timeout=8000)
            except:
                print("❌ brak ceny na stronie produktu")

            html = await page.content()
            await browser.close()

            soup = BeautifulSoup(html, "html.parser")

            price_el = soup.select_one("div.main-price")
            if not price_el:
                return None

            aria = price_el.get("aria-label")
            print("ARIA:", aria)

            if not aria:
                return None

            match = re.search(r"(\d+)\s*złotych\s*i\s*(\d+)\s*groszy", aria)
            if match:
                return f"{match.group(1)},{match.group(2).zfill(2)} zł"

            match = re.search(r"(\d+)\s*złotych", aria)
            if match:
                return f"{match.group(1)},00 zł"

            return None

        # =========================
        # 🔥 CASE 2: LISTA PRODUKTÓW
        # =========================
        try:
            await page.wait_for_selector("div.offer-box", timeout=10000)
        except:
            print("❌ nie załadowało offer-box")

        await asyncio.sleep(2)

        html = await page.content()
        await browser.close()

        soup = BeautifulSoup(html, "html.parser")

        products = soup.select("div.offer-box")
        print("ZNALEZIONE PRODUKTY:", len(products))

        model = extract_model(query)

        for product in products:
            name_el = product.select_one("h3.name a")
            if not name_el:
                continue

            name = name_el.get_text(strip=True)
            print("NAME:", name)

            name_lower = name.lower()

            if any(x in name_lower for x in ["laptop", "komputer", "zestaw", "smx"]):
                print("❌ blacklist")
                continue

            if model and model not in name_lower:
                print("❌ model mismatch")
                continue

            price_el = product.select_one("div.main-price")
            if not price_el:
                continue

            aria = price_el.get("aria-label")
            print("ARIA:", aria)

            if not aria:
                continue

            match = re.search(r"(\d+)\s*złotych\s*i\s*(\d+)\s*groszy", aria)
            if match:
                return f"{match.group(1)},{match.group(2).zfill(2)} zł"

            match = re.search(r"(\d+)\s*złotych", aria)
            if match:
                return f"{match.group(1)},00 zł"

        print("⚠️ MEDIA brak dopasowania")
        return None

# ===== MAIN =====

def parse_price_to_float(price_str):
    return float(price_str.replace("zł", "").replace(",", ".").replace(" ", "").strip())


async def compare_prices(query):
    results = {}

    try:
        x = await search_xkom_and_get_price(query)
        if x and is_reasonable(x):
            results["x-kom"] = x
    except Exception as e:
        print("XKOM ERROR:", e)

    try:
        m = await search_morele_and_get_price(query)
        if m and is_reasonable(m):
            results["morele"] = m
    except Exception as e:
        print("MORELE ERROR:", e)

    try:
        me = await search_mediaexpert_and_get_price(query)
        if me and is_reasonable(me):
            results["mediaexpert"] = me
    except Exception as e:
        print("MEDIA ERROR:", e)

    print("\n=== FINAL ===")
    print(results)

    if not results:
        return None

    numeric = {k: parse_price_to_float(v) for k, v in results.items()}

    return {
        "results": results,
        "cheapest": min(numeric, key=numeric.get),
        "most_expensive": max(numeric, key=numeric.get)
    }

async def compare_prices_stream(query):
    results = {}

    # START
    yield {"type": "status", "value": "start"}

    # XKOM
    yield {"type": "status", "value": "xkom"}
    try:
        x = await search_xkom_and_get_price(query)
        if x and is_reasonable(x):
            results["x-kom"] = x
            yield {"type": "result", "shop": "x-kom", "price": x}
    except Exception as e:
        print("XKOM ERROR:", e)

    # MORELE
    yield {"type": "status", "value": "morele"}
    try:
        m = await search_morele_and_get_price(query)
        if m and is_reasonable(m):
            results["morele"] = m
            yield {"type": "result", "shop": "morele", "price": m}
    except Exception as e:
        print("MORELE ERROR:", e)

    # MEDIA
    yield {"type": "status", "value": "mediaexpert"}
    try:
        me = await search_mediaexpert_and_get_price(query)
        if me and is_reasonable(me):
            results["mediaexpert"] = me
            yield {"type": "result", "shop": "mediaexpert", "price": me}
    except Exception as e:
        print("MEDIA ERROR:", e)

    yield {"type": "done", "results": results}
