import json
from pathlib import Path
from typing import Any, Union, Dict, List
from models.annotation import Annotation


class JsonManager:
    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)
        self.data = self._load_or_create()

    def values(self):
        return self.data.values()

    def keys(self):
        return self.data.keys()

    def _save(self):
        """Сохраняет данные в JSON-файл."""
        with open(self.file_path, "w", encoding="utf-8") as file:
            json.dump(self.data, file, indent=4)

    def _load_or_create(self) -> Dict[str, Any]:
        """Загружает JSON или создаёт файл."""
        if not self.file_path.exists():
            self.file_path.write_text("{}", encoding="utf-8")
            return {}
        with open(self.file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data

    def __getitem__(self, key: str) -> Any:
        """Получить значение по ключу """
        return self.data.setdefault(key, None)

    def __setitem__(self, key: str, value: Any):
        """Установить словарь файлов для папки: `manager['папка'] = {'файл': [...]}`."""
        self.data[key] = value
        self._save()

    def __delitem__(self, key: str):
        """Удалить ключ."""
        del self.data[key]
        self._save()

    def __repr__(self) -> str:
        return f"JsonManager(file='{self.file_path}', data={self.data})"


class AnnotationFileManager(JsonManager):
    def __init__(self, file_path: Union[str, Path]):
        super().__init__(file_path)

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

    def delete_file(self, folder: str, file: str):
        """Удалить файл из папки: `manager.delete_file('папка', 'файл')`."""
        if folder in self.data and file in self.data[folder]:
            del self.data[folder][file]
            self._save()

    def delete_annotation(self, folder: str, file: str, annotation: dict):
        """Удалить аннотацию по файлу из папки."""
        if folder in self.data and file in self.data[folder]:
            for i, ann in enumerate(self.data[folder][file]):
                if Annotation.from_dict(ann) == Annotation.from_dict(annotation):
                    del self.data[folder][file][i]
            self._save()

    def add_file_info(self, folder: str, file: str, info: List[Any]):
        """Добавить информацию о файле: `manager.add_file_info('папка', 'файл', ['info1', 'info2'])`."""
        self.data.setdefault(folder, {}).setdefault(file, []).extend(info)
        self._save()

    def get_file_info(self, folder: str, file: str) -> List[Any]:
        """Получить информацию о файле: `info = manager.get_file_info('папка', 'файл')`."""
        return self.data.get(folder, {}).get(file, [])

    def get_folder_info(self, folder: str) -> Dict[str, List[Any]]:
        """Получить информацию о файле: `info = manager.get_file_info('папка', 'файл')`."""
        return self.data.get(folder, {})

    def __getitem__(self, key: str) -> Dict[str, List[Any]]:
        """Получить словарь файлов папки: `files = manager['папка']`."""
        return self.data.setdefault(key, {})

