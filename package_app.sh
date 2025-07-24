#!/bin/bash
set -e

# Сборка Splash и Main
pyinstaller build_splash.spec
pyinstaller build_main.spec

# Удалим, если старая сборка есть
rm -rf dist/final
mkdir -p dist/final

# Копируем Splash.app как ImageAnnotation.app
cp -R dist/ImageAnnotation.app dist/final/ImageAnnotation.app

# Копируем основное приложение внутрь Resources
cp -R dist/ImageAnnotationMain.app dist/final/ImageAnnotation.app/Contents/Resources/ImageAnnotationMain.app
