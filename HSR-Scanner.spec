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
    hiddenimports=['pywintypes'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['win32com', 'win32ui', 'pywin', 'tkinter', 'PIL._avif', 'PIL._imagingft', 'PIL._imagingtk'],
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

_DROP_BINARY_PARTS = (
    'opencv_videoio_ffmpeg',  # cv2 image ops only; video I/O is unused
    'PyQt6\\Qt6\\bin\\opengl32sw.dll',  # software OpenGL fallback; plain QtWidgets app
    'PyQt6\\Qt6\\bin\\Qt6Pdf.dll',
    'PyQt6\\Qt6\\bin\\Qt6Network.dll',
    'PyQt6\\Qt6\\bin\\Qt6Svg.dll',
    'PyQt6\\Qt6\\plugins\\imageformats\\qpdf.dll',
    'PyQt6\\Qt6\\plugins\\imageformats\\qsvg.dll',
    'PyQt6\\Qt6\\plugins\\iconengines\\qsvgicon.dll',
    'Pythonwin\\',  # win32ui/mfc140u only used by COM, which the app does not use
    'PIL\\_avif',
    'PIL\\_imagingft',
    'PIL\\_imagingtk',
    'tcl86t.dll',
    'tk86t.dll',
    '_tkinter.pyd',
    'tcl8\\',
)


def _drop(name):
    normalized = name.replace('/', '\\')
    return any(part in normalized for part in _DROP_BINARY_PARTS)


a.binaries = [entry for entry in a.binaries if not _drop(entry[0])]
a.datas = [
    entry for entry in a.datas
    if not _drop(entry[0]) and 'PyQt6\\Qt6\\translations\\' not in entry[0].replace('/', '\\')
]

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
