# -*- mode: python ; coding: utf-8 -*-
import platform

# Анализируем зависимости
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# Создание .pyz архива
pyz = PYZ(a.pure)

# Платформозависимая сборка
if platform.system() == "Darwin":
    # macOS: оставляем как есть
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

    app = BUNDLE(
        coll,
        name='ImageAnnotationMain.app',
        icon='favicons/favicon.icns',
        bundle_identifier=None,
    )

else:
    # Windows и Linux: включаем бинарники в .exe
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,  # <--- Важно
        exclude_binaries=False,  # <--- Включаем бинарники в exe
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
