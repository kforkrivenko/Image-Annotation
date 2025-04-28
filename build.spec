# -*- mode: python -*-
from PyInstaller.utils.hooks import collect_all
import os
import sys
import platform

# ========================================================
# 1. Настройка путей и зависимостей
# ========================================================

def find_python_lib():
    """Динамически находит путь к libpython*.dylib/.so/.dll"""
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    system = platform.system()

    if system == "Darwin":  # macOS
        paths = [
            f"/Library/Frameworks/Python.framework/Versions/{python_version}/lib/libpython{python_version}.dylib",
            f"/usr/local/opt/python@{python_version}/Frameworks/Python.framework/Versions/{python_version}/lib/libpython{python_version}.dylib",
            f"/usr/local/lib/libpython{python_version}.dylib",
            f"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/{python_version}/lib/libpython{python_version}.dylib"
        ]
    elif system == "Linux":
        paths = [
            f"/usr/lib/x86_64-linux-gnu/libpython{python_version}.so",
            f"/usr/local/lib/libpython{python_version}.so",
            f"/usr/lib/libpython{python_version}.so"
        ]
    else:  # Windows
        return None

    for path in paths:
        if os.path.exists(path):
            return path
    return None

python_lib = find_python_lib()

# ========================================================
# 2. Сбор данных и зависимостей
# ========================================================

datas, binaries, hiddenimports = [], [], []
for module in ['utils', 'ui', 'models', 'data_processing', 'api', 'ml']:
    d, b, h = collect_all(module)
    datas += d
    binaries += b
    hiddenimports += h

# Добавляем Python библиотеку, если нашли
if python_lib:
    binaries += [(python_lib, '.')]

# Статические файлы
datas += [
    ('favicons/favicon.icns', 'favicons'),
    ('favicons/favicon.png', 'favicons'),
    ('favicons/favicon.ico', 'favicons')
]

# Исключения
excludes = ['annotated_dataset']

# ========================================================
# 3. Конфигурация Analysis
# ========================================================

a = Analysis(
    ['main.py'],
    pathex=[os.getcwd()],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    excludes=excludes,
    noarchive=True,
    runtime_tmpdir=None,
    python_optimize=0,
    upx=True if platform.system() != "Darwin" else False
)

pyz = PYZ(a.pure, a.zipped_data)

# ========================================================
# 4. Конфигурация EXE
# ========================================================

exe = EXE(
    pyz,
    a.scripts,
    [],
    [],
    [],
    name='ImageAnnotation',
    debug=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,
    icon='favicons/favicon.icns' if platform.system() == "Darwin" else 'favicons/favicon.ico'
)

# ========================================================
# 5. Сборка через COLLECT
# ========================================================

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='ImageAnnotation'
)

# ========================================================
# 6. Сборка .app для macOS
# ========================================================

if platform.system() == "Darwin":
    app = BUNDLE(
        coll,
        name='ImageAnnotation.app',
        icon='favicons/favicon.icns',
        bundle_identifier='com.yourdomain.imageannotation',
        info_plist={
            'CFBundleDocumentTypes': [{
                'CFBundleTypeName': 'Image Annotation Project',
                'CFBundleTypeExtensions': ['iap'],
                'CFBundleTypeRole': 'Editor'
            }],
            'NSHighResolutionCapable': 'True',
            'LSMinimumSystemVersion': '10.15',
            'NSRequiresAquaSystemAppearance': 'False'
        }
    )
