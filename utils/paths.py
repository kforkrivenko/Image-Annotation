import sys
import os
from pathlib import Path


def get_data_dir():
    """Возвращает директорию для хранения данных"""
    if getattr(sys, 'frozen', False):  # Собранное приложение
        if sys.platform == "darwin":
            path = Path.home() / "Library/Application Support/ImageAnnotationTool"
        elif sys.platform == "win32":
            path = Path(os.getenv('LOCALAPPDATA')) / "ImageAnnotationTool"
        else:
            path = Path.home() / ".imageannotationtool"

        path.mkdir(exist_ok=True, parents=True)
        return path
    else:
        return Path(os.path.dirname(os.path.abspath(__file__))).parent   # Режим разработки


#  BASE_DIR = get_base_dir()
DATA_DIR = get_data_dir()
