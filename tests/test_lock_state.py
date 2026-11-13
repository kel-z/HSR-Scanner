import sys
import unittest
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from services.scanner.parsers.relic_strategy import RelicStrategy


class LockStateTest(unittest.TestCase):
    def parser(self):
        return RelicStrategy.__new__(RelicStrategy)

    def crop(self, fill, patch=None):
        img = Image.new("RGB", (16, 16), fill)
        if patch:
            x0, y0, x1, y1, color = patch
            for x in range(x0, x1):
                for y in range(y0, y1):
                    img.putpixel((x, y), color)
        return img

    def test_gold_button_with_white_lock_is_locked(self):
        # Gold fill with a white lock patch in the middle.
        img = self.crop((180, 120, 60), patch=(6, 6, 10, 10, (255, 255, 255)))
        self.assertTrue(self.parser()._parse_relic_lock_state(img))

    def test_white_button_with_dark_lock_is_unlocked(self):
        img = self.crop((255, 255, 255), patch=(6, 6, 10, 10, (40, 40, 40)))
        self.assertFalse(self.parser()._parse_relic_lock_state(img))

    def test_ambiguous_gold_without_white_lock_is_not_locked(self):
        # Gold fill but no white pixels: fails white_ratio, must not flip lock.
        img = self.crop((180, 120, 60))
        self.assertFalse(self.parser()._parse_relic_lock_state(img))


if __name__ == "__main__":
    unittest.main()
