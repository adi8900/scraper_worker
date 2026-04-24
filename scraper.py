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

        url = f"https://www.x-kom.pl/szukaj?sort_by=price_asc&q={query.replace(' ', '+')}"
        print("URL:", url)

        await page.goto(url, timeout=30000)
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")

    prices_html = soup.select("span[aria-label*='Cena']")

    print("CENY:", len(prices_html))

    model = extract_model(query)
    prices = []

    for price_el in prices_html[:15]:
        price_text = price_el.get("aria-label", "")

        if "zł" not in price_text:
            continue

        # 🔥 idziemy do produktu
        container = price_el.find_parent("div")

        if not container:
            continue

        name_el = container.find_previous("h3")

        if not name_el:
            continue

        name = name_el.get_text(strip=True)

        print("NAME:", name)

        # 🔥 filtry
        if not is_valid_name(name, query):
            continue

        if model and model.lower() not in name.lower():
            continue

        try:
            price = parse_price_to_float(price_text.replace("Cena:", "").strip())
            prices.append(price)
        except:
            continue

    if not prices:
        print("⚠️ XKOM fallback")
        return None

    best = min(prices)

    print("🏆 BEST PRICE:", best)

    return f"{best:.2f}".replace(".", ",") + " zł"

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

async def search_mediaexpert_and_get_price(query):
    print("\n=== MEDIA START ===")

    import re

    def parse_price_smart(text):
        if not text:
            return None

        text = text.replace("\u202f", " ").replace("zł", "").strip()
        numbers = re.findall(r"\d+", text)

        if not numbers:
            return None

        if len(numbers) == 1:
            return float(numbers[0])

        zl = "".join(numbers[:-1])
        gr = numbers[-1]

        return float(f"{zl}.{gr}")

    async with async_playwright() as p:
        browser = await launch_browser(p)

        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1366, "height": 768},
            locale="pl-PL"
        )

        page = await context.new_page()

        # 🔥 NAJPIERW SORT
        url = f"https://www.mediaexpert.pl/search?query[querystring]={query.replace(' ', '+')}&sort=price_asc"
        print("URL:", url)

        await page.goto(url, timeout=30000)
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        products = soup.select("div.offer-box")

        # =========================
        # 🔥 FALLBACK → bez sortowania (CPU redirect)
        # =========================
        if len(products) == 0:
            print("⚠️ fallback → no sort")

            url = f"https://www.mediaexpert.pl/search?query[querystring]={query.replace(' ', '+')}"
            print("URL2:", url)

            await page.goto(url, timeout=30000)
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)

            final_url = page.url

            # 🔥 PRODUCT PAGE
            if "/search?" not in final_url:
                print("➡️ PRODUCT PAGE")

                html = await page.content()
                await browser.close()

                soup = BeautifulSoup(html, "html.parser")

                price_el = soup.select_one("div.main-price")
                if not price_el:
                    return None

                text = price_el.get_text(" ", strip=True)
                price_float = parse_price_smart(text)

                if price_float:
                    return f"{price_float:.2f}".replace(".", ",") + " zł"

                return None

            # jeśli nadal lista → lecimy dalej
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            products = soup.select("div.offer-box")

        await browser.close()

        print("ZNALEZIONE:", len(products))

        model = extract_model(query)
        prices = []

        for product in products[:8]:  # 🔥 tylko TOP 8
            name_el = product.select_one("h3.name a")
            if not name_el:
                continue

            name = name_el.get_text(strip=True)
            name_l = name.lower()

            print("MEDIA NAME:", name)

            q = query.lower()

            # ===== RAM =====
            if "ddr5" in q:
                if "32gb" not in name_l:
                    continue
                if "6000" not in name_l:
                    continue

            # ===== GPU =====
            elif "rtx" in q:
                if "laptop" in name_l or "komputer" in name_l:
                    continue

            # ===== CPU =====
            else:
                if not is_valid_name(name, query):
                    continue
                if not match_model(name, model):
                    continue

            price_el = product.select_one("div.main-price")
            if not price_el:
                continue

            raw_price = price_el.get_text(" ", strip=True)
            price_float = parse_price_smart(raw_price)

            if price_float:
                prices.append(price_float)

        if not prices:
            print("⚠️ MEDIA fallback final")
            return None

        best = min(prices)

        print("🏆 BEST PRICE:", best)

        return f"{best:.2f}".replace(".", ",") + " zł"

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
