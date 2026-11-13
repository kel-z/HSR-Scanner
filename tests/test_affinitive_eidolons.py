import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config.const import (
    AFFINITIVE_EIDOLON_ACTIVATED,
    AFFINITIVE_EIDOLON_REGULAR,
    AFFINITIVE_EIDOLON_UNACTIVATED,
    AFFINITIVE_EIDOLON_UNKNOWN,
    ASPECT_16_9,
)
from models.const import (
    CHAR_AFFINITIVE_EIDOLONS,
    CHAR_ASCENSION,
    CHAR_LEVEL,
    CHAR_NAME,
    CHAR_PATH,
    CHAR_TRACES,
    EIDOLON_IMAGES,
    TRACES_LEVELS,
    TRACES_UNLOCKS,
)
from services.scanner.parsers.character_parser import CharacterParser
from utils.screenshot import Screenshot


class AffinitiveEidolonFormatTest(unittest.TestCase):
    def parser(self):
        parser = CharacterParser.__new__(CharacterParser)
        parser._interrupt_event = Mock()
        parser._interrupt_event.is_set.return_value = False
        parser._game_data = Mock()
        parser._game_data.get_character_meta_data.return_value = {
            "id": 1308,
            "e3": {},
            "e5": {},
        }
        parser._process_eidolons = Mock(return_value=0)
        parser.get_level = Mock(return_value=80)
        parser._update_signal = Mock()
        parser._log = Mock()
        return parser

    def stats(self, affinitive=None):
        stats = {
            CHAR_NAME: "Acheron",
            CHAR_PATH: "Nihility",
            CHAR_ASCENSION: 6,
            EIDOLON_IMAGES: [],
            CHAR_LEVEL: 80,
            CHAR_TRACES: {TRACES_LEVELS: {}, TRACES_UNLOCKS: {}},
        }
        if affinitive is not None:
            stats[CHAR_AFFINITIVE_EIDOLONS] = affinitive
        return stats

    def test_parser_exports_activated_id(self):
        result = self.parser().parse(self.stats([130801]))
        self.assertEqual(result[CHAR_AFFINITIVE_EIDOLONS], [130801])

    def test_parser_exports_empty_list_when_not_activated(self):
        result = self.parser().parse(self.stats([]))
        self.assertEqual(result[CHAR_AFFINITIVE_EIDOLONS], [])

    def test_parser_omits_field_for_characters_without_an_ae(self):
        result = self.parser().parse(self.stats())
        self.assertNotIn(CHAR_AFFINITIVE_EIDOLONS, result)


class AffinitiveEidolonScreenTest(unittest.TestCase):
    def screenshot(self):
        screenshot = Screenshot.__new__(Screenshot)
        screenshot._aspect_ratio = ASPECT_16_9
        return screenshot

    def screen(self):
        return Image.new("RGB", (1920, 1080), (20, 20, 20))

    def state(self, text):
        with patch("utils.screenshot.image_to_string", return_value=text):
            return self.screenshot().affinitive_eidolon_screen_state(self.screen())

    def test_activated_ae_details(self):
        self.assertEqual(
            self.state("SwitchtoOriginalEidolon Screen"),
            AFFINITIVE_EIDOLON_ACTIVATED,
        )

    def test_unactivated_ae_details(self):
        self.assertEqual(
            self.state("Scroll Back"), AFFINITIVE_EIDOLON_UNACTIVATED
        )

    def test_regular_six_node_layout(self):
        self.assertEqual(self.state("Select Back"), AFFINITIVE_EIDOLON_REGULAR)

    def test_unreadable_layout_is_unknown(self):
        self.assertEqual(self.state(""), AFFINITIVE_EIDOLON_UNKNOWN)

    def test_activated_badge_text(self):
        with patch("utils.screenshot.image_to_string", return_value="Activated"):
            self.assertTrue(
                self.screenshot().affinitive_eidolon_activated(self.screen())
            )

    def test_not_activated_badge_text(self):
        for text in ("Not Activated", ""):
            with self.subTest(text=text), patch(
                "utils.screenshot.image_to_string", return_value=text
            ):
                self.assertFalse(
                    self.screenshot().affinitive_eidolon_activated(self.screen())
                )


if __name__ == "__main__":
    unittest.main()
