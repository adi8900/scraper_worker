import re
import random


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
]


BLACKLIST = [
    "laptop",
    "komputer",
    "zestaw",
    "g4m3r"
]


BAD_WORDS = [
    "kabel",
    "adapter",
    "przewód",
    "uchwyt",
    "etui",
    "wentylator",
    "pasta",
    "obudowa",
    "cooler",
    "chłodzenie"
]



def extract_model(query):

    match = re.search(
        r"\b\d{3,5}[a-zA-Z]*\b",
        query.lower()
    )

    return (
        match.group(0)
        if match
        else None
    )



def detect_category(query):

    q=query.lower()

    if (
      "rtx" in q
      or "radeon" in q
      or "arc" in q
      or "gpu" in q
      or "karta" in q
    ):
        return "gpu"


    if (
      "ram" in q
      or "ddr" in q
    ):
        return "ram"


    if (
      "ssd" in q
      or "nvme" in q
      or "m.2" in q
    ):
        return "ssd"


    if (
      "ryzen" in q
      or "intel" in q
      or "procesor" in q
    ):
        return "cpu"


    return "other"



def match_model(
    name,
    model
):

    if not model:
        return True

    return model in name.lower()



def category_match(
   name,
   category
):

    name=name.lower()


    if category=="gpu":
        return any(
          x in name
          for x in [
             "rtx",
             "geforce",
             "radeon",
             "arc"
          ]
        )


    if category=="ram":
        return any(
          x in name
          for x in [
             "ram",
             "ddr4",
             "ddr5"
          ]
        )


    if category=="ssd":
        return any(
          x in name
          for x in [
             "ssd",
             "nvme",
             "m.2"
          ]
        )


    if category=="cpu":
        return any(
          x in name
          for x in [
             "ryzen",
             "intel",
             "core"
          ]
        )


    return True



def is_garbage(name):

    name=name.lower()

    return any(
      x in name
      for x in BAD_WORDS
    )



def is_valid_name(
   name,
   query=None
):

    name=name.lower()

    if any(
      x in name
      for x in BLACKLIST
    ):
        return False


    if is_garbage(
       name
    ):
        return False


    return True



def parse_price(aria):

    if not aria:
        return None


    match=re.search(
      r"([\d\s]+)\s*złotych\s*i\s*(\d+)\s*groszy",
      aria
    )

    if match:

        whole=match.group(
          1
        ).replace(
          " ",
          ""
        )

        cents=match.group(
          2
        ).zfill(
          2
        )

        return f"{whole},{cents} zł"


    match=re.search(
      r"([\d\s]+)\s*złotych",
      aria
    )

    if match:

        whole=match.group(
          1
        ).replace(
          " ",
          ""
        )

        return f"{whole},00 zł"


    return None
