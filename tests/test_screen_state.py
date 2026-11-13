import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils.screenshot import Screenshot


class ScreenStateTest(unittest.TestCase):
    """inventory_open/escape_menu_open classify screens from OCR text."""

    def _probe(self, method, ocr_text):
        screenshot = Screenshot.__new__(Screenshot)
        screenshot._take_screenshot = Mock()
        screenshot.screenshot_quantity = Mock()
        screenshot._log_signal = Mock()
        with patch("utils.screenshot.image_to_string", return_value=ocr_text):
            return getattr(screenshot, method)()

    def test_inventory_open_when_quantity_parses(self):
        self.assertTrue(self._probe("inventory_open", "135/1500"))

    def test_inventory_open_on_currency_tab(self):
        self.assertTrue(self._probe("inventory_open", "835282982"))

    def test_inventory_closed_when_quantity_is_garbage(self):
        self.assertFalse(self._probe("inventory_open", "84"))

    def test_escape_menu_detected(self):
        self.assertTrue(
            self._probe("escape_menu_open", "TrailblazeLevel 70 ar aLevel")
        )

    def test_escape_menu_not_detected(self):
        self.assertFalse(self._probe("escape_menu_open", "007erar"))


if __name__ == "__main__":
    unittest.main()
