import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from enums.log_level import LogLevel  # noqa: E402
from utils.duplicate_capture import recover_duplicate_capture  # noqa: E402


class FakeScreenshot:
    def __init__(self, captures: list[tuple[dict, bytes]]) -> None:
        self._captures = captures
        self.calls = 0

    def capture_stats(self) -> tuple[dict, bytes]:
        capture = self._captures[min(self.calls, len(self._captures) - 1)]
        self.calls += 1
        return capture


def recover(
    captures: list[tuple[dict, bytes]], previous_bytes: bytes | None, item_id: int
) -> tuple[tuple[dict, bytes], FakeScreenshot, list, list]:
    screenshot = FakeScreenshot(captures)
    logs = []
    sleeps = []
    result = recover_duplicate_capture(
        screenshot.capture_stats,
        previous_bytes,
        item_id,
        lambda msg, level: logs.append((msg, level)),
        lambda seconds: sleeps.append(seconds),
        0.15,
    )
    return result, screenshot, logs, sleeps


class DuplicateStatsCaptureTest(unittest.TestCase):
    def test_no_duplicate_captures_once(self) -> None:
        (stats, panel_bytes), screenshot, logs, sleeps = recover(
            [({"id": 1}, b"current")], b"previous", 1
        )

        self.assertEqual(stats, {"id": 1})
        self.assertEqual(panel_bytes, b"current")
        self.assertEqual(screenshot.calls, 1)
        self.assertEqual(logs, [])
        self.assertEqual(sleeps, [])

    def test_duplicate_fixed_by_wait(self) -> None:
        (stats, panel_bytes), screenshot, logs, sleeps = recover(
            [({"id": "stale"}, b"previous"), ({"id": "fresh"}, b"fresh")],
            b"previous",
            2,
        )

        self.assertEqual(stats, {"id": "fresh"})
        self.assertEqual(panel_bytes, b"fresh")
        self.assertEqual(screenshot.calls, 2)
        self.assertEqual(sleeps, [0.15])
        self.assertIn(LogLevel.WARNING, [level for _, level in logs])

    def test_duplicate_fixed_by_second_wait(self) -> None:
        (stats, panel_bytes), screenshot, logs, sleeps = recover(
            [
                ({"id": "stale1"}, b"previous"),
                ({"id": "stale2"}, b"previous"),
                ({"id": "fresh"}, b"fresh"),
            ],
            b"previous",
            3,
        )

        self.assertEqual(stats, {"id": "fresh"})
        self.assertEqual(panel_bytes, b"fresh")
        self.assertEqual(screenshot.calls, 3)
        self.assertEqual(sleeps, [0.15, 0.15])
        self.assertIn(LogLevel.WARNING, [level for _, level in logs])

    def test_persistent_duplicate_caps_retries_and_continues(self) -> None:
        (stats, panel_bytes), screenshot, logs, sleeps = recover(
            [
                ({"id": "stale1"}, b"previous"),
                ({"id": "stale2"}, b"previous"),
                ({"id": "stale3"}, b"previous"),
            ],
            b"previous",
            4,
        )

        self.assertEqual(stats, {"id": "stale3"})
        self.assertEqual(panel_bytes, b"previous")
        self.assertEqual(screenshot.calls, 3)
        self.assertEqual(sleeps, [0.15, 0.15])
        warning_logs = [msg for msg, level in logs if level == LogLevel.WARNING]
        self.assertEqual(len(warning_logs), 3)
        self.assertIn("persisted after retries", warning_logs[-1])


class DebugRunDuplicateCaptureTest(unittest.TestCase):
    def test_known_debug_run_duplicate_pair(self) -> None:
        debug_run = os.environ.get("HSR_DEBUG_RUN")
        if not debug_run:
            self.skipTest("Set HSR_DEBUG_RUN to validate captured debug screenshots.")

        folder = Path(debug_run)
        log_path = folder / "log.txt"
        if not log_path.exists():
            self.skipTest(f"Missing debug log: {log_path}")

        save_names = []
        for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = re.search(r"Saving (\d+\.png)", line)
            if match:
                save_names.append(match.group(1))

        from PIL import Image

        def raw_panel_bytes(index: int) -> bytes:
            with Image.open(folder / save_names[index]) as img:
                img.load()
                return img.tobytes()

        self.assertGreater(len(save_names), 48)
        # In this debug run, first saves are quantity/sort; item N maps to save_names[N + 1].
        relic_45 = raw_panel_bytes(46)
        relic_46 = raw_panel_bytes(47)
        relic_47 = raw_panel_bytes(48)

        self.assertEqual(relic_45, relic_46)
        self.assertNotEqual(relic_46, relic_47)

        (stats, panel_bytes), screenshot, logs, sleeps = recover(
            [({"id": "relic_46"}, relic_46), ({"id": "relic_47"}, relic_47)],
            relic_45,
            46,
        )

        self.assertEqual(stats, {"id": "relic_47"})
        self.assertEqual(panel_bytes, relic_47)
        self.assertEqual(screenshot.calls, 2)
        self.assertEqual(sleeps, [0.15])
        self.assertIn(LogLevel.WARNING, [level for _, level in logs])


if __name__ == "__main__":
    unittest.main()
