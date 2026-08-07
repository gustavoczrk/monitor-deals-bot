import json
import tempfile
import unittest
from pathlib import Path

from state import (
    load_state,
    new_state,
    record_notification,
    record_observation,
    save_state,
    should_notify,
)


AMAZON_KEY = "amazon:B0BSH2VZ5C"
KABUM_KEY = "kabum:747516"


def notified_state(
    price: float = 1289.0,
    classification: str = "deal",
    key: str = AMAZON_KEY,
) -> dict:
    state = new_state()
    record_notification(state, key, price, classification)
    return state


class NotificationDecisionTests(unittest.TestCase):
    def test_missing_offer_state_is_eligible(self):
        self.assertTrue(should_notify(new_state(), AMAZON_KEY, 1289.0, "deal"))

    def test_first_deal_notifies(self):
        self.assertTrue(should_notify(new_state(), AMAZON_KEY, 1289.0, "deal"))

    def test_first_hot_notifies(self):
        self.assertTrue(should_notify(new_state(), AMAZON_KEY, 1199.0, "hot"))

    def test_same_price_and_classification_is_silent(self):
        state = notified_state()

        self.assertFalse(should_notify(state, AMAZON_KEY, 1289.0, "deal"))

    def test_small_drop_in_deal_is_silent(self):
        state = notified_state()

        self.assertFalse(should_notify(state, AMAZON_KEY, 1279.0, "deal"))

    def test_material_drop_uses_amount_or_percentage(self):
        cases = (
            (notified_state(1289.0), 1239.0),
            (notified_state(900.0), 855.0),
        )
        for state, price in cases:
            with self.subTest(price=price):
                self.assertTrue(should_notify(state, AMAZON_KEY, price, "deal"))

    def test_deal_to_hot_always_notifies(self):
        state = notified_state(1201.0, "deal")

        self.assertTrue(should_notify(state, AMAZON_KEY, 1199.0, "hot"))

    def test_price_increase_in_deal_is_silent(self):
        state = notified_state(1250.0, "deal")

        self.assertFalse(should_notify(state, AMAZON_KEY, 1280.0, "deal"))

    def test_deal_to_ignore_records_out_of_range(self):
        state = notified_state()

        record_observation(state, AMAZON_KEY, 1400.0, "ignore")

        self.assertFalse(should_notify(state, AMAZON_KEY, 1400.0, "ignore"))
        self.assertTrue(state["offers"][AMAZON_KEY]["out_of_range"])

    def test_deal_ignore_deal_notifies_again(self):
        state = notified_state(1289.0, "deal")
        record_observation(state, AMAZON_KEY, 1400.0, "ignore")

        self.assertTrue(should_notify(state, AMAZON_KEY, 1289.0, "deal"))

    def test_hot_to_deal_is_silent(self):
        state = notified_state(1190.0, "hot")

        self.assertFalse(should_notify(state, AMAZON_KEY, 1250.0, "deal"))

    def test_store_keys_are_independent(self):
        state = notified_state(key=AMAZON_KEY)

        self.assertFalse(should_notify(state, AMAZON_KEY, 1289.0, "deal"))
        self.assertTrue(should_notify(state, KABUM_KEY, 1289.0, "deal"))


class StateFileTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "state.json"

    def test_missing_file_returns_empty_state(self):
        self.assertEqual(load_state(self.path), new_state())

    def test_invalid_json_fails_closed(self):
        self.path.write_text("{invalid", encoding="utf-8")

        with self.assertRaisesRegex(RuntimeError, "JSON inválido"):
            load_state(self.path)

    def test_invalid_structure_fails_closed(self):
        self.path.write_text(json.dumps({"offers": []}), encoding="utf-8")

        with self.assertRaisesRegex(RuntimeError, "Estrutura inválida"):
            load_state(self.path)

    def test_save_and_load_preserve_state(self):
        state = notified_state()
        record_observation(state, KABUM_KEY, 1459.99, "ignore")

        save_state(state, self.path)

        self.assertEqual(load_state(self.path), state)
        self.assertEqual(list(Path(self.directory.name).iterdir()), [self.path])


if __name__ == "__main__":
    unittest.main()
