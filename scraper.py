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


def is_valid_name(name, query=None):
    name = normalize(name)

    if "/" in name:
        return False

    if re.search(r"\d+gb.*\d+tb", name):
        return False

    if re.search(r"(i\d-|ryzen\s\d)", name) and "rtx" in name:
        return False

    blacklist = ["komputer", "zestaw", "desktop", "g4m3r", "gaming pc", "laptop"]

    for b in blacklist:
        if b in name:
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

# ===== 🔥 QUERY PARSER =====

def parse_query(query):
    q = query.lower()

    data = {
        "type": None,
        "model": None,
        "ram_size": None,
        "ram_speed": None,
        "storage_size": None,
    }

    if "rtx" in q or "gtx" in q:
        data["type"] = "gpu"
    elif "ddr" in q:
        data["type"] = "ram"
    elif "nvme" in q or "ssd" in q or "hdd" in q:
        data["type"] = "ssd"
    elif "ryzen" in q or "intel" in q:
        data["type"] = "cpu"

    # model (np. 7500f / 5060)
    match = re.search(r"\b\d{3,5}[a-zA-Z]*\b", q)
    if match:
        data["model"] = match.group(0)

    # RAM
    size = re.search(r"(\d+)\s*gb", q)
    if size:
        data["ram_size"] = size.group(1)

    speed = re.search(r"\b(4\d{3}|5\d{3}|6\d{3})\b", q)
    if speed:
        data["ram_speed"] = speed.group(1)

    # STORAGE (uniwersalne)
    storage = re.search(r"(\d+)\s*(tb|gb)", q)
    if storage:
        data["storage_size"] = storage.group(1) + storage.group(2)

    return data

# ===== 🔥 MATCH ENGINE =====

def match_product(name, query_data, query):
    name_l = name.lower()

    if "outlet" in name_l:
        return False

    if not is_valid_name(name, query):
        return False

    t = query_data["type"]

    # ===== GPU =====
    if t == "gpu":
        if not any(x in name_l for x in ["rtx", "gtx"]):
            return False
        if "laptop" in name_l or "komputer" in name_l:
            return False
        if query_data["model"] and query_data["model"] not in name_l:
            return False

    # ===== RAM =====
    elif t == "ram":
        if "ddr" not in name_l:
            return False

        if query_data["ram_size"] and query_data["ram_size"] not in name_l:
            return False

        if query_data["ram_speed"] and query_data["ram_speed"] not in name_l:
            return False

    # ===== SSD / HDD =====
    elif t == "ssd":
        if not any(x in name_l for x in ["ssd", "nvme", "hdd"]):
            return False

        if any(x in name_l for x in ["kieszeń", "adapter", "obudowa", "case"]):
            return False

        if query_data["storage_size"]:
            size = query_data["storage_size"]

            if size.endswith("tb"):
                tb = int(size.replace("tb", ""))
                if size not in name_l and f"{tb*1000}gb" not in name_l:
                    return False

            elif size.endswith("gb"):
                if size not in name_l:
                    return False

    # ===== CPU =====
    elif t == "cpu":
        if query_data["model"] and query_data["model"] not in name_l:
            return False

    return True

# ===== XKOM =====

async def search_xkom_and_get_price(query):
    print("\n=== XKOM START ===")

    async with async_playwright() as p:
        browser = await launch_browser(p)
        page = await browser.new_page()

        url = f"https://www.x-kom.pl/szukaj?sort_by=price_asc&q={query.replace(' ', '+')}"
        print("URL:", url)

        await page.goto(url)
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    prices_html = soup.select("span[aria-label*='Cena']")

    query_data = parse_query(query)
    prices = []

    for price_el in prices_html[:20]:
        price_text = price_el.get("aria-label", "")

        container = price_el.find_parent("div")
        if not container:
            continue

        name_el = container.find_previous("h3")
        if not name_el:
            continue

        name = name_el.get_text(strip=True)
        print("NAME:", name)

        if not match_product(name, query_data, query):
            continue

        try:
            price = parse_price_to_float(price_text.replace("Cena:", "").strip())
            prices.append(price)
        except:
            continue

    if not prices:
        print("⚠️ XKOM fallback")
        return None

    return f"{min(prices):.2f}".replace(".", ",") + " zł"

# ===== MORELE =====

async def search_morele_and_get_price(query):
    print("\n=== MORELE START ===")

    async with async_playwright() as p:
        browser = await launch_browser(p)
        page = await browser.new_page()

        url = f"https://www.morele.net/wyszukiwarka/,,,,,,,p,0,,,,/1/?q={query.replace(' ', '%20')}"
        print("URL:", url)

        await page.goto(url)
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    products = soup.select("div.cat-product")[:40]

    query_data = parse_query(query)
    prices = []

    for p in products:
        name = p.get("data-product-name", "")
        price = p.get("data-product-price")

        print("NAME:", name)

        if not name or not price:
            continue

        if not match_product(name, query_data, query):
            continue

        try:
            prices.append(float(price))
        except:
            continue

    if not prices:
        print("⚠️ MORELE fallback")
        return None

    return f"{min(prices):.2f}".replace(".", ",") + " zł"

# ===== MEDIAEXPERT =====

async def search_mediaexpert_and_get_price(query):
    print("\n=== MEDIA START ===")

    def parse_price(text):
        text = text.replace("\u202f", " ").replace("zł", "")
        nums = re.findall(r"\d+", text)
        if not nums:
            return None
        return float("".join(nums[:-1]) + "." + nums[-1])

    async with async_playwright() as p:
        browser = await launch_browser(p)
        page = await browser.new_page()

        url = f"https://www.mediaexpert.pl/search?query[querystring]={query.replace(' ', '+')}&sort=price_asc"
        print("URL:", url)

        await page.goto(url)
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    products = soup.select("div.offer-box")[:10]

    query_data = parse_query(query)
    prices = []

    for p in products:
        name_el = p.select_one("h3.name a")
        price_el = p.select_one("div.main-price")

        if not name_el or not price_el:
            continue

        name = name_el.get_text(strip=True)
        print("MEDIA NAME:", name)

        if not match_product(name, query_data, query):
            continue

        price = parse_price(price_el.get_text(" ", strip=True))
        if price:
            prices.append(price)

    if not prices:
        print("⚠️ MEDIA fallback")
        return None

    return f"{min(prices):.2f}".replace(".", ",") + " zł"

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
