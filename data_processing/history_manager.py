import json
from pathlib import Path
from typing import List, Dict, Optional


class DatasetHistoryManager:
    def __init__(self):
        self.history_file = Path("dataset_history.json")
        self.history = self._load_history()

    def _load_history(self) -> Dict[str, Dict]:
        """Загружает историю из JSON-файла."""
        if not self.history_file.exists():
            return {}
        with open(self.history_file, "r") as f:
            return json.load(f)

    def add_dataset(self, dataset_path: str, annotations_path: str) -> None:
        """Добавляет датасет в историю."""
        dataset_name = Path(dataset_path).name
        self.history[dataset_name] = {
            "original_path": str(dataset_path),
            "annotations_path": str(annotations_path),
            "images_count": len(list(Path(annotations_path).glob("images/*"))),
            "last_modified": str(Path(annotations_path).stat().st_mtime)
        }
        self._save_history()

    def _save_history(self) -> None:
        """Сохраняет историю в файл."""
        with open(self.history_file, "w") as f:
            json.dump(self.history, f, indent=4)

    def get_all_datasets(self) -> List[Dict]:
        """Возвращает список всех датасетов."""
        return [
            {"name": name, **data}
            for name, data in self.history.items()
        ]
