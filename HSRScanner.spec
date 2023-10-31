# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['main.py'],
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
a.datas += [('assets\\tesseract\\tesseract.exe', 'src\\assets\\tesseract\\tesseract.exe', 'BINARY')]
a.datas += [('assets\\tesseract\\tessdata\\eng.traineddata','src\\assets\\tesseract\\tessdata\\eng.traineddata', "DATA")]
a.datas += [('assets\\images\\databank.png','src\\assets\\images\\databank.png', "DATA")]
a.datas += [('assets\\images\\lock.png','src\\assets\\images\\lock.png', "DATA")]
a.datas += [('assets\\images\\trailblazerm.png','src\\assets\\images\\trailblazerm.png', "DATA")]
a.datas += [('assets\\images\\trailblazerf.png','src\\assets\\images\\trailblazerf.png', "DATA")]
a.datas += [('assets\\images\\app.ico','src\\assets\\images\\app.ico', "DATA")]
a.datas += [('assets\\images\\avatars\\Arlan.png','src\\assets\\images\\avatars\\Arlan.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Asta.png','src\\assets\\images\\avatars\\Asta.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Bailu.png','src\\assets\\images\\avatars\\Bailu.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Blade.png','src\\assets\\images\\avatars\\Blade.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Bronya.png','src\\assets\\images\\avatars\\Bronya.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Clara.png','src\\assets\\images\\avatars\\Clara.png', "DATA")]
a.datas += [('assets\\images\\avatars\\DanHeng.png','src\\assets\\images\\avatars\\DanHeng.png', "DATA")]
a.datas += [('assets\\images\\avatars\\FuXuan.png','src\\assets\\images\\avatars\\FuXuan.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Gepard.png','src\\assets\\images\\avatars\\Gepard.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Guinaifen.png','src\\assets\\images\\avatars\\Guinaifen.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Herta.png','src\\assets\\images\\avatars\\Herta.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Himeko.png','src\\assets\\images\\avatars\\Himeko.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Hook.png','src\\assets\\images\\avatars\\Hook.png', "DATA")]
a.datas += [('assets\\images\\avatars\\ImbibitorLunae#DanHengImbibitorLunae.png','src\\assets\\images\\avatars\\ImbibitorLunae#DanHengImbibitorLunae.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Jingliu.png','src\\assets\\images\\avatars\\Jingliu.png', "DATA")]
a.datas += [('assets\\images\\avatars\\JingYuan.png','src\\assets\\images\\avatars\\JingYuan.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Kafka.png','src\\assets\\images\\avatars\\Kafka.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Luka.png','src\\assets\\images\\avatars\\Luka.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Luocha.png','src\\assets\\images\\avatars\\Luocha.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Lynx.png','src\\assets\\images\\avatars\\Lynx.png', "DATA")]
a.datas += [('assets\\images\\avatars\\March7th.png','src\\assets\\images\\avatars\\March7th.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Natasha.png','src\\assets\\images\\avatars\\Natasha.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Pela.png','src\\assets\\images\\avatars\\Pela.png', "DATA")]
a.datas += [('assets\\images\\avatars\\TopazandNumby.png','src\\assets\\images\\avatars\\TopazandNumby.png', "DATA")]
a.datas += [('assets\\images\\avatars\\TrailblazerDestruction#M.png','src\\assets\\images\\avatars\\TrailblazerDestruction#M.png', "DATA")]
a.datas += [('assets\\images\\avatars\\TrailblazerPreservation#M.png','src\\assets\\images\\avatars\\TrailblazerPreservation#M.png', "DATA")]
a.datas += [('assets\\images\\avatars\\TrailblazerDestruction#F.png','src\\assets\\images\\avatars\\TrailblazerDestruction#F.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Trailblazerpreservation#F.png','src\\assets\\images\\avatars\\TrailblazerPreservation#F.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Qingque.png','src\\assets\\images\\avatars\\Qingque.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Sampo.png','src\\assets\\images\\avatars\\Sampo.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Seele.png','src\\assets\\images\\avatars\\Seele.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Serval.png','src\\assets\\images\\avatars\\Serval.png', "DATA")]
a.datas += [('assets\\images\\avatars\\SilverWolf.png','src\\assets\\images\\avatars\\SilverWolf.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Sushang.png','src\\assets\\images\\avatars\\Sushang.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Tingyun.png','src\\assets\\images\\avatars\\Tingyun.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Welt.png','src\\assets\\images\\avatars\\Welt.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Yanqing.png','src\\assets\\images\\avatars\\Yanqing.png', "DATA")]
a.datas += [('assets\\images\\avatars\\Yukong.png','src\\assets\\images\\avatars\\Yukong.png', "DATA")]

pyz = PYZ(a.puassets\\re, a.zipped_data, cipher=block_cipher)

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
