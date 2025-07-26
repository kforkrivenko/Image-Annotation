#!/bin/bash
set -e

pyinstaller build_splash.spec
pyinstaller build_main.spec

rm -rf dist/final dist/windows dist/linux
mkdir -p dist/final dist/windows dist/linux

UNAME=$(uname -s)

if [[ "$UNAME" == "Darwin" ]]; then
    # macOS: финальный .app с основным .app внутри Resources
    cp -R dist/ImageAnnotation.app dist/final/ImageAnnotation.app
    cp -R dist/ImageAnnotationMain.app dist/final/ImageAnnotation.app/Contents/Resources/ImageAnnotationMain.app
elif [[ "$UNAME" == "Linux" ]]; then
    # Linux: splash и основной бинарник рядом
    cp -R dist/ImageAnnotation/* dist/linux/
    cp -R dist/ImageAnnotationMain/* dist/linux/
elif [[ "$UNAME" == *NT* ]] || [[ "$UNAME" == *MINGW* ]] || [[ "$UNAME" == *MSYS* ]] || [[ "$UNAME" == *CYGWIN* ]]; then
    # Windows: копируем только splash exe и папку с основным приложением
    cp -R dist/ImageAnnotation/* dist/windows/
    # Копируем содержимое основного приложения в отдельную папку
    mkdir -p dist/windows/ImageAnnotationMain
    cp -R dist/ImageAnnotationMain/* dist/windows/ImageAnnotationMain/
fi
