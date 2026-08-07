import argparse
import re
import urllib.error
import urllib.request
from pathlib import Path

from amazon import _extract_div, _plain_text, build_amazon_request

MONEY_PATTERN = re.compile(r"R\$\s*\d[\d.]*,\d{2}", re.IGNORECASE)


def _classify_candidate(context: str) -> tuple[str, str]:
    lowered = context.casefold()
    if "apex-pricetopay" in lowered or "pricetopay" in lowered:
        return "primary", "corePrice / priceToPay"
    if any(marker in lowered for marker in ("basisprice", "listprice", "a-text-price")):
        return "old_price", "corePrice / basis or list price"
    if any(marker in lowered for marker in ("installment", "monthly", "parcela")):
        return "installment", "corePrice / installment"
    if any(marker in lowered for marker in ("saving", "discount", "desconto")):
        return "saving", "corePrice / savings"
    return "unclassified", "corePrice / a-offscreen"


def _core_price_candidates(core_price: str | None) -> list[dict[str, str]]:
    if not core_price:
        return []

    candidates = []
    seen = set()
    pattern = re.compile(
        r'<span\b[^>]*class=["\'][^"\']*\ba-offscreen\b[^"\']*["\'][^>]*>'
        r'(?P<value>.*?)</span>',
        flags=re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(core_price):
        value_match = MONEY_PATTERN.search(_plain_text(match.group("value")))
        if not value_match:
            continue
        context = core_price[max(0, match.start() - 700):match.start()]
        kind, structure = _classify_candidate(context)
        value = re.sub(r"\s+", " ", value_match.group(0)).strip()
        key = (kind, value, structure)
        if key not in seen:
            seen.add(key)
            candidates.append(
                {"kind": kind, "value": value, "structure": structure}
            )
    return candidates


def _append_candidate(
    candidates: list[dict[str, str]],
    kind: str,
    value: str,
    structure: str,
) -> None:
    candidate = {"kind": kind, "value": value.strip(), "structure": structure}
    if candidate not in candidates:
        candidates.append(candidate)


def analyze_html(source: str, expected_asin: str, expected_model: str) -> dict:
    plain = _plain_text(source)
    title_match = re.search(r"<title\b[^>]*>(.*?)</title>", source, re.I | re.S)
    title = _plain_text(title_match.group(1)) if title_match else ""
    core_price = _extract_div(source, "corePrice_feature_div")
    core_opening = re.match(r"<div\b[^>]*>", core_price or "", re.I)
    core_attributes = core_opening.group(0) if core_opening else ""
    apex = _extract_div(source, "apex_desktop")
    apex_opening = re.match(r"<div\b[^>]*>", apex or "", re.I)
    apex_attributes = apex_opening.group(0) if apex_opening else ""
    core_display = _extract_div(source, "corePriceDisplay_desktop_feature_div")
    installments = _extract_div(source, "installmentCalculatorCentral_feature_div")
    twister = _extract_div(source, "twisterPlusWWDesktop")
    buybox = _extract_div(source, "desktop_buybox")
    merchant = _extract_div(source, "merchantInfoFeature_feature_div")
    availability = _extract_div(source, "availability")
    candidates = _core_price_candidates(core_price)

    old_price_match = re.search(
        r"De:\s*(R\$\s*\d[\d.]*,\d{2})",
        _plain_text(core_display or ""),
        re.IGNORECASE,
    )
    if old_price_match:
        _append_candidate(
            candidates,
            "old_reference",
            old_price_match.group(1),
            "corePriceDisplay / basisPrice (média de 90 dias)",
        )

    installment_match = re.search(
        r"ou\s*(R\$\s*\d[\d.]*,\d{2})\s*em até\s*(\d+)x de\s*"
        r"(R\$\s*\d[\d.]*,\d{2})",
        _plain_text(installments or ""),
        re.IGNORECASE,
    )
    if installment_match:
        _append_candidate(
            candidates,
            "installment_total",
            installment_match.group(1),
            "installmentCalculatorCentral / total",
        )
        _append_candidate(
            candidates,
            "installment",
            installment_match.group(3),
            f"installmentCalculatorCentral / {installment_match.group(2)} parcelas",
        )

    twister_match = re.search(
        r'"displayPrice"\s*:\s*"(R\$\s*\d[\d.]*,\d{2})"\s*,\s*'
        r'"priceAmount"\s*:\s*([0-9.]+)',
        twister or "",
        re.IGNORECASE,
    )
    if twister_match:
        _append_candidate(
            candidates,
            "buybox_display",
            twister_match.group(1),
            "twisterPlusWWDesktop / displayPrice and priceAmount",
        )

    shipping_match = re.search(
        r"Entrega\s*(R\$\s*\d+(?:,\d{2})?)",
        _plain_text(buybox or ""),
        re.IGNORECASE,
    )
    if shipping_match:
        _append_candidate(
            candidates,
            "shipping",
            shipping_match.group(1),
            "desktop_buybox / entrega",
        )

    asin_attribute = rf'data-csa-c-asin=["\']{re.escape(expected_asin)}["\']'
    add_to_cart = _extract_div(source, "addToCart_feature_div")
    buy_now = _extract_div(source, "buyNow_feature_div")

    return {
        "title": title,
        "asin_found": expected_asin.casefold() in source.casefold(),
        "model_found": expected_model.casefold() in source.casefold(),
        "captcha": bool(re.search(
            r"captcha|validateCaptcha|digite os caracteres|type the characters",
            source,
            re.IGNORECASE,
        )),
        "blocked": bool(re.search(
            r"Robot Check|automated access|acesso automatizado|"
            r"To discuss automated access",
            plain,
            re.IGNORECASE,
        )),
        "price_not_available": "priceNotAvailable" in source,
        "add_to_cart_message": bool(re.search(
            r"Para ver os detalhes do produto.{0,160}adicione este item ao seu carrinho|"
            r"To see product details.{0,160}add this item to your cart",
            plain,
            re.IGNORECASE,
        )),
        "core_price_found": core_price is not None,
        "core_price_asin_matches": bool(re.search(
            asin_attribute,
            core_attributes,
            re.IGNORECASE,
        )),
        "apex_asin_matches": bool(re.search(
            asin_attribute, apex_attributes, re.IGNORECASE
        )),
        "buybox_controls_asin_match": bool(
            re.search(asin_attribute, add_to_cart or "", re.IGNORECASE)
            and re.search(asin_attribute, buy_now or "", re.IGNORECASE)
        ),
        "availability": _plain_text(availability or ""),
        "merchant": _plain_text(merchant or ""),
        "coupon_found": bool(re.search(r"cupom|coupon", apex or "", re.I)),
        "price_candidates": candidates,
    }


def fetch_page(url: str) -> tuple[dict, bytes]:
    request = build_amazon_request(url)
    try:
        response = urllib.request.urlopen(request, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        reason = getattr(error, "reason", error)
        raise RuntimeError(f"Não foi possível acessar a Amazon: {reason}") from error

    with response:
        body = response.read()
        metadata = {
            "status": response.status,
            "final_url": response.geturl(),
            "content_type": response.headers.get("Content-Type", ""),
            "charset": response.headers.get_content_charset() or "utf-8",
        }
    return metadata, body


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnóstico HTTP da Amazon")
    parser.add_argument("url")
    parser.add_argument("asin")
    parser.add_argument("model")
    parser.add_argument("--save-html", type=Path)
    args = parser.parse_args()

    metadata, body = fetch_page(args.url)
    source = body.decode(metadata["charset"], errors="replace")
    report = analyze_html(source, args.asin, args.model)

    if args.save_html:
        args.save_html.write_bytes(body)

    print(f"HTTP status: {metadata['status']}")
    print(f"URL final: {metadata['final_url']}")
    print(f"Tamanho: {len(body)} bytes")
    print(f"Content-Type: {metadata['content_type']}")
    for key, value in report.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        raise SystemExit(f"Erro: {error}") from error
