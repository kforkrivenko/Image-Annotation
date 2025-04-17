# -*- mode: python -*-
from PyInstaller.utils.hooks import collect_all
import os
import sys
import platform

# ========================================================
# 1. Настройка путей и зависимостей (универсальная)
# ========================================================

def find_python_lib():
    """Динамически находит путь к libpython*.dylib/.so/.dll"""
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    system = platform.system()

    if system == "Darwin":  # macOS
        paths = [
            # Стандартные пути на macOS
            f"/Library/Frameworks/Python.framework/Versions/{python_version}/lib/libpython{python_version}.dylib",
            f"/usr/local/opt/python@{python_version}/Frameworks/Python.framework/Versions/{python_version}/lib/libpython{python_version}.dylib",
            # Для Python из Homebrew
            f"/usr/local/lib/libpython{python_version}.dylib",
            # Для Python из Xcode Command Line Tools
            f"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/{python_version}/lib/libpython{python_version}.dylib"
        ]
    elif system == "Linux":
        paths = [
            f"/usr/lib/x86_64-linux-gnu/libpython{python_version}.so",
            f"/usr/local/lib/libpython{python_version}.so",
            f"/usr/lib/libpython{python_version}.so"
        ]
    else:  # Windows
        return None  # На Windows PyInstaller обычно сам находит pythonXX.dll

    for path in paths:
        if os.path.exists(path):
            return path
    return None

# Автоматически находим Python библиотеку
python_lib = find_python_lib()

# ========================================================
# 2. Сбор данных и зависимостей
# ========================================================

# Основные зависимости
datas, binaries, hiddenimports  = [], [], []
for module in ['utils', 'ui', 'models', 'data_processing', 'api']:
    d, b, h = collect_all(module)
    datas += d
    binaries += b
    hiddenimports += h

# Добавляем Python библиотеку, если нашли
if python_lib:
    binaries += [(python_lib, '.')]

# Статические файлы (относительные пути)
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
    runtime_hooks=[os.path.join(os.getcwd(), 'hooks/runtime_hook.py')],
    upx=True if platform.system() != "Darwin" else False  # UPX может вызывать проблемы на macOS
)

# ========================================================
# 4. Сборка исполняемого файла
# ========================================================

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='ImageAnnotation',
    debug=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,  # Для GUI приложения
    icon='favicons/favicon.icns' if platform.system() == "Darwin" else 'favicons/favicon.ico'
)

# ========================================================
# 5. Сборка .app бандла (только для macOS)
# ========================================================

if platform.system() == "Darwin":
    app = BUNDLE(
        exe,
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