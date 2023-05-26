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
a.datas += [('images\\app.ico','src\\images\\app.ico', "DATA")]
a.datas += [('images\\avatars\\arlan.png','src\\images\\avatars\\arlan.png', "DATA")]
a.datas += [('images\\avatars\\asta.png','src\\images\\avatars\\asta.png', "DATA")]
a.datas += [('images\\avatars\\bailu.png','src\\images\\avatars\\bailu.png', "DATA")]
a.datas += [('images\\avatars\\bronya.png','src\\images\\avatars\\bronya.png', "DATA")]
a.datas += [('images\\avatars\\clara.png','src\\images\\avatars\\clara.png', "DATA")]
a.datas += [('images\\avatars\\danheng.png','src\\images\\avatars\\danheng.png', "DATA")]
a.datas += [('images\\avatars\\gepard.png','src\\images\\avatars\\gepard.png', "DATA")]
a.datas += [('images\\avatars\\herta.png','src\\images\\avatars\\herta.png', "DATA")]
a.datas += [('images\\avatars\\himeko.png','src\\images\\avatars\\himeko.png', "DATA")]
a.datas += [('images\\avatars\\hook.png','src\\images\\avatars\\hook.png', "DATA")]
a.datas += [('images\\avatars\\jingyuan.png','src\\images\\avatars\\jingyuan.png', "DATA")]
a.datas += [('images\\avatars\\mar7th.png','src\\images\\avatars\\mar7th.png', "DATA")]
a.datas += [('images\\avatars\\natasha.png','src\\images\\avatars\\natasha.png', "DATA")]
a.datas += [('images\\avatars\\pela.png','src\\images\\avatars\\pela.png', "DATA")]
a.datas += [('images\\avatars\\playerboy1.png','src\\images\\avatars\\playerboy1.png', "DATA")]
a.datas += [('images\\avatars\\playerboy2.png','src\\images\\avatars\\playerboy2.png', "DATA")]
a.datas += [('images\\avatars\\playergirl1.png','src\\images\\avatars\\playergirl1.png', "DATA")]
a.datas += [('images\\avatars\\playergirl2.png','src\\images\\avatars\\playergirl2.png', "DATA")]
a.datas += [('images\\avatars\\qingque.png','src\\images\\avatars\\qingque.png', "DATA")]
a.datas += [('images\\avatars\\sampo.png','src\\images\\avatars\\sampo.png', "DATA")]
a.datas += [('images\\avatars\\seele.png','src\\images\\avatars\\seele.png', "DATA")]
a.datas += [('images\\avatars\\serval.png','src\\images\\avatars\\serval.png', "DATA")]
a.datas += [('images\\avatars\\sushang.png','src\\images\\avatars\\sushang.png', "DATA")]
a.datas += [('images\\avatars\\tingyun.png','src\\images\\avatars\\tingyun.png', "DATA")]
a.datas += [('images\\avatars\\welt.png','src\\images\\avatars\\welt.png', "DATA")]
a.datas += [('images\\avatars\\yanqing.png','src\\images\\avatars\\yanqing.png', "DATA")]

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
