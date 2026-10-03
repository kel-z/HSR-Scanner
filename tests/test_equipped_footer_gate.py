import sys
import unittest
import threading
from pathlib import Path
from unittest.mock import Mock, patch
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from services.scanner.parsers.relic_strategy import RelicStrategy
from utils.scan_integrity import ScanIntegrityError


class EquippedFooterGateTest(unittest.TestCase):
    def parser(self):
        s=RelicStrategy.__new__(RelicStrategy)
        s._interrupt_event=threading.Event()
        s._debug=False
        s._log=Mock()
        s._update_signal=Mock()
        s._lock_icon=s._discard_icon=None
        s._parse_icon_flag=Mock(return_value=False)
        s._game_data=Mock()
        s._game_data.RELIC_META_DATA={'Example Hat':{}}
        s._game_data.get_relic_meta_data.return_value={'set_id':'1','set':'Example','slot':'Head'}
        s._game_data.get_verified_equipped_character.return_value=('8010',None)
        s.extract_stats_data=lambda k,v:v
        return s

    def row(self,label):
        image=Image.new('RGB',(40,40))
        return dict(name='Example Hat',level='0',mainstat='HP',rarity=5,lock=image,discard=image,
                    equipped=label,equipped_avatar=image,equipped_avatar_trailblazer=image,
                    _equipped_frame=image,substat_names='ATK\nEffect RES\nBreak Effect',
                    substat_vals='3.8%\n3.4%\n5.8%')

    def test_noisy_or_blank_label_requires_verified_frame_and_portrait(self):
        for label in ('pEquippe','', 'Equipped'):
            s=self.parser()
            with patch('services.scanner.parsers.relic_strategy.equipped_frame_present',return_value=True):
                self.assertEqual(s.parse(self.row(label),1)['location'],'8010')
            s._game_data.get_verified_equipped_character.assert_called_once()

    def test_unknown_portrait_still_blocks_export(self):
        s=self.parser()
        s._game_data.get_verified_equipped_character.side_effect=ScanIntegrityError('unknown')
        with patch('services.scanner.parsers.relic_strategy.equipped_frame_present',return_value=True):
            with self.assertRaises(ScanIntegrityError):s.parse(self.row('pEquippe'),1)

    def test_label_frame_conflict_still_rejected(self):
        s=self.parser()
        with patch('services.scanner.parsers.relic_strategy.equipped_frame_present',return_value=False):
            with self.assertRaises(ScanIntegrityError):s.parse(self.row('Equipped'),1)

    def test_cached_field_retry_is_bounded_and_does_not_change_uid(self):
        s=self.parser()
        image=Image.new('RGB',(20,20))
        row={'name':'bad','_raw_stats':{'name':image}}
        s._parse_once=Mock(side_effect=[ScanIntegrityError('Uncertain relic name'),{'_uid':'relic_8'}])
        s.extract_stats_data=Mock(return_value='Example Hat')
        self.assertEqual(s.parse(row,8),{'_uid':'relic_8'})
        self.assertEqual(s._parse_once.call_count,2)
        self.assertEqual(s._parse_once.call_args.args[1],8)
        s.extract_stats_data.assert_called_once_with('name',image)
        s._parse_once=Mock(side_effect=ScanIntegrityError('Uncertain relic name'))
        with self.assertRaises(ScanIntegrityError):s.parse(row,8)
        self.assertEqual(s._parse_once.call_count,2)


class CachedRetryChainTest(unittest.TestCase):
    """A re-read name can expose a substat misread the first parse never reached."""

    def setUp(self):
        self.s=EquippedFooterGateTest.parser(None)
        self.image=Image.new('RGB',(20,20))
        self.row={'name':'bad','substat_names':'SPD (+3 to activa','substat_vals':'.2',
                  '_raw_stats':{k:self.image for k in ('name','substat_names','substat_vals')}}
        self.s.extract_stats_data=Mock(side_effect=lambda k,v:{'name':'Example Hat','substat_names':'SPD (+3 to activa','substat_vals':'2'}[k])

    def test_later_field_group_gets_its_own_reread(self):
        self.s._parse_once=Mock(side_effect=[ScanIntegrityError('Uncertain relic name'),
                                             ScanIntegrityError("Relic 9: invalid integer substat SPD='.2'"),
                                             {'_uid':'relic_9'}])
        self.assertEqual(self.s.parse(self.row,9),{'_uid':'relic_9'})
        last=self.s._parse_once.call_args.args[0]
        self.assertEqual((last['name'],last['substat_vals']),('Example Hat','2'))
        self.assertEqual([c.args[0] for c in self.s.extract_stats_data.call_args_list],
                         ['name','substat_names','substat_vals'])

    def test_group_is_never_reread_twice(self):
        self.s._parse_once=Mock(side_effect=[ScanIntegrityError('Uncertain relic name'),
                                             ScanIntegrityError('invalid integer substat'),
                                             ScanIntegrityError('Uncertain relic name')])
        with self.assertRaisesRegex(ScanIntegrityError,'relic name'):self.s.parse(self.row,9)
        self.assertEqual(self.s._parse_once.call_count,3)
