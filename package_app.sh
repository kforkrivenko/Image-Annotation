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
    cp dist/ImageAnnotation dist/linux/ImageAnnotation
    cp dist/ImageAnnotationMain dist/linux/ImageAnnotationMain
elif [[ "$UNAME" == *NT* ]] || [[ "$UNAME" == *MINGW* ]] || [[ "$UNAME" == *MSYS* ]] || [[ "$UNAME" == *CYGWIN* ]]; then
    # Windows: splash.exe и основной exe рядом
    cp dist/ImageAnnotation.exe dist/windows/ImageAnnotation.exe
    cp dist/ImageAnnotationMain.exe dist/windows/ImageAnnotationMain.exe
fi
