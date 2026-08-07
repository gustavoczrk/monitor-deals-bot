import unittest

from main import evaluate_price
from watchlist import MONITORS


EXPECTED_PRODUCTS = {
    "ASUS TUF VG27AQ5A": (1300.0, 1200.0),
    "Gigabyte GS27QA-AS": (1250.0, 1150.0),
    "ASRock Phantom Gaming PG27QFT1B": (1200.0, 1100.0),
    "ASUS ROG Strix XG27ACS": (1350.0, 1250.0),
}
EXPECTED_KABUM = {
    "747516": (
        "VG27AQ5A",
        "https://www.kabum.com.br/produto/747516/"
        "monitor-gamer-asus-tuf-27-qhd-210hz-0-3ms-fast-ips-"
        "g-sync-comp-freesync-premium-hdr10-som-integrado-vg27aq5a",
    ),
    "613323": (
        "GS27QA-AS",
        "https://www.kabum.com.br/produto/613323/"
        "monitor-gamer-gigabyte-27-qhd-180hz-1ms-ips-vrr-"
        "freesync-hdr-ready-preto-gs27qa-as",
    ),
    "911990": (
        "PG27QFT1B",
        "https://www.kabum.com.br/produto/911990/"
        "monitor-gamer-asrock-phantom-27-qhd-180hz-1ms-ips-"
        "freesync-premium-hdr-400-displayport-e-hdmi-preto-pg27qft1b",
    ),
    "626864": (
        "XG27ACS",
        "https://www.kabum.com.br/produto/626864/"
        "monitor-gamer-asus-rog-strix-27-qhd-180hz-1ms-fast-ips-vrr-"
        "g-sync-freesync-hdr-400-usb-c-altura-ajustavel-xg27acs",
    ),
}


class WatchlistTests(unittest.TestCase):
    def test_contains_exactly_four_official_models(self):
        self.assertEqual(
            {monitor["model"] for monitor in MONITORS},
            set(EXPECTED_PRODUCTS),
        )

    def test_product_thresholds_are_correct(self):
        actual = {
            monitor["model"]: (
                monitor["alert_price"],
                monitor["hot_price"],
            )
            for monitor in MONITORS
        }

        self.assertEqual(actual, EXPECTED_PRODUCTS)

    def test_kabum_ids_models_and_urls_are_correct(self):
        sources = {
            source["id"]: (source["expected_model"], source["url"])
            for monitor in MONITORS
            for source in monitor["sources"]
            if source["store"] == "kabum"
        }

        self.assertEqual(sources, EXPECTED_KABUM)

    def test_amazon_is_associated_only_with_asus_tuf(self):
        amazon_sources = [
            (monitor["model"], source)
            for monitor in MONITORS
            for source in monitor["sources"]
            if source["store"] == "amazon"
        ]

        self.assertEqual(len(amazon_sources), 1)
        model, source = amazon_sources[0]
        self.assertEqual(model, "ASUS TUF VG27AQ5A")
        self.assertEqual(source["id"], "B0BSH2VZ5C")
        self.assertEqual(source["expected_model"], "VG27AQ5A")
        self.assertEqual(
            source["url"], "https://www.amazon.com.br/dp/B0BSH2VZ5C"
        )

    def test_each_product_uses_its_own_thresholds(self):
        for monitor in MONITORS:
            with self.subTest(model=monitor["model"]):
                self.assertEqual(
                    evaluate_price(monitor, monitor["hot_price"]), "hot"
                )
                self.assertEqual(
                    evaluate_price(monitor, monitor["alert_price"]), "deal"
                )
                self.assertEqual(
                    evaluate_price(monitor, monitor["alert_price"] + 0.01),
                    "ignore",
                )


if __name__ == "__main__":
    unittest.main()
