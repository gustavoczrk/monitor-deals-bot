import html
import re
import urllib.error
import urllib.request
from dataclasses import dataclass


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/151.0 Safari/537.36"
)


@dataclass(frozen=True)
class AmazonOffer:
    asin: str
    title: str
    cash_price: float
    card_price: float | None
    availability: str
    seller: str | None
    url: str


def _plain_text(source: str) -> str:
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", source, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _extract_divs(source: str, element_id: str) -> list[str]:
    openings = list(re.finditer(
        rf'<div\b[^>]*\bid=["\']{re.escape(element_id)}["\'][^>]*>',
        source,
        flags=re.IGNORECASE,
    ))
    blocks = []
    for opening in openings:
        depth = 1
        for tag in re.finditer(
            r"<div\b[^>]*>|</div\s*>", source[opening.end():], re.I
        ):
            depth += -1 if tag.group(0).lower().startswith("</") else 1
            if depth == 0:
                blocks.append(source[opening.start():opening.end() + tag.end()])
                break
    return blocks


def _extract_div(source: str, element_id: str) -> str | None:
    blocks = _extract_divs(source, element_id)
    return blocks[0] if blocks else None


def _opening_tag(block: str) -> str:
    match = re.match(r"<div\b[^>]*>", block, re.IGNORECASE)
    return match.group(0) if match else ""


def _has_asin(block: str, expected_asin: str) -> bool:
    return re.search(
        rf'data-csa-c-asin=["\']{re.escape(expected_asin)}["\']',
        _opening_tag(block),
        re.IGNORECASE,
    ) is not None


def _parse_brl(value: str, label: str) -> float:
    normalized = _plain_text(value).replace("\xa0", " ").strip()
    match = re.fullmatch(
        r"R\$\s*(-?(?:\d{1,3}(?:\.\d{3})*|\d+)),(\d{2})",
        normalized,
    )
    if not match:
        raise RuntimeError(f"A Amazon retornou {label} inválido: {normalized!r}.")

    price = float(f"{match.group(1).replace('.', '')}.{match.group(2)}")
    if price <= 0:
        raise RuntimeError(f"A Amazon retornou {label} inválido.")
    return price


def _extract_cash_prices(core_blocks: list[str]) -> list[float]:
    values = []
    marker_found = False
    pattern = re.compile(
        r'<span\b[^>]*class=["\'][^"\']*\bapex-pricetopay-value\b'
        r'[^"\']*["\'][^>]*>\s*'
        r'<span\b[^>]*class=["\'][^"\']*\ba-offscreen\b[^"\']*'
        r'["\'][^>]*>(?P<value>.*?)</span>',
        flags=re.IGNORECASE | re.DOTALL,
    )
    accessibility_pattern = re.compile(
        r'<span\b[^>]*id=["\']apex-pricetopay-accessibility-label["\']'
        r'[^>]*>(?P<value>.*?)</span>',
        flags=re.IGNORECASE | re.DOTALL,
    )

    for block in core_blocks:
        marker_found |= bool(re.search(r"priceToPay|apex-pricetopay", block, re.I))
        for candidate_pattern in (pattern, accessibility_pattern):
            for match in candidate_pattern.finditer(block):
                value_text = _plain_text(match.group("value"))
                if value_text:
                    values.append(_parse_brl(value_text, "priceToPay"))

    if not values:
        if marker_found:
            raise RuntimeError(
                "A estrutura priceToPay da Amazon não contém um preço válido."
            )
        raise RuntimeError("Preço principal priceToPay ausente na Amazon.")
    return values


def _extract_card_price(source: str, expected_asin: str) -> float | None:
    blocks = [
        block
        for block in _extract_divs(source, "installmentCalculatorCentral_feature_div")
        if _has_asin(block, expected_asin)
    ]
    values = []
    pattern = re.compile(
        r"\bou\s*(R\$\s*\d[\d.]*,\d{2})\s*em até\s*\d+x de\s*"
        r"R\$\s*\d[\d.]*,\d{2}",
        re.IGNORECASE,
    )
    for block in blocks:
        for match in pattern.finditer(_plain_text(block)):
            values.append(_parse_brl(match.group(1), "preço no cartão"))

    unique_values = set(values)
    if len(unique_values) > 1:
        raise RuntimeError("A Amazon retornou preços no cartão conflitantes.")
    return values[0] if values else None


