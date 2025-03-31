import sys
from utils.paths import DATA_DIR, BASE_DIR
from .history_manager import DatasetHistoryManager
import json
import shutil
from pathlib import Path
from typing import List, Dict, Any
from models.annotation import Annotation
from utils.paths import *


class AnnotationSaver:
    def __init__(self, folder_path: str):
        self.history_manager = DatasetHistoryManager()
        self.source_folder = Path(folder_path)

        # Выбираем куда сохранять в зависимости от режима
        if getattr(sys, 'frozen', False):
            self.output_dir = DATA_DIR / "annotated_datasets"
        else:
            self.output_dir = BASE_DIR / "annotated_dataset"

        self.output_dir.mkdir(exist_ok=True)
        self.output_dir_images = self.output_dir / "images"
        self.output_dir_images.mkdir(exist_ok=True)
        self.annotations_file = self.output_dir / "annotations.json"

    def save_annotations(self, image_path: str, annotations: List[Annotation]):
        # Получаем полный путь к исходному изображению
        full_image_path = self.source_folder / Path(image_path).name
        img_name = full_image_path.name

        self._copy_image_to_output(full_image_path)

        annotations_data = [ann.to_dict() for ann in annotations]
        all_annotations = self._load_all_annotations()

        # Сохраняем с полным путем к папке для уникальности
        all_annotations.setdefault(str(self.source_folder), {})[img_name] = annotations_data

        with open(self.annotations_file, 'w') as f:
            json.dump(all_annotations, f, indent=4)

        self.history_manager.add_dataset(
            dataset_path=str(self.source_folder),
            annotations_path=str(self.output_dir)
        )

    def _copy_image_to_output(self, src_path: Path):
        if not src_path.exists():
            return

        dst_path = self.output_dir / "images" / src_path.name

        if not dst_path.exists():
            shutil.copy2(src_path, dst_path)

    def get_annotations(self, image_path: str) -> List[Annotation]:
        img_name = Path(image_path).name
        all_annotations = self._load_all_annotations()
        annotations_data = all_annotations.get(str(self.source_folder), {}).get(img_name, [])
        return [Annotation.from_dict(ann) for ann in annotations_data]

    def _load_all_annotations(self):
        if not self.annotations_file.exists():
            return {}

        with open(self.annotations_file, 'r') as f:
            return json.load(f)
