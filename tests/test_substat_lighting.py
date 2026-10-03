import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from utils.ocr import preprocess_sub_stat_img


class SubstatLightingTest(unittest.TestCase):
    def test_neutral_active_and_dim_preview_strokes_survive_lighting(self):
        for background in ((20, 20, 20), (25, 75, 110), (80, 60, 35)):
            with self.subTest(background=background):
                rgb = np.full((40, 120, 3), background, dtype=np.uint8)
                rgb[8:25, 12:16] = (235, 235, 235)
                # Only 45 levels above the darkest channel of the warm background.
                rgb[8:25, 62:66] = (80, 80, 80)
                result = np.asarray(preprocess_sub_stat_img(Image.fromarray(rgb)))
                self.assertEqual(result.shape, (120, 360))
                self.assertEqual(result[45, 42], 0)
                self.assertEqual(result[45, 192], 0)
                self.assertEqual(result[45, 110], 255)

    def test_slow_coloured_gradient_without_text_stays_blank(self):
        ramp = np.linspace(15, 100, 120).astype(np.uint8)
        rgb = np.empty((40, 120, 3), dtype=np.uint8)
        rgb[:, :, 0] = ramp
        rgb[:, :, 1] = ramp + 40
        rgb[:, :, 2] = ramp + 100
        result = np.asarray(preprocess_sub_stat_img(Image.fromarray(rgb)))
        self.assertTrue(np.all(result == 255))

    def test_input_is_not_mutated_and_result_is_binary(self):
        img = Image.new("RGB", (75, 30), (30, 80, 150))
        before = img.tobytes()
        result = preprocess_sub_stat_img(img)
        self.assertEqual(img.tobytes(), before)
        self.assertEqual(result.mode, "L")
        self.assertLessEqual(set(result.tobytes()), {0, 255})


if __name__ == "__main__":
    unittest.main()
