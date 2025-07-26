# -*- mode: python ; coding: utf-8 -*-
import platform
import os
from PyInstaller.utils.hooks import collect_all

# Собираем все необходимые модули проекта
modules = ['utils', 'ui', 'data_processing', 'api', 'ml']

datas, binaries, hiddenimports = [], [], []
for module in modules:
    try:
        d, b, h = collect_all(module)
        datas += d
        binaries += b
        hiddenimports += h
    except:
        pass

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
    'tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox', 'tkinter.simpledialog',
    'PIL', 'PIL.Image', 'PIL.ImageTk', 'PIL.ImageDraw', 'PIL.ImageFont',
    'torch', 'torch.cuda', 'torch.backends.mps',
    'ultralytics', 'ultralytics.YOLO',
    'cv2',
    'matplotlib', 'matplotlib.pyplot',
    'sklearn', 'sklearn.model_selection',
    'pandas',
    'numpy',
    'threading',
    'subprocess',
    'tempfile',
    'shutil',
    'zipfile',
    'collections',
    'datetime',
    'time',
    'sleep',
    'pathlib',
    'json',
    'yaml',
    'google_api_python_client',
    'google_auth_oauthlib'
]

hiddenimports += additional_hiddenimports

a = Analysis(
    ['main.py'],
    pathex=[os.getcwd()],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['annotated_dataset'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ImageAnnotationMain',
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
    name='ImageAnnotationMain',
)
if platform.system() == "Darwin":
    app = BUNDLE(
        coll,
        name='ImageAnnotationMain.app',
        icon='favicons/favicon.icns',
        bundle_identifier=None,
    )
