import sys
import types
import unittest
from asyncio import Event
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

pyautogui_stub = types.ModuleType("pyautogui")


class ImageNotFoundException(Exception):
    pass


pyautogui_stub.ImageNotFoundException = ImageNotFoundException
pyautogui_stub.locate = lambda *args, **kwargs: None
sys.modules.setdefault("pyautogui", pyautogui_stub)

from models.const import (  # noqa: E402
    RELIC_DISCARD,
    RELIC_LEVEL,
    RELIC_LOCATION,
    RELIC_MAINSTAT,
    RELIC_NAME,
    RELIC_PREVIEW_SUBSTATS,
    RELIC_RARITY,
    RELIC_SET,
    RELIC_SET_ID,
    RELIC_SLOT,
    RELIC_SUBSTAT_NAMES,
    RELIC_SUBSTAT_VALUES,
    RELIC_SUBSTATS,
)
from services.scanner.parsers.relic_strategy import RelicStrategy  # noqa: E402
from config.const import EQUIPPED, EQUIPPED_AVATAR, EQUIPPED_AVATAR_OFFSET, LOCK  # noqa: E402


class _DummySignal:
    def __init__(self) -> None:
        self.calls = []

    def emit(self, value) -> None:
        self.calls.append(value)


class _DummyGameData:
    def get_closest_relic_name(self, name: str) -> tuple[str, int]:
        return name, 0

    def get_closest_relic_main_stat(self, main_stat: str) -> tuple[str, int]:
        return main_stat, 0

    def get_closest_relic_sub_stat(self, sub_stat: str) -> tuple[str, int]:
        normalized = sub_stat.replace("%", "").strip()
        if normalized == "CRIT DMG":
            return "CRIT DMG_", 0
        return normalized, 0

    def get_relic_meta_data(self, _name: str) -> dict[str, str]:
        return {
            RELIC_SET_ID: "111",
            RELIC_SET: "Thief of Shooting Meteor",
            RELIC_SLOT: "Hands",
        }

    def get_equipped_character(self, _avatar) -> tuple[str, None]:
        return "", None


class RelicPreviewSubstatsTest(unittest.TestCase):
    def test_parse_exports_unactivated_substats_as_preview_substats(self) -> None:
        strategy = RelicStrategy.__new__(RelicStrategy)
        strategy._game_data = _DummyGameData()
        strategy._log_signal = _DummySignal()
        strategy._update_signal = _DummySignal()
        strategy._interrupt_event = Event()
        strategy._debug = False
        strategy._debug_output_location = None
        strategy._lock_icon = object()
        strategy._discard_icon = object()
        strategy._log = lambda *args, **kwargs: None
        strategy._parse_icon_flag = lambda uid, key, haystack, icon: bool(haystack)
        strategy._validate_substats = lambda *args, **kwargs: None

        stats_dict = {
            RELIC_NAME: "Thief of Shooting Meteor",
            RELIC_LEVEL: "0",
            RELIC_MAINSTAT: "ATK",
            LOCK: False,
            RELIC_DISCARD: False,
            RELIC_RARITY: 5,
            EQUIPPED: "",
            EQUIPPED_AVATAR: None,
            EQUIPPED_AVATAR_OFFSET: None,
            RELIC_SUBSTAT_NAMES: "ATK\nDEF\nCRIT DMG (+3 to activate)",
            RELIC_SUBSTAT_VALUES: "16\n16\n5.8%",
        }

        result = strategy.parse(stats_dict, 7)

        self.assertIn(RELIC_SUBSTATS, result)
        self.assertIn(RELIC_PREVIEW_SUBSTATS, result)
        self.assertNotIn("unactivated_substats", result)
        self.assertEqual(
            result[RELIC_PREVIEW_SUBSTATS],
            [{"key": "CRIT DMG_", "value": 5.8}],
        )
        self.assertEqual(result[RELIC_LOCATION], "")


if __name__ == "__main__":
    unittest.main()
