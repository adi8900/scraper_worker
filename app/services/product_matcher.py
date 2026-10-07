import json
import os
import urllib.request


OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://ollama:11434"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "phi3:mini"
)


def match_products(query, products):
    """
    Zwraca:
        list[int] - indeksy produktów pasujących do zapytania
        []        - Ollama odpowiedziała, ale nie znalazła dopasowania
        None      - błąd Ollamy -> używany jest fallback
    """

    if not products:
        return []

    product_lines = [
        f"{i}: {product['name']}"
        for i, product in enumerate(products)
    ]

    products_text = "\n".join(product_lines)

    prompt = f"""
You are a product matching system.

User search:
{query}

Candidate products:
{products_text}

Select ONLY products that are actual matches for the user's search.

Rules:
- The exact requested product model must match.
- Manufacturer differences are allowed.
- Different cooler, edition, factory overclocking or memory size are allowed.
- RTX 5060 is NOT RTX 5060 Ti.
- RTX 5060 is NOT RTX 5060 Super.
- RTX 5070 is NOT RTX 5060.
- Ryzen 5 7500F is NOT Ryzen 5 7600.
- Ryzen 5 7500F is NOT Ryzen 7 7500F.
- Different CPU/GPU generations are different products.
- Accessories, cables, adapters, cases, cooling products and toys are NOT matches.
- A product mentioning the requested model only as compatibility information is NOT a match.
- Do not consider price.
- Do not consider ranking.
- Match the actual product described by its name.

Return ONLY valid JSON.

{{"matches":[0,2,5]}}

If nothing matches:

{{"matches":[]}}
"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0
        }
    }

    try:
        request = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json"
            },
            method="POST"
        )

        with urllib.request.urlopen(
            request,
            timeout=60
        ) as response:

            data = json.loads(
                response.read().decode("utf-8")
            )

        text = data.get(
            "response",
            ""
        ).strip()

        print(
            "[OLLAMA] RESPONSE:",
            text
        )

        result = json.loads(text)

        if not isinstance(result, dict):
            print(
                "[OLLAMA] Invalid response format"
            )
            return None

        matches = result.get(
            "matches"
        )

        if not isinstance(matches, list):
            print(
                "[OLLAMA] Missing matches"
            )
            return None

        valid_ids = []

        for value in matches:

            if (
                isinstance(value, int)
                and 0 <= value < len(products)
            ):
                valid_ids.append(value)

        return valid_ids

    except Exception as e:

        print(
            "[OLLAMA ERROR]:",
            e
        )

        return None
