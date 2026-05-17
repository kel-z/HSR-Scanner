import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils.ocr_threads import (  # noqa: E402
    clamp_thread_count,
    get_host_thread_count,
    percent_from_threads,
    threads_from_percent,
)


class OCRThreadHelpersTest(unittest.TestCase):
    def test_get_host_thread_count_falls_back_to_one(self) -> None:
        with patch("utils.ocr_threads.os.cpu_count", return_value=None):
            self.assertEqual(get_host_thread_count(), 1)

    def test_threads_from_default_percent_uses_ceil(self) -> None:
        expected = {
            1: 1,
            2: 2,
            4: 3,
            6: 5,
            8: 6,
            12: 9,
            16: 12,
            32: 24,
        }
        for host_threads, resolved_threads in expected.items():
            with self.subTest(host_threads=host_threads):
                self.assertEqual(threads_from_percent(75, host_threads), resolved_threads)

    def test_clamp_thread_count_limits_to_host_threads(self) -> None:
        self.assertEqual(clamp_thread_count(999, 8), 8)
        self.assertEqual(clamp_thread_count(0, 8), 1)
        self.assertEqual(clamp_thread_count(None, 8), 1)

    def test_slider_percent_converts_to_absolute_threads(self) -> None:
        self.assertEqual(threads_from_percent(50, 12), 6)
        self.assertEqual(threads_from_percent(51, 12), 7)
        self.assertEqual(threads_from_percent(100, 12), 12)

    def test_percent_from_threads_rounds_for_existing_settings(self) -> None:
        self.assertEqual(percent_from_threads(9, 12), 75)
        self.assertEqual(percent_from_threads(8, 12), 67)
        self.assertEqual(percent_from_threads(12, 12), 100)


if __name__ == "__main__":
    unittest.main()
