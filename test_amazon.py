import unittest
import urllib.error
from unittest.mock import patch

from amazon import fetch_amazon_offer, parse_amazon_offer


ASIN = "B0BSH2VZ5C"
MODEL = "VG27AQ5A"
URL = f"https://www.amazon.com.br/dp/{ASIN}"


def amazon_page(
    *,
    asin: str = ASIN,
    model: str = MODEL,
    cash_prices: tuple[str, ...] = ("R$ 1.287,98",),
    card_price: str | None = "R$ 1.399,98",
    availability: str = "Em estoque",
    extra_inside_apex: str = "",
    extra_page: str = "",
) -> str:
    price_html = "".join(
        '<span class="a-price priceToPay apex-pricetopay-value">'
        f'<span class="a-offscreen">{price}</span></span>'
        for price in cash_prices
    )
    card_html = ""
    if card_price is not None:
        card_html = (
            '<div id="installmentCalculatorCentral_feature_div" '
            f'data-csa-c-asin="{asin}">'
            f'ou {card_price} em até 12x de R$ 116,72 sem juros</div>'
        )
    return (
        f"<title>Monitor ASUS TUF {model} | Amazon.com.br</title>"
        f"{extra_page}"
        f'<div id="apex_desktop" data-csa-c-asin="{asin}">'
        f'<div id="corePrice_feature_div" data-csa-c-asin="{asin}">'
        f"{price_html}</div>"
        f"{card_html}"
        f'<div id="availability">{availability}</div>'
        '<div id="merchantInfoFeature_feature_div" '
        f'data-csa-c-asin="{asin}">'
        '<a id="sellerProfileTriggerId">KaBuM!</a></div>'
        f'<div id="addToCart_feature_div" data-csa-c-asin="{asin}"></div>'
        f'<div id="buyNow_feature_div" data-csa-c-asin="{asin}"></div>'
        f"{extra_inside_apex}</div>"
    )


class ParseAmazonOfferTests(unittest.TestCase):
    def test_extracts_valid_price_to_pay(self):
        offer = parse_amazon_offer(amazon_page(), ASIN, MODEL, URL)

        self.assertEqual(offer.asin, ASIN)
        self.assertEqual(offer.cash_price, 1287.98)
        self.assertEqual(offer.availability, "Em estoque")
        self.assertEqual(offer.seller, "KaBuM!")

    def test_extracts_optional_card_price(self):
        offer = parse_amazon_offer(amazon_page(), ASIN, MODEL, URL)
        without_card = parse_amazon_offer(
            amazon_page(card_price=None), ASIN, MODEL, URL
        )

        self.assertEqual(offer.card_price, 1399.98)
        self.assertIsNone(without_card.card_price)

    def test_rejects_wrong_asin(self):
        with self.assertRaisesRegex(RuntimeError, "Oferta principal"):
            parse_amazon_offer(amazon_page(asin="B000WRONG1"), ASIN, MODEL, URL)

    def test_rejects_wrong_model(self):
        with self.assertRaisesRegex(RuntimeError, "Modelo"):
            parse_amazon_offer(amazon_page(model="OUTRO-MODELO"), ASIN, MODEL, URL)

    def test_rejects_captcha(self):
        with self.assertRaisesRegex(RuntimeError, "captcha"):
            parse_amazon_offer(amazon_page(extra_page="validateCaptcha"), ASIN, MODEL, URL)

    def test_rejects_robot_check(self):
        with self.assertRaisesRegex(RuntimeError, "bloqueou"):
            parse_amazon_offer(amazon_page(extra_page="Robot Check"), ASIN, MODEL, URL)

    def test_rejects_missing_price(self):
        with self.assertRaisesRegex(RuntimeError, "priceToPay ausente"):
            parse_amazon_offer(
                amazon_page(cash_prices=()), ASIN, MODEL, URL
            )

    def test_rejects_invalid_price(self):
        for price in ("R$ 0,00", "R$ -1,00", "valor inválido"):
            with self.subTest(price=price):
                with self.assertRaisesRegex(RuntimeError, "priceToPay"):
                    parse_amazon_offer(
                        amazon_page(cash_prices=(price,)), ASIN, MODEL, URL
                    )

    def test_rejects_conflicting_prices(self):
        with self.assertRaisesRegex(RuntimeError, "conflitantes"):
            parse_amazon_offer(
                amazon_page(cash_prices=("R$ 1.287,98", "R$ 999,99")),
                ASIN,
                MODEL,
                URL,
            )

    def test_does_not_use_installment_as_primary_price(self):
        with self.assertRaisesRegex(RuntimeError, "priceToPay ausente"):
            parse_amazon_offer(
                amazon_page(cash_prices=(), card_price="R$ 999,99"),
                ASIN,
                MODEL,
                URL,
            )

    def test_ignores_price_from_other_asin(self):
        related = amazon_page(
            asin="B000RELATED",
            model="MONITOR-RELACIONADO",
            cash_prices=("R$ 99,99",),
        )

        offer = parse_amazon_offer(
            amazon_page(extra_page=related), ASIN, MODEL, URL
        )

        self.assertEqual(offer.cash_price, 1287.98)

    def test_rejects_unavailable_product(self):
        with self.assertRaisesRegex(RuntimeError, "indisponível"):
            parse_amazon_offer(
                amazon_page(availability="Temporariamente fora de estoque"),
                ASIN,
                MODEL,
                URL,
            )

    def test_rejects_hidden_price(self):
        with self.assertRaisesRegex(RuntimeError, "indisponível"):
            parse_amazon_offer(
                amazon_page(extra_page="priceNotAvailable"), ASIN, MODEL, URL
            )

    @patch("amazon.urllib.request.urlopen")
    def test_reports_network_error(self, urlopen):
        urlopen.side_effect = urllib.error.URLError("sem conexão")

        with self.assertRaisesRegex(RuntimeError, "Não foi possível acessar"):
            fetch_amazon_offer(URL, ASIN, MODEL)

    @patch("amazon.urllib.request.urlopen")
    def test_reports_http_error(self, urlopen):
        error = urllib.error.HTTPError(
            URL, 503, "Service Unavailable", {}, None
        )
        urlopen.side_effect = error

        try:
            with self.assertRaisesRegex(RuntimeError, "HTTP 503"):
                fetch_amazon_offer(URL, ASIN, MODEL)
        finally:
            error.close()


if __name__ == "__main__":
    unittest.main()
