import json
from pathlib import Path
from typing import Any, Union, Optional, Dict, List


class JsonManager:
    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)
        self.data = self._load_or_create()

    def _load_or_create(self) -> Dict[str, Dict[str, List[Any]]]:
        """Загружает JSON или создаёт файл с пустым словарём словарей."""
        if not self.file_path.exists():
            self.file_path.write_text("{}", encoding="utf-8")
            return {}
        with open(self.file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            # Проверяем, что структура соответствует нужному формату
            if not all(isinstance(v, dict) for v in data.values()):
                raise ValueError("JSON must be a dict of dicts of lists!")
            return data

    def _save(self):
        """Сохраняет данные в JSON-файл."""
        with open(self.file_path, "w", encoding="utf-8") as file:
            json.dump(self.data, file, indent=4)

    def __getitem__(self, key: str) -> Dict[str, List[Any]]:
        """Получить словарь файлов папки: `files = manager['папка']`."""
        return self.data.setdefault(key, {})

    def __setitem__(self, key: str, value: Dict[str, List[Any]]):
        """Установить словарь файлов для папки: `manager['папка'] = {'файл': [...]}`."""
        if not isinstance(value, dict):
            raise ValueError("Value must be a dict of lists!")
        self.data[key] = value
        self._save()

    def add_file_info(self, folder: str, file: str, info: List[Any]):
        """Добавить информацию о файле: `manager.add_file_info('папка', 'файл', ['info1', 'info2'])`."""
        self.data.setdefault(folder, {}).setdefault(file, []).extend(info)
        self._save()

    def get_file_info(self, folder: str, file: str) -> List[Any]:
        """Получить информацию о файле: `info = manager.get_file_info('папка', 'файл')`."""
        return self.data.get(folder, {}).get(file, [])

    def __delitem__(self, key: str):
        """Удалить папку: `del manager['папка']`."""
        del self.data[key]
        self._save()

    def delete_file(self, folder: str, file: str):
        """Удалить файл из папки: `manager.delete_file('папка', 'файл')`."""
        if folder in self.data and file in self.data[folder]:
            del self.data[folder][file]
            self._save()

    def __repr__(self) -> str:
        return f"JsonManager(file='{self.file_path}', data={self.data})"