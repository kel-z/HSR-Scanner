import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from services.scanner.scanner import HSRScanner
from services.scanner.parsers.relic_strategy import RelicStrategy
from utils.screenshot import Screenshot
from utils.duplicate_capture import UnresolvedDuplicateCaptureError
from config.const import ASPECT_16_9
from models.const import CONFIG_INVENTORY_KEY, CONFIG_DEBUG, SORT_RARITY


class CapturePollingTest(unittest.TestCase):
    def test_basic_mode_saves_before_retry_and_exact_panel(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            screenshot = Screenshot.__new__(Screenshot)
            screenshot._debug = True
            screenshot._save_capture_png = False
            screenshot._verbose_logs = False
            screenshot._debug_output_location = folder
            screenshot._log_signal = Mock()
            screenshot._take_screenshot = Mock(return_value=Image.new("RGB", (20, 20)))
            screenshot._diagnostic_panel = Image.new("RGB", (10, 10))
            screenshot.remember_inventory_before_navigation()
            screenshot._take_screenshot.assert_not_called()
            self.assertIs(screenshot._inventory_before_navigation, screenshot._diagnostic_panel)
            screenshot.save_inventory_transition_diagnostic(52, 0)
            names = {path.name for path in Path(folder).glob("*.png")}
            self.assertEqual(names, {
                "inventory-transition-item-52-before-panel.png",
                "inventory-transition-item-52-attempt-0.png",
                "inventory-transition-item-52-attempt-0-exact-panel.png",
            })

    def poll(self, values, timeout=0.15, settle=0.035, debug=False, verbose=False, pipeline=False, interrupt_after_nav=False):
        screenshot = Screenshot.__new__(Screenshot)
        screenshot._aspect_ratio = ASPECT_16_9
        screenshot._window_width = 1920
        screenshot._window_height = 1080
        screenshot._window_x = screenshot._window_y = 0
        screenshot._x_scaling_factor = screenshot._y_scaling_factor = 1
        screenshot._debug = debug
        screenshot._save_capture_png = False
        screenshot._verbose_logs = verbose
        screenshot._stats_capture_records = []
        screenshot._nontext_change_events = []
        screenshot._last_panel_raw = Image.new("RGB", (480, 842), (1, 0, 0))
        screenshot._log_signal = Mock()
        clock = [0.0]
        calls = []

        def grab(_bbox):
            clock[0] += 0.01
            value = values[min(len(calls), len(values) - 1)]
            calls.append(value)
            return Image.new("RGB", (480, 842), (value, 0, 0)), "fake"

        screenshot._grab_screenshot = grab
        screenshot._panel_change_signature = lambda img, key: bytes([img.getpixel((0, 0))[0]])
        self.navigation_observations = []
        def advance(_raw, _key):
            self.navigation_observations.append(list(calls))
            return clock[0], clock[0]
        def interrupt():
            if interrupt_after_nav and self.navigation_observations:
                raise RuntimeError('test interruption')
        screenshot.configure_inventory_capture(2, advance if pipeline else None, interrupt)
        self.last_screenshot = screenshot
        with patch("utils.screenshot.time.perf_counter", side_effect=lambda: clock[0]):
            result = screenshot._screenshot_stats("relic", b"\x01", timeout, settle)
        self.last_screenshot = screenshot
        return result, calls

    def test_pipeline_sends_after_first_change_before_confirmation(self):
        (_, signature), calls = self.poll([1, 2, 2], settle=0, pipeline=True)
        self.assertEqual(signature, b'\x02')
        self.assertEqual(calls, [1, 2, 2])
        self.assertEqual(self.navigation_observations, [[1, 2]])

    def test_pipeline_delayed_elements_still_confirm(self):
        (_, signature), calls = self.poll([1, 2, 3, 3], settle=0, pipeline=True)
        self.assertEqual(signature, b'\x03')
        self.assertEqual(self.navigation_observations, [[1, 2]])
        self.assertIsNone(getattr(self.last_screenshot, '_pipeline_cache', None))

    def test_overlap_accepts_preceding_candidate_and_carries_next_owner(self):
        (_, signature), calls = self.poll([1, 2, 3, 4], settle=0, pipeline=True, debug=True)
        self.assertEqual(signature, b'\x03')
        screenshot = self.last_screenshot
        self.assertEqual(screenshot._pipeline_cache[0], 3)
        self.assertEqual(screenshot._pipeline_cache[4], b'\x04')
        screenshot.configure_inventory_capture(3)
        (_, next_signature) = screenshot._screenshot_stats('relic', signature, 0.15, 0)
        self.assertEqual(next_signature, b'\x04')
        self.assertIsNone(screenshot._pipeline_cache)
        self.assertEqual(calls, [1, 2, 3, 4, 4])
        self.assertTrue(any(row[-1] == 'unconfirmed_overlap' for row in screenshot._capture_trace))
        self.assertTrue(any(row[-2] == 'cache' for row in screenshot._capture_trace))

    def test_pipeline_profile_on_off_has_same_decisions(self):
        plain, calls = self.poll([1, 2, 3, 4], settle=0, pipeline=True)
        profiled, profile_calls = self.poll([1, 2, 3, 4], settle=0, pipeline=True, debug=True)
        self.assertEqual(plain[1], profiled[1])
        self.assertEqual(calls, profile_calls)

    def test_pipeline_failed_navigation_does_not_send(self):
        (_, signature), _ = self.poll([1], settle=0, pipeline=True)
        self.assertEqual(signature, b'\x01')
        self.assertEqual(self.navigation_observations, [])

    def test_pipeline_reversion_timeout_aborts_instead_of_recapturing_next(self):
        from utils.scan_integrity import ScanIntegrityError
        with self.assertRaisesRegex(ScanIntegrityError, 'ownership is unresolved'):
            self.poll([2, 1], settle=0, pipeline=True)
        self.assertEqual(self.navigation_observations, [[2]])

    def test_interrupt_after_navigation_keeps_trace(self):
        with self.assertRaisesRegex(RuntimeError, 'test interruption'):
            self.poll([2, 2], settle=0, pipeline=True, debug=True, interrupt_after_nav=True)
        events = [row[1] for row in self.last_screenshot._capture_trace]
        self.assertEqual(events, ['poll', 'nav', 'abort'])
        self.assertEqual(self.navigation_observations, [[2]])

    def test_overlap_evidence_is_deferred_until_flush(self):
        import tempfile
        import csv
        with patch.object(Image.Image, 'save') as save:
            self.poll([2, 3, 4], settle=0, pipeline=True, debug=True)
            save.assert_not_called()
        screenshot = self.last_screenshot
        with tempfile.TemporaryDirectory() as folder:
            screenshot._debug_output_location = folder
            path = screenshot.flush_inventory_capture_trace()
            self.assertTrue(Path(folder, 'overlap-2-unconfirmed.png').exists())
            self.assertTrue(Path(folder, 'overlap-2-following.png').exists())
            with open(path, newline='', encoding='utf-8') as stream:
                rows = list(csv.DictReader(stream))
            self.assertTrue(all(row['capture_id'] == '1' for row in rows))
            self.assertEqual(rows[-1]['decision'], 'unconfirmed_overlap')

    def test_capture_trace_is_bounded_and_reports_drops(self):
        self.poll([2, 2], settle=0, debug=True)
        screenshot = self.last_screenshot
        screenshot._capture_trace = [()] * 200000
        screenshot._trace_capture(('poll',))
        self.assertEqual(len(screenshot._capture_trace), 200000)
        self.assertEqual(screenshot._capture_trace_dropped, 1)

    def test_basic_mode_never_computes_full_panel_differences(self):
        with patch("utils.screenshot.ImageChops.difference", side_effect=AssertionError("hot-path diff")), \
             patch.object(Screenshot, "_record_nontext_change", side_effect=AssertionError("hot-path diff")):
            self.poll([1, 1, 2, 2], settle=0, debug=True)
        self.assertIsNone(self.last_screenshot._stats_capture_records[0]["accept_area"])
        self.assertTrue(any("disabled" in line for line in self.last_screenshot.get_capture_timing_summary_lines()))

    def test_verbose_mode_retains_nontext_diagnostics(self):
        with patch.object(Screenshot, "_record_nontext_change") as record:
            self.poll([1, 1, 2, 2], settle=0, debug=True, verbose=True)
        self.assertEqual(record.call_count, 2)

    def test_profile_does_not_add_grabs_or_change_result(self):
        values = [1, 1, 2, 3, 3]
        plain, plain_calls = self.poll(values, settle=0, debug=False)
        profiled, profile_calls = self.poll(values, settle=0, debug=True)
        self.assertEqual(plain[1], profiled[1])
        self.assertEqual(plain_calls, profile_calls)
        record = self.last_screenshot._stats_capture_records[0]
        self.assertAlmostEqual(record['all_grabs_ms'], 50)
        self.assertAlmostEqual(record['first_change_ms'], 30)
        self.assertAlmostEqual(record['confirmation_ms'], 20)
        self.assertEqual(record['signature_changes'], 2)
        self.last_screenshot._log_signal.emit.assert_not_called()
        self.assertTrue(any('all_grabs_ms' in line for line in self.last_screenshot.get_capture_timing_summary_lines()))

    def test_profile_unchanged_timeout_has_no_confirmation(self):
        self.poll([1], settle=0, debug=True)
        record = self.last_screenshot._stats_capture_records[0]
        self.assertFalse(record['first_change_seen'])
        self.assertEqual(record['confirmation_ms'], 0)

    def test_fast_path_only_needs_two_matching_observations(self):
        self.assertEqual(HSRScanner.PANEL_SETTLE_TIME, 0.0)
        (_, signature), calls = self.poll([2], settle=0.0)
        self.assertEqual(signature, b"\x02")
        self.assertEqual(calls, [2, 2])

    def test_fast_path_delayed_partial_update(self):
        (_, signature), calls = self.poll([1, 1, 2, 3, 3], settle=0.0)
        self.assertEqual(signature, b"\x03")
        self.assertEqual(calls, [1, 1, 2, 3, 3])

    def test_fast_path_return_to_previous_requires_new_confirmation(self):
        (_, signature), calls = self.poll([2, 1, 2, 3, 3], settle=0.0)
        self.assertEqual(signature, b"\x03")
        self.assertEqual(calls, [2, 1, 2, 3, 3])

    def test_fast_path_never_stable_or_unchanged_fails_closed(self):
        for values in ([1], [2, 3] * 20):
            with self.subTest(values=values):
                (_, signature), _ = self.poll(values, settle=0.0)
                self.assertEqual(signature, b"\x01")

    def test_art_only_changes_do_not_establish_freshness(self):
        before = Image.new("RGB", (480, 842))
        after = before.copy()
        after.paste((255, 0, 0), (240, 130, 400, 180))
        self.assertEqual(Screenshot._panel_change_signature(before, "relic"),
                         Screenshot._panel_change_signature(after, "relic"))

    def test_delayed_update_waits_for_stable_new_panel(self):
        (_, signature), calls = self.poll([1, 1, 2, 3, 3, 3, 3, 3])
        self.assertEqual(signature, b"\x03")
        self.assertGreaterEqual(calls.count(3), 5)

    def test_return_to_old_panel_resets_stability(self):
        (_, signature), calls = self.poll([2, 2, 1, 1, 2, 2, 2, 2, 2])
        self.assertEqual(signature, b"\x02")
        self.assertGreaterEqual(len(calls), 9)

    def test_never_settled_panel_is_rejected(self):
        (_, signature), _ = self.poll([2, 3] * 20)
        self.assertEqual(signature, b"\x01")

    def test_failed_navigation_or_identical_panel_is_unresolved(self):
        (_, signature), _ = self.poll([1])
        self.assertEqual(signature, b"\x01")


class InventoryLoopTest(unittest.TestCase):
    def scanner(self):
        scanner = HSRScanner.__new__(HSRScanner)
        HSRScanner.__bases__[0].__init__(scanner)
        scanner._aspect_ratio = ASPECT_16_9
        scanner._config = {CONFIG_INVENTORY_KEY: "b", CONFIG_DEBUG: False, "filters": {}}
        scanner._scan_mode = 0
        scanner._ocr_batch_size = 50
        scanner._ocr_concurrency = 12
        scanner._nav = Mock()
        scanner._screenshot = Mock()
        scanner._screenshot.get_capture_timing_summary_lines.return_value = []
        scanner._nav_sleep = Mock()
        scanner._scan_sleep = Mock()
        scanner._interruptible_sleep = Mock()
        scanner._profiled_parse_task = Mock(side_effect=lambda *args: args[-1])
        scanner._log = Mock()
        strategy = Mock(spec=RelicStrategy)
        from config.relic_scan import RELIC_NAV_DATA
        from enums.increment_type import IncrementType
        strategy.NAV_DATA = RELIC_NAV_DATA
        strategy.SCAN_TYPE = IncrementType.RELIC_ADD
        strategy.get_optimal_sort_method.return_value = SORT_RARITY
        strategy.check_filters.side_effect = lambda stats, filters, uid: ({}, stats)
        return scanner, strategy

    def test_batch_boundary_preserves_order_and_counts(self):
        scanner, strategy = self.scanner()
        scanner._capture_inventory_stats = Mock(side_effect=lambda strategy, uid, previous: ({"uid": uid}, str(uid).encode()))
        with patch("services.scanner.scanner.image_to_string", side_effect=["53/3000", SORT_RARITY]), patch("services.scanner.scanner.time.sleep"):
            shards = scanner.scan_inventory(strategy)
        self.assertEqual([uid for shard in shards for uid, stats in shard], list(range(1, 54)))
        self.assertEqual(sum(call.args == ("d",) for call in scanner._nav.key_tap.call_args_list), 52)
        self.assertEqual(len(shards[0]), 50)

    def test_profile_groups_batch_boundary_without_changing_navigation(self):
        scanner, strategy = self.scanner()
        scanner._config[CONFIG_DEBUG] = True
        scanner._screenshot.screenshot_stats_on_panel_change.side_effect = [
            ({"uid": uid}, str(uid).encode()) for uid in range(1, 54)
        ]
        with patch("services.scanner.scanner.image_to_string", side_effect=["53/3000", SORT_RARITY]), patch("services.scanner.scanner.time.sleep"):
            shards = scanner.scan_inventory(strategy)
        self.assertEqual([uid for shard in shards for uid, stats in shard], list(range(1, 54)))
        self.assertEqual([r[0] for r in scanner._inventory_profile if r[1] == 'after_shard_1_3'], [51, 52, 53])
        self.assertEqual(len(scanner._inventory_profile), 52)
        self.assertEqual(sum(call.args == ('d',) for call in scanner._nav.key_tap.call_args_list), 52)

    def test_exhaustion_does_not_queue_failed_uid_or_advance_again(self):
        scanner, strategy = self.scanner()
        scanner._screenshot.screenshot_stats_on_panel_change.side_effect = [({}, b"a"), ({}, b"a"), ({}, b"a"), ({}, b"a")]
        with patch("services.scanner.scanner.image_to_string", side_effect=["53/3000", SORT_RARITY]), patch("services.scanner.scanner.time.sleep"):
            with self.assertRaises(UnresolvedDuplicateCaptureError):
                scanner.scan_inventory(strategy)
        self.assertEqual(sum(call.args == ("d",) for call in scanner._nav.key_tap.call_args_list), 1)
        scanner._profiled_parse_task.assert_not_called()

    def test_start_scan_failure_cannot_return_export(self):
        import asyncio
        scanner, _ = self.scanner()
        scanner._is_en = True
        scanner._hwnd = 0
        scanner._ocr_capture_workers = 6
        scanner._run_capture_phases = Mock(side_effect=UnresolvedDuplicateCaptureError(52, 3))
        scanner._open_ocr_gate = Mock()
        order = []
        with patch("services.scanner.scanner.prepare_ocr", side_effect=lambda: order.append('preflight') or '5.4'), patch("services.scanner.scanner.bring_window_to_foreground", side_effect=lambda hwnd: order.append('focus')):
            with self.assertRaises(UnresolvedDuplicateCaptureError):
                asyncio.run(scanner.start_scan())
        self.assertEqual(order, ['preflight', 'focus'])
        scanner._open_ocr_gate.assert_called_once()
        scanner._screenshot.close.assert_called_once()
