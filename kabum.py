import json
import math
import re
import urllib.error
import urllib.request


_PRODUCT_PATTERN = re.compile(
    r'"friendlyName"\s*:\s*(?P<name>"(?:\\.|[^"\\])*")'
    r'\s*,\s*"prices"\s*:\s*(?P<prices>\{[^{}]*\})',
    flags=re.IGNORECASE,
)


def _contains_model(text: str, expected_model: str) -> bool:
    return re.search(
        rf"(?<![a-z0-9]){re.escape(expected_model)}(?![a-z0-9])",
        text,
        flags=re.IGNORECASE,
    ) is not None


def extract_kabum_price(html: str, expected_model: str) -> float:
    if not expected_model.strip():
        raise ValueError("O modelo esperado não pode estar vazio.")

    matching_prices = []

    for match in _PRODUCT_PATTERN.finditer(html):
        try:
            product_name = json.loads(match.group("name"))
            prices = json.loads(match.group("prices"))
        except json.JSONDecodeError:
            continue

        if not _contains_model(product_name, expected_model):
            continue

        if "priceWithDiscount" not in prices:
            raise RuntimeError(
                f"A Kabum não informou priceWithDiscount para {expected_model}."
            )

        price = prices["priceWithDiscount"]
        if (
            isinstance(price, bool)
            or not isinstance(price, (int, float))
        ):
            raise RuntimeError(
                f"A Kabum retornou priceWithDiscount inválido para {expected_model}."
            )

        try:
            numeric_price = float(price)
        except (OverflowError, ValueError):
            numeric_price = math.nan

        if not math.isfinite(numeric_price) or numeric_price <= 0:
            raise RuntimeError(
                f"A Kabum retornou priceWithDiscount inválido para {expected_model}."
            )

        matching_prices.append(numeric_price)

    if not matching_prices:
        if not _contains_model(html, expected_model):
            raise RuntimeError(
                f"Modelo {expected_model} não encontrado na página da Kabum."
            )
        raise RuntimeError(
            "Não foi possível localizar os dados estruturados de preço "
            f"para {expected_model}."
        )

    unique_prices = set(matching_prices)
    if len(unique_prices) != 1:
        raise RuntimeError(
            f"A Kabum retornou preços conflitantes para {expected_model}."
        )

    return matching_prices[0]


def fetch_kabum_price(
    url: str,
    expected_model: str,
) -> float:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/151.0 Safari/537.36"
            )
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            html = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        raise RuntimeError(
            f"A Kabum respondeu com erro HTTP {error.code}."
        ) from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        reason = getattr(error, "reason", error)
        raise RuntimeError(
            f"Não foi possível acessar a Kabum: {reason}"
        ) from error

    return extract_kabum_price(html, expected_model)
