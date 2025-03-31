# -*- mode: python -*-
from PyInstaller.utils.hooks import collect_data_files
import os

# Получаем все зависимости для модулей
datas, binaries, hiddenimports = collect_all('utils')
datas += collect_all('ui')[0]
datas += collect_all('models')[0]
datas += collect_all('logger')[0]
datas += collect_all('data_processing')[0]

# Добавляем статические файлы
datas += [
    ('favicons/favicon.icns', 'favicons'),
    ('favicons/favicon.ico', 'favicons')
]

# Исключаем динамические данные
excludes = ['annotated_dataset']

a = Analysis(
    ['main.py'],
    pathex=[os.getcwd()],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False
)

exe = EXE(
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='ImageAnnotationTool',
    debug=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,  # Убрать консоль
    icon='favicons/favicon.ico',
)