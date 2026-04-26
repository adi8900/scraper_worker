import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.services.query_parser import (
    extract_model,
    match_model,
    is_valid_name
)


def parse_price(v):
    return float(
      v.replace(",",".")
    )


async def search_morele_and_get_price(
 query
):

    print(
      "\n=== MORELE START ==="
    )

    async with async_playwright() as p:

        browser=await p.chromium.launch(
          headless=True,
          args=[
           "--no-sandbox",
           "--disable-dev-shm-usage"
          ]
        )

        page=await browser.new_page()

        url=(
        "https://www.morele.net/"
        "wyszukiwarka/,,,,,,,p,0,,,,/1/"
        f"?q={query.replace(' ','+')}"
        )

        print(
         "URL:",
         url
        )

        await page.goto(url)

        await page.wait_for_load_state(
         "domcontentloaded"
        )

        await asyncio.sleep(2)

        html=await page.content()

        await browser.close()


    soup=BeautifulSoup(
      html,
      "html.parser"
    )

    products=soup.select(
      "div.cat-product"
    )[:15]


    model=extract_model(
      query
    )


    best=None
    best_price=None


    for p in products:

        name=p.get(
          "data-product-name",
          ""
        )

        price=p.get(
          "data-product-price"
        )

        if not name or not price:
            continue

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


        link=p.select_one("a")
        href=""

        if link:
           href=link.get(
             "href",
             ""
           )

        if href.startswith("/"):
           href=(
            "https://www.morele.net"
            +href
           )


        numeric=parse_price(
          price
        )


        if (
         best_price is None
         or numeric<best_price
        ):

          best_price=numeric

          best={
           "price":
             f"{price.replace('.',',')} zł",

           "url":
             href
          }


    return best
