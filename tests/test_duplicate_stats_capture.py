import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from enums.log_level import LogLevel  # noqa: E402
from utils.duplicate_capture import (  # noqa: E402
    UnresolvedDuplicateCaptureError,
    recover_duplicate_capture,
)
from utils.scan_integrity import (  # noqa: E402
    ScanIntegrityError,
    validate_relic_records,
)


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

    def test_delayed_panel_update_is_recovered_by_wait(self) -> None:
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

    def test_exhausted_recovery_aborts_instead_of_accepting_stale_capture(self) -> None:
        screenshot = FakeScreenshot(
            [
                ({"id": "stale1"}, b"previous"),
                ({"id": "stale2"}, b"previous"),
                ({"id": "stale3"}, b"previous"),
            ]
        )
        logs = []
        sleeps = []
        with self.assertRaisesRegex(
            UnresolvedDuplicateCaptureError, "will not be exported"
        ):
            recover_duplicate_capture(
                screenshot.capture_stats,
                b"previous",
                4,
                lambda msg, level: logs.append((msg, level)),
                lambda seconds: sleeps.append(seconds),
                0.15,
            )

        self.assertEqual(screenshot.calls, 3)
        self.assertEqual(sleeps, [0.15, 0.15])
        self.assertIn(LogLevel.ERROR, [level for _, level in logs])
        self.assertIn("no export will be written", logs[-1][0])

    def test_failed_navigation_is_never_blindly_resent(self) -> None:
        actions = []
        captures = FakeScreenshot([({"id": "same-selection"}, b"previous")])

        with self.assertRaises(UnresolvedDuplicateCaptureError):
            recover_duplicate_capture(
                captures.capture_stats,
                b"previous",
                5,
                lambda _msg, _level: None,
                lambda seconds: actions.append(("wait", seconds)),
                0.15,
            )

        self.assertEqual(actions, [("wait", 0.15), ("wait", 0.15)])
        self.assertNotIn("navigate", [action[0] for action in actions])

    def test_basic_debug_callback_records_each_unchanged_attempt(self) -> None:
        attempts = []
        captures = FakeScreenshot([({"id": "stale"}, b"previous")])

        with self.assertRaises(UnresolvedDuplicateCaptureError):
            recover_duplicate_capture(
                captures.capture_stats,
                b"previous",
                6,
                lambda _msg, _level: None,
                lambda _seconds: None,
                0.15,
                lambda attempt, stats: attempts.append((attempt, stats["id"])),
            )

        self.assertEqual(attempts, [(0, "stale"), (1, "stale"), (2, "stale")])


class ScanIntegrityTest(unittest.TestCase):
    def test_legitimate_identical_unequipped_relics_are_preserved(self) -> None:
        relic = {
            "set_id": "101",
            "slot": "Head",
            "mainstat": "HP",
            "substats": [{"key": "SPD", "value": 2}],
            "location": "",
        }
        records = [dict(relic, _uid="relic_1"), dict(relic, _uid="relic_2")]

        result = validate_relic_records(records)

        self.assertIs(result, records)
        self.assertEqual([record["_uid"] for record in result], ["relic_1", "relic_2"])
        self.assertEqual(len(result), 2)

    def test_exact_duplicate_equipped_record_aborts(self) -> None:
        records = [
            {
                "_uid": "relic_51",
                "slot": "Head",
                "location": "1014",
                "mainstat": "HP",
            },
            {
                "_uid": "relic_52",
                "slot": "Head",
                "location": "1014",
                "mainstat": "HP",
            },
        ]

        with self.assertRaisesRegex(ScanIntegrityError, "relic_51.*relic_52"):
            validate_relic_records(records)

    def test_same_equipped_slot_with_different_stats_is_preserved(self) -> None:
        records = [
            {
                "_uid": "relic_1",
                "slot": "Body",
                "location": "1014",
                "mainstat": "CRIT Rate",
            },
            {
                "_uid": "relic_2",
                "slot": "Body",
                "location": "1014",
                "mainstat": "CRIT DMG",
            },
        ]

        self.assertIs(validate_relic_records(records), records)

    def test_valid_records_keep_item_order_and_count(self) -> None:
        records = [
            {"_uid": "relic_49", "slot": "Link Rope", "location": "1501"},
            {"_uid": "relic_50", "slot": "Body", "location": "1501"},
            {"_uid": "relic_51", "slot": "Head", "location": "1014"},
            {"_uid": "relic_52", "slot": "Hands", "location": "1014"},
        ]

        result = validate_relic_records(records)

        self.assertEqual(len(result), 4)
        self.assertEqual(
            [record["_uid"] for record in result],
            ["relic_49", "relic_50", "relic_51", "relic_52"],
        )


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
