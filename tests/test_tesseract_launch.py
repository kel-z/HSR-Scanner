import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils import patched_pytesseract as tess
from utils.ocr import prepare_ocr


@unittest.skipUnless(sys.platform == "win32", "Windows subprocess flags")
class TesseractLaunchTest(unittest.TestCase):
    def assert_hidden(self, kwargs):
        self.assertTrue(kwargs['creationflags'] & subprocess.CREATE_NO_WINDOW)
        self.assertTrue(kwargs['creationflags'] & subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        self.assertEqual(kwargs['startupinfo'].wShowWindow, subprocess.SW_HIDE)
        self.assertEqual(kwargs['stderr'], subprocess.PIPE)
        self.assertNotIn('shell', kwargs)

    def test_recognition_launch_hidden(self):
        process = Mock(returncode=0)
        process.communicate.return_value = (b'', b'')
        with patch.object(tess.subprocess, 'Popen', return_value=process) as launch:
            tess.run_tesseract('input.png', 'output', 'txt', 'eng')
        self.assert_hidden(launch.call_args.kwargs)

    def test_version_probe_hidden_and_bounded(self):
        with patch.object(tess.subprocess, 'check_output', return_value=b'tesseract 5.4.0\n') as launch:
            self.assertEqual(str(tess.get_tesseract_version.__wrapped__()), '5.4.0')
        self.assert_hidden(launch.call_args.kwargs)
        self.assertEqual(launch.call_args.kwargs['timeout'], 10)
        self.assertNotIn('stdout', launch.call_args.kwargs)

    def test_language_probe_hidden(self):
        with patch.object(tess.subprocess, 'run', return_value=Mock(returncode=0, stdout=b'eng\n')) as launch:
            self.assertEqual(tess.get_languages.__wrapped__(), ['eng'])
        self.assert_hidden(launch.call_args.kwargs)

    def test_preflight_populates_cache_before_first_tsv(self):
        with patch.object(tess.get_tesseract_version, '_result', tess.get_tesseract_version), \
             patch.object(tess.subprocess, 'check_output', return_value=b'tesseract 5.4.0\n') as probe, \
             patch.object(tess, 'run_and_get_output', return_value=''):
            self.assertEqual(prepare_ocr(), '5.4.0')
            tess.image_to_data('fake.png')
            tess.image_to_data('fake.png')
            probe.assert_called_once()

    def test_preflight_failure_propagates(self):
        with patch.object(tess, 'get_tesseract_version', side_effect=RuntimeError('failed')):
            with self.assertRaisesRegex(RuntimeError, 'failed'):
                prepare_ocr()
