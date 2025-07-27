#!/bin/bash
set -e

# pyinstaller build_splash.spec
pyinstaller build_main.spec

rm -rf dist/macos dist/windows dist/linux
mkdir -p dist/macos dist/windows dist/linux

UNAME=$(uname -s)

if [[ "$UNAME" == "Darwin" ]]; then
    # macOS: финальный .app с основным .app внутри Resources
    cp -R dist/ImageAnnotationMain.app dist/macos/ImageAnnotation.app
elif [[ "$UNAME" == "Linux" ]]; then
    # Linux: splash и основной бинарник рядом
    cp -R dist/ImageAnnotationMain/* dist/linux/
elif [[ "$UNAME" == *NT* ]] || [[ "$UNAME" == *MINGW* ]] || [[ "$UNAME" == *MSYS* ]] || [[ "$UNAME" == *CYGWIN* ]]; then
    # Копируем содержимое основного приложения в отдельную папку
    mkdir -p dist/windows/ImageAnnotationMain
    cp -R dist/ImageAnnotationMain/* dist/windows/ImageAnnotationMain/
fi
