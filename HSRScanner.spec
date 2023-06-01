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
a.datas += [('tesseract\\tesseract.exe', 'src\\tesseract\\tesseract.exe', 'BINARY')]
a.datas += [('tesseract\\tessdata\\eng.traineddata','src\\tesseract\\tessdata\\eng.traineddata', "DATA")]
a.datas += [('images\\lock.png','src\\images\\lock.png', "DATA")]
a.datas += [('images\\lock2.png','src\\images\\lock2.png', "DATA")]
a.datas += [('images\\trailblazerm.png','src\\images\\trailblazerm.png', "DATA")]
a.datas += [('images\\trailblazerf.png','src\\images\\trailblazerf.png', "DATA")]
a.datas += [('images\\app.ico','src\\images\\app.ico', "DATA")]
a.datas += [('images\\avatars\\Arlan.png','src\\images\\avatars\\Arlan.png', "DATA")]
a.datas += [('images\\avatars\\Asta.png','src\\images\\avatars\\Asta.png', "DATA")]
a.datas += [('images\\avatars\\Bailu.png','src\\images\\avatars\\Bailu.png', "DATA")]
a.datas += [('images\\avatars\\Bronya.png','src\\images\\avatars\\Bronya.png', "DATA")]
a.datas += [('images\\avatars\\Clara.png','src\\images\\avatars\\Clara.png', "DATA")]
a.datas += [('images\\avatars\\DanHeng.png','src\\images\\avatars\\DanHeng.png', "DATA")]
a.datas += [('images\\avatars\\Gepard.png','src\\images\\avatars\\Gepard.png', "DATA")]
a.datas += [('images\\avatars\\Herta.png','src\\images\\avatars\\Herta.png', "DATA")]
a.datas += [('images\\avatars\\Himeko.png','src\\images\\avatars\\Himeko.png', "DATA")]
a.datas += [('images\\avatars\\Hook.png','src\\images\\avatars\\Hook.png', "DATA")]
a.datas += [('images\\avatars\\JingYuan.png','src\\images\\avatars\\JingYuan.png', "DATA")]
a.datas += [('images\\avatars\\March7th.png','src\\images\\avatars\\March7th.png', "DATA")]
a.datas += [('images\\avatars\\Natasha.png','src\\images\\avatars\\Natasha.png', "DATA")]
a.datas += [('images\\avatars\\Pela.png','src\\images\\avatars\\Pela.png', "DATA")]
a.datas += [('images\\avatars\\TrailblazerDestruction#M.png','src\\images\\avatars\\TrailblazerDestruction#M.png', "DATA")]
a.datas += [('images\\avatars\\TrailblazerPreservation#M.png','src\\images\\avatars\\TrailblazerPreservation#M.png', "DATA")]
a.datas += [('images\\avatars\\TrailblazerDestruction#F.png','src\\images\\avatars\\TrailblazerDestruction#F.png', "DATA")]
a.datas += [('images\\avatars\\Trailblazerpreservation#F.png','src\\images\\avatars\\TrailblazerPreservation#F.png', "DATA")]
a.datas += [('images\\avatars\\Qingque.png','src\\images\\avatars\\Qingque.png', "DATA")]
a.datas += [('images\\avatars\\Sampo.png','src\\images\\avatars\\Sampo.png', "DATA")]
a.datas += [('images\\avatars\\Seele.png','src\\images\\avatars\\Seele.png', "DATA")]
a.datas += [('images\\avatars\\Serval.png','src\\images\\avatars\\Serval.png', "DATA")]
a.datas += [('images\\avatars\\Sushang.png','src\\images\\avatars\\Sushang.png', "DATA")]
a.datas += [('images\\avatars\\Tingyun.png','src\\images\\avatars\\Tingyun.png', "DATA")]
a.datas += [('images\\avatars\\Welt.png','src\\images\\avatars\\Welt.png', "DATA")]
a.datas += [('images\\avatars\\Yanqing.png','src\\images\\avatars\\Yanqing.png', "DATA")]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='HSRScanner',
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
    icon='src\\images\\app.ico'
)
