import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils.screenshot import Screenshot


class InventoryTabActiveTest(unittest.TestCase):
    def _screenshot_with(self, img):
        screenshot = Screenshot.__new__(Screenshot)
        screenshot._take_screenshot = Mock(return_value=img)
        return screenshot

    def test_selected_tab_is_detected(self):
        img = Image.new("RGB", (77, 65), (60, 60, 60))
        img.paste((255, 255, 255), (10, 10, 40, 40))
        self.assertTrue(self._screenshot_with(img).inventory_tab_active(0.43, 0.06))

    def test_unselected_tab_is_rejected(self):
        img = Image.new("RGB", (77, 65), (60, 60, 60))
        img.paste((195, 195, 195), (10, 10, 40, 40))
        self.assertFalse(self._screenshot_with(img).inventory_tab_active(0.43, 0.06))


if __name__ == "__main__":
    unittest.main()
