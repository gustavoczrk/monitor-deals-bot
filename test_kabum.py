import unittest
import urllib.error
from unittest.mock import patch

from kabum import extract_kabum_price, fetch_kabum_price


class ExtractKabumPriceTests(unittest.TestCase):
    def test_extracts_discount_price_from_kabum_structure(self):
        html = (
            '<script>window.data={'
            '"friendlyName":"monitor-gamer-asus-tuf-vg27aq5a",'
            '"prices":{"oldPrice":2222.22,"priceWithDiscount":1499.99,'
            '"price":1666.66,"discountPercentage":10}'
            '}</script>'
        )

        price = extract_kabum_price(html, "VG27AQ5A")

        self.assertEqual(price, 1499.99)

    def test_uses_discount_price_instead_of_other_prices(self):
        html = (
            '"friendlyName":"Monitor TEST-27",'
            '"prices":{"oldPrice":2200,"priceWithDiscount":1499.99,'
            '"price":1666.66}'
        )

        self.assertEqual(extract_kabum_price(html, "TEST-27"), 1499.99)

    def test_same_parser_supports_all_configured_kabum_models(self):
        for model in ("VG27AQ5A", "GS27QA-AS", "PG27QFT1B", "XG27ACS"):
            with self.subTest(model=model):
                html = (
                    f'"friendlyName":"monitor-gamer-{model.lower()}",'
                    '"prices":{"priceWithDiscount":1299.99}'
                )

                self.assertEqual(extract_kabum_price(html, model), 1299.99)

    def test_rejects_missing_expected_model(self):
        html = (
            '"friendlyName":"Monitor OUTRO",'
            '"prices":{"priceWithDiscount":999.99}'
        )

        with self.assertRaisesRegex(RuntimeError, "não encontrado"):
            extract_kabum_price(html, "TEST-27")

    def test_rejects_model_as_part_of_another_code(self):
        html = (
            '"friendlyName":"Monitor TEST-270",'
            '"prices":{"priceWithDiscount":999.99}'
        )

        with self.assertRaisesRegex(RuntimeError, "não encontrado"):
            extract_kabum_price(html, "TEST-27")

    def test_rejects_missing_discount_price(self):
        html = '"friendlyName":"Monitor TEST-27","prices":{"price":999.99}'

        with self.assertRaisesRegex(RuntimeError, "não informou"):
            extract_kabum_price(html, "TEST-27")

    def test_rejects_invalid_discount_prices(self):
        for value in ("0", "-1", '"1499.99"', "null", "true"):
            with self.subTest(value=value):
                html = (
                    '"friendlyName":"Monitor TEST-27",'
                    f'"prices":{{"priceWithDiscount":{value}}}'
                )

                with self.assertRaisesRegex(RuntimeError, "inválido"):
                    extract_kabum_price(html, "TEST-27")

    def test_rejects_conflicting_prices_for_same_model(self):
        html = (
            '"friendlyName":"Monitor TEST-27",'
            '"prices":{"priceWithDiscount":1499.99}'
            '"friendlyName":"Monitor TEST-27",'
            '"prices":{"priceWithDiscount":999.99}'
        )

        with self.assertRaisesRegex(RuntimeError, "conflitantes"):
            extract_kabum_price(html, "TEST-27")

    @patch("kabum.urllib.request.urlopen")
    def test_reports_network_error_clearly(self, urlopen):
        urlopen.side_effect = urllib.error.URLError("sem conexão")

        with self.assertRaisesRegex(RuntimeError, "Não foi possível acessar"):
            fetch_kabum_price("https://example.invalid/product", "TEST-27")


if __name__ == "__main__":
    unittest.main()
