import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PIL import Image as PILImage

from config.const import DATABANK_HEIGHT_RATIO, DATABANK_WIDTH_RATIO
from utils.screenshot import Screenshot

DATABANK_PATH = (
    Path(__file__).resolve().parents[1] / "src" / "assets" / "images" / "databank.png"
)


class ScreenStateTest(unittest.TestCase):
    """inventory_open/escape_menu_open classify screens from OCR text and the Data Bank icon."""

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

    def _escape_menu_open(self, screen):
        screenshot = Screenshot.__new__(Screenshot)
        screenshot.screenshot_screen = Mock(return_value=screen)
        screenshot.databank_img = PILImage.open(DATABANK_PATH)
        screenshot._log_signal = Mock()
        return screenshot.escape_menu_open()

    def _screen(self, with_databank):
        screen = PILImage.new("RGB", (1920, 1080), (10, 10, 10))
        if with_databank:
            needle = PILImage.open(DATABANK_PATH).resize(
                (
                    int(1920 * DATABANK_WIDTH_RATIO),
                    int(1080 * DATABANK_HEIGHT_RATIO),
                )
            )
            screen.paste(needle, (100, 100))
        return screen

    def test_escape_menu_detected(self):
        self.assertTrue(self._escape_menu_open(self._screen(True)))

    def test_escape_menu_not_detected(self):
        self.assertFalse(self._escape_menu_open(self._screen(False)))


if __name__ == "__main__":
    unittest.main()
