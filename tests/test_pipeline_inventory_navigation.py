"""Scanner-side ownership and stop-boundary regressions for early navigation."""
import unittest
from unittest.mock import Mock, patch

from PIL import Image
import test_inventory_capture_integration as fixtures
from models.const import (FILTERS, RELIC_FILTERS, MIN_RARITY, MIN_LEVEL,
                          CONFIG_SCAN_DELAY, CONFIG_RECENT_RELICS_NUM, SORT_DATE,
                          SORT_RARITY, SORT_LV)
from enums.scan_mode import ScanMode


class PipelineInventoryNavigationTest(unittest.TestCase):
    def test_real_capture_loop_and_navigation_preserve_53_frames(self):
        """Exercise the real poll/retry/scanner coupling, not a capture mock."""
        scanner, strategy = fixtures.InventoryLoopTest().scanner()
        helper = fixtures.CapturePollingTest()
        helper.poll([1], settle=0, debug=False)
        screenshot = helper.last_screenshot
        scanner._screenshot.configure_inventory_capture.side_effect = screenshot.configure_inventory_capture
        scanner._screenshot.screenshot_stats_on_panel_change.side_effect = screenshot.screenshot_stats_on_panel_change
        scanner._screenshot.reset_inventory_pipeline.side_effect = screenshot.reset_inventory_pipeline
        scanner._screenshot.remember_inventory_before_navigation.side_effect = screenshot.remember_inventory_before_navigation
        frame = [1]
        pending = [False]
        polls_since_d = [0]
        clock = [0.0]
        events = []
        def tap(key):
            if key == 'd':
                self.assertFalse(pending[0], 'second input before prior navigation arrived')
                pending[0] = True
                polls_since_d[0] = 0
                events.append(('d', frame[0] + 1))
        def grab(bbox):
            clock[0] += .009
            if pending[0]:
                polls_since_d[0] += 1
                if polls_since_d[0] == 2:
                    frame[0] += 1
                    pending[0] = False
            events.append(('grab', frame[0]))
            return Image.new('RGB', (480, 842), (frame[0], 0, 0)), 'fake'
        scanner._nav.key_tap.side_effect = tap
        screenshot._grab_screenshot = grab
        with patch('services.scanner.scanner.image_to_string', side_effect=['53/3000', SORT_RARITY]), \
             patch('services.scanner.scanner.time.sleep'), \
             patch('utils.screenshot.time.perf_counter', side_effect=lambda: clock[0]):
            shards = scanner.scan_inventory(strategy)
        items = [(uid, stats['name'].getpixel((0, 0))[0]) for shard in shards for uid, stats in shard]
        self.assertEqual(items, [(uid, uid) for uid in range(1, 54)])
        self.assertEqual(sum(kind == 'd' for kind, _ in events), 52)
        self.assertFalse(pending[0])

    def run_inventory(self, quantity=53, recent=None, level=0, scan_delay=0, rarities=None):
        scanner, strategy = fixtures.InventoryLoopTest().scanner()
        scanner._config[FILTERS] = {RELIC_FILTERS: {MIN_RARITY: 5, MIN_LEVEL: level}}
        scanner._config[CONFIG_SCAN_DELAY] = scan_delay
        scanner._game_data = Mock()
        scanner._game_data.get_closest_rarity.side_effect = lambda pixel: pixel[0]
        if recent is not None:
            scanner._scan_mode = ScanMode.RECENT_RELICS.value
            scanner._config[CONFIG_RECENT_RELICS_NUM] = recent
        sort = SORT_DATE if recent is not None else SORT_LV if level else SORT_RARITY
        strategy.get_optimal_sort_method.return_value = sort
        allowed = []
        def capture(_strategy, uid, previous):
            allowed.append((uid, scanner._pipeline_allowed))
            rarity = (rarities or {}).get(uid, 5)
            if uid > 1 and scanner._pipeline_allowed:
                scanner._advance_inventory_candidate(uid, Image.new('RGB', (480, 842), (rarity, 0, 0)), 'relic')
            return {'uid': uid, 'rarity': rarity, 'level': 15}, str(uid).encode()
        scanner._capture_inventory_stats = Mock(side_effect=capture)
        strategy.check_filters.side_effect = lambda stats, filters, uid: (
            {MIN_RARITY: stats['rarity'] >= 5, MIN_LEVEL: stats['level'] >= level}, stats)
        with patch('services.scanner.scanner.image_to_string', side_effect=[f'{quantity}/3000', sort]), \
             patch('services.scanner.scanner.time.sleep'):
            shards = scanner.scan_inventory(strategy)
        return scanner, shards, allowed

    def test_five_star_full_scan_pipelines_across_shard_and_never_double_taps(self):
        scanner, shards, allowed = self.run_inventory()
        self.assertTrue(all(enabled for uid, enabled in allowed[:-1]))
        self.assertFalse(allowed[-1][1])
        self.assertEqual([uid for shard in shards for uid, _ in shard], list(range(1, 54)))
        self.assertEqual(sum(call.args == ('d',) for call in scanner._nav.key_tap.call_args_list), 52)
        self.assertEqual(scanner._inventory_nav_target, 53)
        self.assertEqual(len(shards[0]), 50)

    def test_rarity_stop_candidate_does_not_send_next_d(self):
        scanner, shards, _ = self.run_inventory(quantity=6, rarities={4: 4})
        self.assertEqual([uid for shard in shards for uid, _ in shard], [1, 2, 3])
        self.assertEqual(scanner._inventory_nav_target, 4)
        self.assertEqual(sum(call.args == ('d',) for call in scanner._nav.key_tap.call_args_list), 3)

    def test_recent_count_and_filtered_item_do_not_cause_extra_navigation(self):
        scanner, shards, allowed = self.run_inventory(quantity=10, recent=3, rarities={2: 4})
        self.assertEqual([uid for shard in shards for uid, _ in shard], [1, 3, 4])
        self.assertEqual(allowed, [(1, True), (2, True), (3, True), (4, False)])
        self.assertEqual(scanner._inventory_nav_target, 4)
        self.assertEqual(sum(call.args == ('d',) for call in scanner._nav.key_tap.call_args_list), 3)

    def test_level_or_configured_delay_keeps_sequential_path(self):
        for options in ({'level': 3}, {'scan_delay': .1}):
            scanner, shards, allowed = self.run_inventory(quantity=3, **options)
            self.assertFalse(any(enabled for _, enabled in allowed))
            self.assertEqual(sum(call.args == ('d',) for call in scanner._nav.key_tap.call_args_list), 2)
            if 'scan_delay' in options:
                self.assertEqual(sum(call.args == (0,) for call in scanner._scan_sleep.call_args_list), 2)

    def test_zero_delay_never_calls_sleep_zero_after_navigation(self):
        scanner, _, _ = self.run_inventory(quantity=3)
        self.assertNotIn(((0,), {}), scanner._scan_sleep.call_args_list)


if __name__ == '__main__':
    unittest.main()
