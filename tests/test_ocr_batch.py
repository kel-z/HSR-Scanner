import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils.ocr_batch import _compose_vertical_batch, batch_image_to_strings


def tsv_row(text, top, height, left, block, line):
    return {
        "text": text,
        "top": str(top),
        "height": str(height),
        "left": str(left),
        "block_num": str(block),
        "par_num": "1",
        "line_num": str(line),
    }


class BatchOcrMappingTest(unittest.TestCase):
    def test_words_map_to_their_own_crop_and_padding_is_dropped(self):
        first = Image.new("RGB", (40, 20), "white")
        second = Image.new("RGB", (40, 30), "white")
        _, bounds = _compose_vertical_batch([first, second], padding=10)
        self.assertEqual(bounds, [(10, 30), (40, 70)])

        rows = [
            tsv_row("A1", 12, 8, 5, 1, 1),
            tsv_row("B2", 52, 8, 5, 2, 2),
            tsv_row("B1", 42, 8, 5, 2, 1),
            # Centre at y=34, inside the padding between the two crops.
            tsv_row("PAD", 32, 4, 0, 9, 1),
        ]
        with patch("utils.ocr_batch._run_tesseract_tsv", return_value=rows):
            texts, profile = batch_image_to_strings(
                [first, second],
                "0123456789",
                6,
                force_preprocess=False,
                remove_newline=True,
                padding=10,
            )

        self.assertEqual(texts, ["A1", "B1 B2"])
        self.assertEqual(profile.image_count, 2)
        self.assertEqual(profile.composite_size[0], 40)


if __name__ == "__main__":
    unittest.main()
