import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

from pynput.keyboard import Key

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from models.const import CONFIG_DEBUG, CONFIG_INVENTORY_KEY
from services.scanner.scanner import HSRScanner


class OpenInventoryTest(unittest.TestCase):
    """_open_inventory confirms the screen before pressing ESC/B."""

    def _scanner(self, inventory_states, esc_menu_states):
        scanner = HSRScanner.__new__(HSRScanner)
        HSRScanner.__bases__[0].__init__(scanner)  # QObject init for log_signal
        scanner._nav = Mock()
        scanner._nav_sleep = Mock()
        scanner._screenshot = Mock()
        scanner._config = {CONFIG_INVENTORY_KEY: "b", CONFIG_DEBUG: False}
        scanner._screenshot.inventory_open.side_effect = inventory_states
        scanner._screenshot.escape_menu_open.side_effect = esc_menu_states
        return scanner

    def test_already_open_sends_no_keys(self):
        scanner = self._scanner([True], [])
        scanner._open_inventory()
        scanner._nav.key_tap.assert_not_called()

    def test_escape_menu_closes_before_inventory_key(self):
        # Attempt 0: ESC menu -> ESC, wait for close, B, poll sees it open.
        scanner = self._scanner([False, True], [True, False])
        scanner._open_inventory()
        scanner._nav.key_tap.assert_any_call(Key.esc)
        scanner._nav.key_tap.assert_any_call("b")

    def test_overworld_goes_straight_to_inventory_key(self):
        # Attempt 0: no menu -> B only; the poll then sees it open.
        scanner = self._scanner([False, True], [False])
        scanner._open_inventory()
        scanner._nav.key_tap.assert_called_once_with("b")

    def test_unrecognized_screen_fails_loudly(self):
        # 4 attempts x 8 poll checks, all unreadable.
        scanner = self._scanner([False] * 40, [False] * 4)
        with self.assertRaises(ValueError):
            scanner._open_inventory()


if __name__ == "__main__":
    unittest.main()
