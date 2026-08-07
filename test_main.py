import unittest
from unittest.mock import patch

from main import evaluate_price, process_offer, send_notification


class EvaluatePriceTests(unittest.TestCase):
    monitor = {"alert_price": 1300.0, "hot_price": 1200.0}

    def test_ignores_price_above_alert_limit(self):
        self.assertEqual(evaluate_price(self.monitor, 1300.01), "ignore")

    def test_classifies_price_at_alert_limit_as_deal(self):
        self.assertEqual(evaluate_price(self.monitor, 1300.0), "deal")

    def test_classifies_price_at_hot_limit_as_hot(self):
        self.assertEqual(evaluate_price(self.monitor, 1200.0), "hot")

    def test_rejects_invalid_prices(self):
        for price in (0, -1, float("nan"), float("inf"), True, "1200"):
            with self.subTest(price=price):
                with self.assertRaisesRegex(ValueError, "maior que zero"):
                    evaluate_price(self.monitor, price)

    @patch.dict("os.environ", {"NTFY_TOPIC": ""})
    def test_ignore_does_not_require_ntfy_topic(self):
        process_offer(
            model="ASUS TUF VG27AQ5A",
            price=1499.99,
            store="Kabum",
            url="https://example.invalid/product",
        )

    @patch.dict("os.environ", {"NTFY_TOPIC": ""})
    def test_notification_requires_ntfy_topic(self):
        with self.assertRaisesRegex(RuntimeError, "NTFY_TOPIC não configurada"):
            send_notification("Oferta", "Mensagem")


if __name__ == "__main__":
    unittest.main()
