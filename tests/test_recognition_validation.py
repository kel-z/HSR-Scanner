import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from utils.recognition_validation import validated_match, validate_main_stat_slot
from utils.avatar_matching import require_avatar_match, equipped_frame_present, split_icon_key
from utils.scan_integrity import ScanIntegrityError, validate_relic_records
from services.scanner.parsers.relic_strategy import RelicStrategy
from models.game_data import GameData, RELIC_MAIN_STATS


class ConfirmedOutfitPortraitTest(unittest.TestCase):
    def game_data(self):
        import base64
        import io
        buf = io.BytesIO()
        Image.fromarray(np.random.default_rng(9).integers(
            0, 255, (100, 100, 3), dtype=np.uint8)).save(buf, format='PNG')
        icon = base64.b64encode(buf.getvalue()).decode()
        response = Mock()
        response.json.return_value = {
            'version': 'fixture', 'relics': {}, 'light_cones': {},
            'characters': {}, 'mini_icons': {'1505': icon, '1409': icon},
        }
        with patch('models.game_data.requests.get', return_value=response):
            return GameData()

    def test_confirmed_outfits_resolve_to_canonical_characters(self):
        data = self.game_data()
        assets = Path(__file__).resolve().parents[1] / 'src/assets/images'
        for filename, character in (
            ('evanescia_lunar_blossoming_equipped_reference.png', '1505'),
            ('hyacine_warm_cotton_skies_equipped_reference.png', '1409'),
        ):
            with self.subTest(character=character), Image.open(assets / filename) as image:
                self.assertEqual(data.get_equipped_character(image, strict=True), (character, None))
                self.assertEqual(data.get_verified_equipped_character(
                    image, Image.new('RGB', image.size)), (character, None))
                self.assertIn(character, data.EQUIPPED_ICONS)  # original feed retained

    def test_reference_outfits_never_report_an_outfit_id(self):
        self.assertEqual(split_icon_key('1310#SPRING_MISSIVE'), ('1310', 'SPRING_MISSIVE'))
        self.assertEqual(split_icon_key('1505#reference:x.png'), ('1505', None))
        self.assertEqual(split_icon_key('1505'), ('1505', None))
        data = self.game_data()
        with Image.open(Path(__file__).resolve().parents[1]
                        / 'src/assets/images/hyacine_warm_cotton_skies_equipped_reference.png') as image:
            self.assertEqual(data.get_equipped_character(image), ('1409', None))

    def test_unknown_portrait_still_rejected_with_outfit_references(self):
        data = self.game_data()
        with self.assertRaises(ScanIntegrityError):
            data.get_verified_equipped_character(
                Image.new('RGB', (40, 40)), Image.new('RGB', (40, 40)))


class RecognitionValidationTest(unittest.TestCase):
    def test_main_stat_garbage_is_not_nearest_guessed(self):
        for text in ('', 'NV fi eYo COCOCXJ a', 'HF', 'AIH'):
            with self.subTest(text=text), self.assertRaises(ScanIntegrityError):
                validated_match(text, RELIC_MAIN_STATS, 'main stat')

    def test_exact_and_small_unambiguous_title_error(self):
        choices = ["Vonwacq's Island of Birth", "Vonwacq's Islandic Coast"]
        self.assertEqual(validated_match("Vonwacgq's Island of Birth", choices, 'relic name'), choices[0])
        with self.assertRaises(ScanIntegrityError):
            validated_match('unreadable title', choices, 'relic name')

    def test_tied_main_stat_is_rejected(self):
        with self.assertRaises(ScanIntegrityError):
            validated_match('abcdefgz', ['abcdefgx', 'abcdefgy'], 'main stat')

    def test_slot_gate_even_for_valid_stat_name(self):
        with self.assertRaises(ScanIntegrityError):
            validate_main_stat_slot('Fire DMG Boost', 'Feet')
        validate_main_stat_slot('Fire DMG Boost', 'Planar Sphere')

    def test_bad_level_and_flag_are_not_defaulted(self):
        parser = RelicStrategy.__new__(RelicStrategy)
        parser._log = Mock()
        self.assertIsNone(parser._parse_level_int('garbage15'))
        with self.assertRaises(ScanIntegrityError):
            parser._parse_icon_flag(1, 'lock', None, None)

    def test_generic_parser_exception_cannot_become_empty_record(self):
        parser = RelicStrategy.__new__(RelicStrategy)
        parser._interrupt_event = Mock()
        parser._interrupt_event.is_set.return_value = False
        parser._log = Mock()
        parser.extract_stats_data = Mock(side_effect=ValueError('OCR broke'))
        with self.assertRaises(ScanIntegrityError):
            parser.parse({'field': 'bad'}, 1)
        with self.assertRaises(ScanIntegrityError):
            validate_relic_records([{}])

    def test_avatar_interior_alignment_and_background_invariance(self):
        rng = np.random.default_rng(4)
        template = rng.integers(0, 255, (100,100,3), dtype=np.uint8)
        other = rng.integers(0, 255, (100,100,3), dtype=np.uint8)
        for background in ((0,0,0),(220,150,30),(30,120,220)):
            query = np.full((100,100,3), background, dtype=np.uint8)
            query[20:80,28:88] = template[20:80,20:80]
            self.assertEqual(require_avatar_match(Image.fromarray(query), {'correct':template,'other':other}), ('correct',None))

    def test_unknown_and_tied_avatars_fail_closed(self):
        rng = np.random.default_rng(2)
        template = rng.integers(0,255,(100,100,3),dtype=np.uint8)
        with self.assertRaises(ScanIntegrityError):
            require_avatar_match(Image.new('RGB',(100,100)), {'a':template})
        with self.assertRaises(ScanIntegrityError):
            require_avatar_match(Image.fromarray(template), {'a':template,'b':template})

    def test_equipped_footer_presence_and_uncertain_border(self):
        self.assertFalse(equipped_frame_present(Image.new('RGB',(480,68))))
        for value, valid in ((100,True),(30,False)):
            arr = np.zeros((68,480,3),dtype=np.uint8)
            arr[9,20:460] = value
            arr[44,20:460] = value
            if valid:
                self.assertTrue(equipped_frame_present(Image.fromarray(arr)))
            else:
                with self.assertRaises(ScanIntegrityError):
                    equipped_frame_present(Image.fromarray(arr))


if __name__ == '__main__':
    unittest.main()
