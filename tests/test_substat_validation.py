import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from utils.substat_validation import validate_substat_rolls
from utils.scan_integrity import ScanIntegrityError
from services.scanner.parsers.relic_strategy import RelicStrategy


def stat(key, value):
    return {'key': key, 'value': value}


class SubstatValidationTest(unittest.TestCase):
    def base(self):
        return [stat('ATK_', 3.8), stat('Effect RES_', 3.4), stat('Break Effect_', 5.8)]

    def test_level_zero_valid_preview_and_active_unchanged(self):
        active, preview = self.base(), [stat('SPD', 2)]
        validate_substat_rolls(active, preview, 5, 0, 125)
        self.assertEqual(preview, [stat('SPD', 2)])

    def test_invalid_preview_zero_and_impossible_single_roll(self):
        for value in (0, -1, 11, float('nan'), float('inf'), True):
            with self.subTest(value=value), self.assertRaises(ScanIntegrityError):
                validate_substat_rolls(self.base(), [stat('SPD', value)], 5, 0, 125)

    def test_exact_table_rejects_value_inside_broad_bounds(self):
        with self.assertRaises(ScanIntegrityError):
            validate_substat_rolls([stat('ATK', 27), stat('SPD', 2), stat('HP', 33)], [], 5, 0, 1)

    def test_too_many_rolls_for_level(self):
        with self.assertRaises(ScanIntegrityError):
            validate_substat_rolls([stat('SPD', 11), *self.base()], [], 5, 0, 1)

    def test_too_few_rolls_at_max_level(self):
        with self.assertRaises(ScanIntegrityError):
            validate_substat_rolls([stat('SPD', 2), *self.base()], [], 5, 15, 1)

    def test_known_high_level_rounded_spd_is_feasible(self):
        validate_substat_rolls([stat('ATK_', 3.4), stat('SPD', 11),
                               stat('CRIT Rate_', 6.1), stat('Effect RES_', 3.8)], [], 5, 15, 51)

    def test_count_changes_at_upgrade_boundary(self):
        validate_substat_rolls(self.base(), [], 5, 2, 1)
        with self.assertRaises(ScanIntegrityError):
            validate_substat_rolls(self.base(), [], 5, 3, 1)
        validate_substat_rolls([*self.base(), stat('SPD', 2)], [], 5, 3, 1)

    def test_duplicates_including_preview_and_excess_preview(self):
        for preview in ([stat('ATK_', 3.8)], [stat('SPD', 2), stat('HP', 33)]):
            with self.assertRaises(ScanIntegrityError):
                validate_substat_rolls(self.base(), preview, 5, 0, 1)

    def test_different_rarity_uses_its_own_table(self):
        validate_substat_rolls([stat('HP', 20)], [], 3, 0, 1)
        with self.assertRaises(ScanIntegrityError):
            validate_substat_rolls([stat('HP', 33)], [], 3, 0, 1)

    def test_fractional_integer_ocr_is_not_truncated(self):
        parser = RelicStrategy.__new__(RelicStrategy)
        parser._log = Mock()
        parser._game_data = Mock()
        parser._game_data.get_closest_relic_sub_stat.return_value = ('SPD', 0)
        with self.assertRaisesRegex(ScanIntegrityError, 'invalid integer'):
            parser._parse_substats(['SPD (+3 to activate)'], ['.2'], 125)

    def test_parse_propagates_failure_instead_of_returning_empty_record(self):
        parser = RelicStrategy.__new__(RelicStrategy)
        parser._interrupt_event = Mock()
        parser._interrupt_event.is_set.return_value = False
        parser._log = Mock()
        parser.extract_stats_data = Mock(side_effect=ScanIntegrityError('incomplete'))
        with self.assertRaises(ScanIntegrityError):
            parser.parse({'test': 'value'}, 1)


if __name__ == '__main__':
    unittest.main()
