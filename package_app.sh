#!/bin/bash
set -e

# Очистка предыдущих сборок
rm -rf dist/ build/ __pycache__
mkdir -p dist/windows dist/macos dist/linux

UNAME=$(uname -s)

if [[ "$UNAME" == "Darwin" ]]; then
    echo "📦 macOS: Сборка в режиме --onedir (PyInstaller onefile не работает стабильно на macOS)"
    pyinstaller build_main.spec
    cp -R dist/ImageAnnotationMain.app dist/macos/ImageAnnotationMain.app
elif [[ "$UNAME" == "Linux" ]]; then
    echo "📦 Linux: Сборка в режиме --onefile"
    pyinstaller build_main.spec
    cp dist/ImageAnnotationMain dist/linux/ImageAnnotationMain
elif [[ "$UNAME" == *NT* ]] || [[ "$UNAME" == *MINGW* ]] || [[ "$UNAME" == *MSYS* ]] || [[ "$UNAME" == *CYGWIN* ]]; then
    echo "📦 Windows: Сборка в режиме --onefile"
    pyinstaller --onefile --noconsole --name ImageAnnotationMain main.py
    cp dist/ImageAnnotationMain.exe dist/windows/ImageAnnotationMain.exe
else
    echo "❌ Неизвестная платформа: $UNAME"
    exit 1
fi

echo "✅ Сборка завершена!"
