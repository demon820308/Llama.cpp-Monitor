# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['start-mimo-gui.py'],
    pathex=[],
    binaries=[],
    datas=[('logo.ico', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'gi',
        'gi.repository',
        'pystray._appindicator',
        'pystray._darwin',
        'pystray._gtk',
        'pystray._xorg',
        'pystray._util.gtk',
        'pystray._util.notify_dbus',
        'Xlib',
        'AppKit',
        'Foundation',
        'objc',
        'PyObjCTools',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Llama Monitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['logo.ico'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Llama Monitor',
)
