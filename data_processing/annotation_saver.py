import os
import json
import shutil
from pathlib import Path
from typing import List, Dict, Any
from models.annotation import Annotation


class AnnotationSaver:
    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self.output_dir = Path("annotated_dataset")
        self.annotations_file = self.output_dir / "annotations.json"
        self._setup_output_dirs()

    def _setup_output_dirs(self):
        self.output_dir.mkdir(exist_ok=True)
        (self.output_dir / "images").mkdir(exist_ok=True)

    def save_annotations(self, image_path: str, annotations: List[Annotation]):
        # Получаем полный путь к исходному изображению
        full_image_path = Path(self.folder_path) / Path(image_path).name
        img_name = full_image_path.name

        self._copy_image_to_output(full_image_path)

        annotations_data = [ann.to_dict() for ann in annotations]
        all_annotations = self._load_all_annotations()

        # Сохраняем с полным путем к папке для уникальности
        all_annotations.setdefault(str(self.folder_path), {})[img_name] = annotations_data

        with open(self.annotations_file, 'w') as f:
            json.dump(all_annotations, f, indent=4)

    def _copy_image_to_output(self, src_path: Path):
        if not src_path.exists():
            return

        dst_path = self.output_dir / "images" / src_path.name
        if not dst_path.exists():
            shutil.copy2(src_path, dst_path)

    def get_annotations(self, image_path: str) -> List[Annotation]:
        img_name = Path(image_path).name
        all_annotations = self._load_all_annotations()
        annotations_data = all_annotations.get(str(self.folder_path), {}).get(img_name, [])
        return [Annotation.from_dict(ann) for ann in annotations_data]

    def _load_all_annotations(self):
        if not self.annotations_file.exists():
            return {}

        with open(self.annotations_file, 'r') as f:
            return json.load(f)
