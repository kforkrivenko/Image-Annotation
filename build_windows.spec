from PyInstaller.utils.hooks import collect_data_files
import os

a = Analysis(
    ['main.py'],
    pathex=[os.getcwd()],
    binaries=[],
    datas=[
        *collect_data_files('PIL'),
        ('favicons/favicon.ico', 'favicons'),
        ('ui', 'ui'),
        ('data_processing', 'data_processing'),
        ('models', 'models'),
        ('logger', 'logger'),
        ('utils', 'utils'),
    ],
    hiddenimports=['tkinter', 'PIL'],
    hookspath=[],
    runtime_hooks=[],
    excludes=['annotated_dataset'],

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
