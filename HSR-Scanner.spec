# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Stop PyInstaller bundling stray DLLs from other apps on PATH (e.g. Poppler's ICU).
python_root = Path(sys.executable).parent
windows_root = Path(os.environ['SystemRoot'])
os.environ['PATH'] = os.pathsep.join(str(path) for path in (
    python_root, python_root / 'DLLs', windows_root / 'System32', windows_root,
))


block_cipher = None


a = Analysis(
    ['src\\main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
a.datas += [('vgamepad\\win\\vigem\\client\\x64\\ViGEmClient.dll', 'src\\assets\\vgamepad\\ViGEmClient.dll', 'BINARY')]
a.datas += [('assets\\tesseract\\tesseract.exe', 'src\\assets\\tesseract\\tesseract.exe', 'BINARY')]
a.datas += [('assets\\tesseract\\tessdata\\DIN-Alternate.traineddata','src\\assets\\tesseract\\tessdata\\DIN-Alternate.traineddata', "DATA")]
a.datas += [('assets\\images\\databank.png','src\\assets\\images\\databank.png', "DATA")]
a.datas += [('assets\\images\\lock.png','src\\assets\\images\\lock.png', "DATA")]
a.datas += [('assets\\images\\discard.png','src\\assets\\images\\discard.png', "DATA")]
a.datas += [('assets\\images\\trailblazerm.png','src\\assets\\images\\trailblazerm.png', "DATA")]
a.datas += [('assets\\images\\trailblazerf.png','src\\assets\\images\\trailblazerf.png', "DATA")]
a.datas += [('assets\\images\\app.ico','src\\assets\\images\\app.ico', "DATA")]
a.datas += [('assets\\images\\sparxie_equipped_reference.png','src\\assets\\images\\sparxie_equipped_reference.png', "DATA")]
a.datas += [('assets\\images\\evanescia_lunar_blossoming_equipped_reference.png','src\\assets\\images\\evanescia_lunar_blossoming_equipped_reference.png', "DATA")]
a.datas += [('assets\\images\\hyacine_warm_cotton_skies_equipped_reference.png','src\\assets\\images\\hyacine_warm_cotton_skies_equipped_reference.png', "DATA")]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='HSR-Scanner',
    exclude_binaries=False,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    version='version_info.txt',
    icon='src\\assets\\images\\app.ico'
)
