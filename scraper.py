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

def normalize(text: str):
    text = text.lower()
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_model(query):
    q = query.lower()

    # tylko CPU/GPU
    if any(x in q for x in ["ryzen", "intel", "rtx", "gtx"]):
        match = re.search(r"\b\d{3,5}[a-zA-Z]*\b", q)
        return match.group(0) if match else None

    return None


def match_model(name, model):
    if not model:
        return True
    return bool(re.search(rf"\b{model}\b", name, re.IGNORECASE))


def is_valid_name(name, query=None):
    name = normalize(name)

    # 🔥 HARD FILTRY NA GOTOWE PC
    if "/" in name:
        return False

    if re.search(r"\d+gb.*\d+tb", name):
        return False

    if re.search(r"(i\d-|ryzen\s\d)", name) and "rtx" in name:
        return False

    blacklist = [
        "komputer",
        "zestaw",
        "desktop",
        "g4m3r",
        "gaming pc",
        "laptop",
    ]

    for b in blacklist:
        if b in name:
            return False

    # GPU sanity
    if query and "rtx" in query.lower():
        if not re.search(r"rtx\s*\d{3,4}", name):
            return False

    return True


def is_reasonable(price_str):
    try:
        price = float(price_str.replace("zł", "").replace(",", ".").replace(" ", ""))
    except:
        return False

    return 100 < price < 20000


def parse_price_to_float(price_str):
    return float(price_str.replace("zł", "").replace(",", ".").replace(" ", ""))


async def launch_browser(p):
    return await p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )

# ===== XKOM =====

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
            await browser.close()
            return None

        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    prices = soup.select('span[aria-label*="Cena"]')

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

        if not is_valid_name(name, query):
            continue

        if not match_model(name, model):
            continue

        return text.replace("Cena:", "").strip()

    return None


# ===== MORELE =====

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
    products = soup.select("div.cat-product")[:10]

    model = extract_model(query)

    for p in products:
        name = p.get("data-product-name", "")
        price = p.get("data-product-price")

        print("NAME:", name)

        if not name or not price:
            continue

        if not is_valid_name(name, query):
            continue

        if not match_model(name, model):
            continue

        return f"{price.replace('.', ',')} zł"

    return None

# ===== MEDIA EXPERT =====
async def search_mediaexpert_and_get_price(query):
    print("\n=== MEDIA START ===")

    async with async_playwright() as p:
        browser = await launch_browser(p)

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

        # 🔥 SCROLL żeby załadować więcej produktów
        for _ in range(5):
            await page.mouse.wheel(0, 2000)
            await asyncio.sleep(1)

        final_url = page.url

        # =========================
        # 🔥 PRODUCT PAGE
        # =========================
        if "/search?" not in final_url:
            html = await page.content()
            await browser.close()

            soup = BeautifulSoup(html, "html.parser")

            price_el = soup.select_one("div.main-price")
            if not price_el:
                return None

            # 🔥 wyciągamy BEZPOŚREDNIO liczby (lepsze niż aria)
            whole = price_el.select_one(".whole")
            cents = price_el.select_one(".cents")

            if not whole:
                return None

            price = whole.get_text(strip=True).replace("\u202f", "")

            if cents:
                price += "," + cents.get_text(strip=True)
            else:
                price += ",00"

            return f"{price} zł"

        # =========================
        # 🔥 LISTA PRODUKTÓW
        # =========================
        html = await page.content()
        await browser.close()

        soup = BeautifulSoup(html, "html.parser")
        products = soup.select("div.offer-box")

        print("ZNALEZIONE:", len(products))

        model = extract_model(query)

        for product in products:
            name_el = product.select_one("h3.name a")
            if not name_el:
                continue

            name = name_el.get_text(strip=True)
            print("MEDIA NAME:", name)

            if not is_valid_name(name, query):
                continue

            if not match_model(name, model):
                continue

            # 🔥 FILTR GPU (żeby nie brało laptopów)
            if "rtx" in query.lower():
                if not any(x in name.lower() for x in ["karta", "geforce", "rtx"]):
                    continue

            price_el = product.select_one("div.main-price")
            if not price_el:
                continue

            whole = price_el.select_one(".whole")
            cents = price_el.select_one(".cents")

            if not whole:
                continue

            price = whole.get_text(strip=True).replace("\u202f", "")

            if cents:
                price += "," + cents.get_text(strip=True)
            else:
                price += ",00"

            print("✅ MEDIA:", name)

            return f"{price} zł"

        print("⚠️ MEDIA fallback")
        return None

# ===== MAIN =====

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

    if not results:
        return None

    numeric = {k: parse_price_to_float(v) for k, v in results.items()}

    return {
        "results": results,
        "cheapest": min(numeric, key=numeric.get),
        "most_expensive": max(numeric, key=numeric.get)
    }
