from pathlib import Path
import os
from ui.app import ImageAnnotationApp
import sys
from utils.paths import *


def prepare_env():
    """Создает необходимые директории"""
    (DATA_DIR / "logs").mkdir(exist_ok=True)
    (DATA_DIR / "annotated_dataset").mkdir(exist_ok=True)


if __name__ == "__main__":
    prepare_env()
    app = ImageAnnotationApp()
    app.run()