def _find_seller(source: str, expected_asin: str) -> str | None:
    blocks = [
        block
        for block in _extract_divs(source, "merchantInfoFeature_feature_div")
        if _has_asin(block, expected_asin)
    ]
    pattern = re.compile(
        r'<a\b[^>]*id=["\']sellerProfileTriggerId["\'][^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    sellers = {
        _plain_text(match.group(1))
        for block in blocks
        for match in pattern.finditer(block)
        if _plain_text(match.group(1))
    }
    return sellers.pop() if len(sellers) == 1 else None


def build_amazon_request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "DNT": "1",
        },
    )


def parse_amazon_offer(
    source: str,
    expected_asin: str,
    expected_model: str,
    url: str,
) -> AmazonOffer:
    plain = _plain_text(source)
    if re.search(
        r"captcha|validateCaptcha|digite os caracteres|type the characters",
        source,
        re.IGNORECASE,
    ):
        raise RuntimeError("A Amazon retornou uma página de captcha.")
    if re.search(
        r"Robot Check|automated access|acesso automatizado|"
        r"To discuss automated access",
        plain,
        re.IGNORECASE,
    ):
        raise RuntimeError("A Amazon bloqueou a consulta automatizada.")
    if "priceNotAvailable" in source or re.search(
        r"Para ver os detalhes do produto.{0,160}adicione este item ao seu carrinho|"
        r"To see product details.{0,160}add this item to your cart",
        plain,
        re.IGNORECASE,
    ):
        raise RuntimeError("O preço da Amazon está indisponível.")

    title_match = re.search(r"<title\b[^>]*>(.*?)</title>", source, re.I | re.S)
    title = _plain_text(title_match.group(1)) if title_match else ""
    if expected_model.casefold() not in title.casefold():
        raise RuntimeError(
            f"Modelo {expected_model} não encontrado no título da Amazon."
        )

    apex_blocks = [
        block for block in _extract_divs(source, "apex_desktop")
        if _has_asin(block, expected_asin)
    ]
    core_blocks = [
        block for block in _extract_divs(source, "corePrice_feature_div")
        if _has_asin(block, expected_asin)
    ]
    add_to_cart = [
        block for block in _extract_divs(source, "addToCart_feature_div")
        if _has_asin(block, expected_asin)
    ]
    buy_now = [
        block for block in _extract_divs(source, "buyNow_feature_div")
        if _has_asin(block, expected_asin)
    ]
    if not apex_blocks or not core_blocks or not add_to_cart or not buy_now:
        raise RuntimeError(
            f"Oferta principal do ASIN {expected_asin} não confirmada na Amazon."
        )

    availabilities = {
        _plain_text(block)
        for block in _extract_divs(source, "availability")
        if _plain_text(block)
    }
    if any(
        re.search(
            r"indisponível|sem estoque|fora de estoque|não disponível",
            availability,
            re.IGNORECASE,
        )
        for availability in availabilities
    ):
        raise RuntimeError(
            f"Produto indisponível na Amazon: {', '.join(sorted(availabilities))}."
        )
    if len(availabilities) != 1:
        raise RuntimeError("Disponibilidade de compra ambígua na Amazon.")
    availability = availabilities.pop()
    if not re.search(r"\bem estoque\b", availability, re.IGNORECASE):
        raise RuntimeError("Disponibilidade de compra não confirmada na Amazon.")

    cash_prices = set(_extract_cash_prices(core_blocks))
    if len(cash_prices) != 1:
        raise RuntimeError("A Amazon retornou preços priceToPay conflitantes.")

    return AmazonOffer(
        asin=expected_asin,
        title=title,
        cash_price=cash_prices.pop(),
        card_price=_extract_card_price("".join(apex_blocks), expected_asin),
        availability=availability,
        seller=_find_seller(source, expected_asin),
        url=url,
    )


def fetch_amazon_offer(
    url: str,
    expected_asin: str,
    expected_model: str,
) -> AmazonOffer:
    request = build_amazon_request(url)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"A Amazon respondeu com HTTP {response.status}."
                )
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type.casefold():
                raise RuntimeError(
                    f"A Amazon retornou Content-Type inesperado: {content_type}."
                )
            charset = response.headers.get_content_charset() or "utf-8"
            source = response.read().decode(charset, errors="replace")
            final_url = response.geturl()
    except urllib.error.HTTPError as error:
        raise RuntimeError(
            f"A Amazon respondeu com HTTP {error.code}."
        ) from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        reason = getattr(error, "reason", error)
        raise RuntimeError(
            f"Não foi possível acessar a Amazon: {reason}"
        ) from error

    return parse_amazon_offer(source, expected_asin, expected_model, final_url)
