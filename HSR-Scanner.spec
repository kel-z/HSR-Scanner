# -*- mode: python ; coding: utf-8 -*-


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
    icon='src\\assets\\images\\app.ico'
)
