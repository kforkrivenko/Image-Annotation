# -*- mode: python ; coding: utf-8 -*-
import platform
import os
from PyInstaller.utils.hooks import collect_all

# Собираем необходимые модули
datas, binaries, hiddenimports = [], [], []

# Добавляем favicons
favicons = []
base_path = os.path.join(os.getcwd(), 'favicons')
if os.path.exists(base_path):
    for fname in os.listdir(base_path):
        full_path = os.path.join(base_path, fname)
        if os.path.isfile(full_path):
            favicons.append((full_path, 'favicons'))
datas += favicons

# Добавляем необходимые скрытые импорты
additional_hiddenimports = [
    'tkinter', 'subprocess', 'threading', 'time', 'os', 'sys', 'platform'
]

hiddenimports += additional_hiddenimports

a = Analysis(
    ['splash.py'],
    pathex=[os.getcwd()],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ImageAnnotation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ImageAnnotation',
)
if platform.system() == "Darwin":
    app = BUNDLE(
        coll,
        name='ImageAnnotation.app',
        icon='favicons/favicon.icns',
        bundle_identifier=None,
    )
