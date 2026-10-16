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
    "g4m3r",
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
    "chłodzenie",
    "outlet",
    "refabrykowany",
    "refurbished",
]


# ---------------------------------------------------------
# NORMALIZACJA
# ---------------------------------------------------------

def normalize(text):
    """
    Normalizuje nazwę produktu / zapytanie.
    """
    text = text.lower()

    # myślniki traktujemy jako separatory
    text = text.replace("-", " ")

    # usuwamy nadmiarowe znaki
    text = re.sub(r"[(),./]", " ", text)

    # wielokrotne spacje
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ---------------------------------------------------------
# MODEL
# ---------------------------------------------------------

def extract_model(query):
    """
    Wyciąga główny numer modelu.

    Przykłady:
        RTX 5060       -> 5060
        RX 7900 XTX    -> 7900
        Ryzen 5 7500F  -> 7500F
        i5-14600K      -> 14600K
    """

    q = normalize(query)

    # Ryzen / Intel:
    # 7500F, 7800X3D, 14600K, 14900KF
    match = re.search(
        r"\b\d{3,5}(?:[a-z]{1,4})?\b",
        q
    )

    if match:
        return match.group(0)

    # GPU / inne
    match = re.search(
        r"\b\d{3,5}\b",
        q
    )

    return match.group(0) if match else None


# ---------------------------------------------------------
# WARIANT MODELU
# ---------------------------------------------------------

def extract_variant(text):
    """
    Wyciąga wariant modelu.

    Przykłady:

        RTX 5060       -> ""
        RTX 5060 Ti    -> ti
        RTX 5060 Super -> super

        RX 7900 XT     -> xt
        RX 7900 XTX    -> xtx

        Ryzen 7 7800X3D -> x3d
        Ryzen 7 7800X   -> x

        14600K          -> k
        14600KF         -> kf
    """

    text = normalize(text)

    # Najpierw warianty wieloznakowe
    variants = [
        "xtx",
        "x3d",
        "super",
        "ultra",
        "max",
        "kf",
        "ks",
        "xe",
        "xt",
        "ti",
        "k",
        "x",
        "f",
    ]

    for variant in variants:

        if re.search(
            rf"\b{re.escape(variant)}\b",
            text
        ):
            return variant

    return ""


# ---------------------------------------------------------
# CPU SOCKET / TYP
# ---------------------------------------------------------

def extract_cpu_family(text):
    """
    Rozpoznaje rodzinę CPU.

    Przykłady:
        Ryzen 5 7500F -> ryzen5
        Ryzen 7 7800X3D -> ryzen7
        Intel Core i5-14600K -> i5
        Intel Core i7-14700K -> i7
    """

    text = normalize(text)

    match = re.search(
        r"\bryzen\s+([3579])\b",
        text
    )

    if match:
        return f"ryzen{match.group(1)}"

    match = re.search(
        r"\bi([3579])\b",
        text
    )

    if match:
        return f"i{match.group(1)}"

    return None


# ---------------------------------------------------------
# KATEGORIA
# ---------------------------------------------------------

def detect_category(query):

    q = normalize(query)

    if any(
        x in q
        for x in [
            "rtx",
            "radeon",
            "geforce",
            "arc",
            "gpu",
            "karta",
        ]
    ):
        return "gpu"

    if any(
        x in q
        for x in [
            "ram",
            "ddr",
        ]
    ):
        return "ram"

    if any(
        x in q
        for x in [
            "ssd",
            "nvme",
            "m.2",
        ]
    ):
        return "ssd"

    if any(
        x in q
        for x in [
            "ryzen",
            "intel",
            "procesor",
            "core i3",
            "core i5",
            "core i7",
            "core i9",
        ]
    ):
        return "cpu"

    return "other"


# ---------------------------------------------------------
# MODEL MATCH
# ---------------------------------------------------------

