import sys
import os
from pathlib import Path


def get_base_dir():
    """Возвращает базовую директорию в зависимости от режима запуска"""
    if getattr(sys, 'frozen', False):  # Собранное приложение
        return Path(sys._MEIPASS)
    return Path(os.path.dirname(os.path.abspath(__file__))).parent  # Режим разработки


def get_data_dir():
    """Возвращает директорию для хранения данных"""
    if sys.platform == "darwin":
        path = Path.home() / "Library/Application Support/ImageAnnotationTool"
    elif sys.platform == "win32":
        path = Path(os.getenv('LOCALAPPDATA')) / "ImageAnnotationTool"
    else:
        path = Path.home() / ".imageannotationtool"

    path.mkdir(exist_ok=True, parents=True)
    return path


BASE_DIR = get_base_dir()
DATA_DIR = get_data_dir()
