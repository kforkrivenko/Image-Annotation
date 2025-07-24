#!/bin/bash
set -e

pyinstaller build_splash.spec
pyinstaller build_main.spec

rm -rf dist/final dist/windows dist/linux
mkdir -p dist/final dist/windows dist/linux

# macOS: финальный .app с основным .app внутри Resources
cp -R dist/ImageAnnotation.app dist/final/ImageAnnotation.app
cp -R dist/ImageAnnotationMain.app dist/final/ImageAnnotation.app/Contents/Resources/ImageAnnotationMain.app

# Windows: splash.exe и основной exe рядом
if [[ "$(uname -s)" == *NT* ]] || [[ "$(uname -o 2>/dev/null)" == *Msys* ]] || [[ "$(uname -o 2>/dev/null)" == *Cygwin* ]]; then
    cp dist/ImageAnnotation.exe dist/windows/ImageAnnotation.exe
    cp dist/ImageAnnotationMain.exe dist/windows/ImageAnnotationMain.exe
fi

# Linux: splash и основной бинарник рядом
if [[ "$(uname -s)" == "Linux" ]]; then
    cp dist/image_annotation dist/linux/image_annotation
    cp dist/image_annotation_main dist/linux/image_annotation_main
fi
