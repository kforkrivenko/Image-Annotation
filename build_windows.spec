# -*- mode: python -*-
from PyInstaller.utils.hooks import collect_data_files
import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[os.getcwd()],
    binaries=[],
    datas=[
        *collect_data_files('PIL'),
        ('favicons/favicon.ico', 'favicons'),
        ('ui/*.ui', 'ui'),  # Если используете Qt Designer
        ('data_processing/*.py', 'data_processing')
    ],
    hiddenimports=['tkinter', 'PIL'],
    hookspath=[],
    runtime_hooks=[],
    excludes=['annotated_dataset'],  # Исключаем пользовательские данные
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