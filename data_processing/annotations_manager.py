import json
from pathlib import Path
from typing import Any, Dict, List, Union


class JsonManager:
    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)
        self.data = self._load_or_create()

    def _load_or_create(self) -> Dict[str, Dict[str, List[Any]]]:
        if not self.file_path.exists():
            self.file_path.parent.mkdir(exist_ok=True)
            self.file_path.write_text("{}", encoding="utf-8")
            return {}

        with open(self.file_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def _save(self):
        with open(self.file_path, "w", encoding="utf-8") as file:
            json.dump(self.data, file, indent=4)

    def add_file_info(self, folder: str, file: str, info: List[Any]):
        self.data.setdefault(folder, {}).setdefault(file, []).extend(info)
        self._save()

    def get_file_info(self, folder: str, file: str) -> List[Any]:
        return self.data.get(folder, {}).get(file, [])
