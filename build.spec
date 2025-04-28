# -*- mode: python -*-
import os
import sys
import platform
from PyInstaller.utils.hooks import collect_all

# ========================================================
# 1. Функция поиска libpython (для Mac и Linux)
# ========================================================

def find_python_lib():
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    system = platform.system()

    if system == "Darwin":
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
    else:
        return None

    for path in paths:
        if os.path.exists(path):
            return path
    return None

python_lib = find_python_lib()

# ========================================================
# 2. Сбор всех модулей и ресурсов
# ========================================================

# Сбор всех файлов из favicons/
def collect_favicons():
    favicons = []
    base_path = os.path.join(os.getcwd(), 'favicons')
    if os.path.exists(base_path):
        for fname in os.listdir(base_path):
            full_path = os.path.join(base_path, fname)
            if os.path.isfile(full_path):
                favicons.append((full_path, 'favicons'))
    return favicons

# Модули проекта
modules = ['utils', 'ui', 'models', 'data_processing', 'api', 'ml']

datas, binaries, hiddenimports = [], [], []
for module in modules:
    d, b, h = collect_all(module)
    datas += d
    binaries += b
    hiddenimports += h

# Добавляем найденную библиотеку python (для Mac/Linux)
if python_lib:
    binaries += [(python_lib, '.')]

# Добавляем фавиконки
datas += collect_favicons()

# Модули которые исключаем (если есть)
excludes = ['annotated_dataset']

# ========================================================
# 3. Analysis
# ========================================================

a = Analysis(
    ['main.py'],                 # Главный скрипт
    pathex=[os.getcwd()],         # Путь к проекту
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    excludes=excludes,
    noarchive=False,              # Архивируем (ускоряет запуск!)
    runtime_tmpdir=None,
    python_optimize=2,            # Максимальная оптимизация байткода
    upx=True if platform.system() != "Darwin" else False  # UPX использовать, но на Mac — осторожно
)

# ========================================================
# 4. Компиляция
# ========================================================

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='ImageAnnotation',
    debug=False,
    strip=True,                   # Убираем дебажные символы (меньше размер)
    upx=True,
    console=False,                 # Без консоли (GUI)
    icon='favicons/favicon.icns' if platform.system() == "Darwin" else 'favicons/favicon.ico'
)

# ========================================================
# 5. macOS: создание полноценного .app пакета
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
