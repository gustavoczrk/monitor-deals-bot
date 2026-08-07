import unittest

from amazon_diagnostic import analyze_html


class AmazonDiagnosticTests(unittest.TestCase):
    def test_finds_primary_price_bound_to_expected_asin(self):
        source = (
            '<title>Monitor ASUS VG27AQ5A</title>'
            '<div id="corePrice_feature_div" data-csa-c-asin="B0BSH2VZ5C">'
            '<span class="a-price priceToPay apex-pricetopay-value">'
            '<span class="a-offscreen">R$ 1.287,98</span></span></div>'
        )

        report = analyze_html(source, "B0BSH2VZ5C", "VG27AQ5A")

        self.assertTrue(report["asin_found"])
        self.assertTrue(report["model_found"])
        self.assertTrue(report["core_price_asin_matches"])
        self.assertEqual(
            report["price_candidates"],
            [{
                "kind": "primary",
                "value": "R$ 1.287,98",
                "structure": "corePrice / priceToPay",
            }],
        )

    def test_identifies_unavailable_price_without_candidate(self):
        source = (
            '<title>Monitor ASUS VG27AQ5A</title>'
            '<div data-csa-c-asin="B0BSH2VZ5C">priceNotAvailable '
            'Para ver os detalhes do produto, adicione este item ao seu carrinho.'
            '</div>'
        )

        report = analyze_html(source, "B0BSH2VZ5C", "VG27AQ5A")

        self.assertTrue(report["price_not_available"])
        self.assertTrue(report["add_to_cart_message"])
        self.assertEqual(report["price_candidates"], [])


if __name__ == "__main__":
    unittest.main()