def match_model(name, model):

    if not model:
        return True

    name = normalize(name)
    model = normalize(model)

    # model musi być osobnym tokenem
    return bool(
        re.search(
            rf"(?<!\d){re.escape(model)}(?!\d)",
            name
        )
    )


# ---------------------------------------------------------
# WARIANT MATCH
# ---------------------------------------------------------

def variant_match(name, query):
    """
    Sprawdza, czy wariant produktu odpowiada zapytaniu.

    Najważniejsza część parsera:

        RTX 5060       != RTX 5060 Ti
        RTX 5060       != RTX 5060 Super

        RX 7900 XT     != RX 7900 XTX

        Ryzen 7800X    != Ryzen 7800X3D
    """

    name_variant = extract_variant(name)
    query_variant = extract_variant(query)

    # Jeżeli zapytanie ma konkretny wariant,
    # produkt musi mieć dokładnie ten sam wariant.
    if query_variant:

        return name_variant == query_variant

    # Jeżeli zapytanie NIE ma wariantu,
    # nie wolno przepuszczać produktu z wariantem.
    if name_variant:

        return False

    return True


# ---------------------------------------------------------
# CPU FAMILY MATCH
# ---------------------------------------------------------

def cpu_family_match(name, query):

    query_family = extract_cpu_family(query)

    if not query_family:
        return True

    name_family = extract_cpu_family(name)

    if not name_family:
        return False

    return name_family == query_family


# ---------------------------------------------------------
# CATEGORY MATCH
# ---------------------------------------------------------

def category_match(name, category):

    name = normalize(name)

    if category == "gpu":

        return any(
            x in name
            for x in [
                "rtx",
                "geforce",
                "radeon",
                "rx ",
                "arc",
            ]
        )

    if category == "ram":

        return any(
            x in name
            for x in [
                "ram",
                "ddr4",
                "ddr5",
            ]
        )

    if category == "ssd":

        return any(
            x in name
            for x in [
                "ssd",
                "nvme",
                "m.2",
            ]
        )

    if category == "cpu":

        return any(
            x in name
            for x in [
                "ryzen",
                "intel",
                "core",
                "procesor",
            ]
        )

    return True


# ---------------------------------------------------------
# GARBAGE
# ---------------------------------------------------------

def is_garbage(name):

    name = normalize(name)

    return any(
        x in name
        for x in BAD_WORDS
    )


# ---------------------------------------------------------
# VALID NAME
# ---------------------------------------------------------

def is_valid_name(
    name,
    query=None
):

    name = normalize(name)

    if any(
        x in name
        for x in BLACKLIST
    ):
        return False

    if is_garbage(name):
        return False

    return True


# ---------------------------------------------------------
# GŁÓWNE DOPASOWANIE
# ---------------------------------------------------------

def product_matches_query(name, query):

    model = extract_model(query)
    category = detect_category(query)

    # podstawowy model
    if not match_model(name, model):
        return False

    # kategoria
    if not category_match(name, category):
        return False

    # wariant
    if not variant_match(name, query):
        return False

    # Ryzen 5 vs Ryzen 7 / Intel i5 vs i7
    if category == "cpu":

        if not cpu_family_match(name, query):
            return False

    return True


# ---------------------------------------------------------
# PRICE
# ---------------------------------------------------------

def parse_price(aria):

    if not aria:
        return None

    aria = aria.lower()

    # np.
    # 562 złote i 99 groszy
    # 562 złotych i 99 groszy
    match = re.search(
        r"([\d\s]+)\s*złot(?:e|ych)\s*i\s*(\d+)\s*groszy",
        aria
    )

    if match:

        whole = match.group(1).replace(
            " ",
            ""
        )

        cents = match.group(2).zfill(2)

        return f"{whole},{cents} zł"

    # np.
    # 562 złote
    # 562 złotych
    match = re.search(
        r"([\d\s]+)\s*złot(?:e|ych)",
        aria
    )

    if match:

        whole = match.group(1).replace(
            " ",
            ""
        )

        return f"{whole},00 zł"

    return None
