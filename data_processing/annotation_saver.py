from utils.json_manager import AnnotationFileManager
import shutil
from typing import List, Dict
from models.annotation import Annotation
from utils.paths import *


class AnnotationSaver:
    def __init__(self, folder_path: str):
        self.source_folder = Path(folder_path)

        # Выбираем куда сохранять в зависимости от режима
        self.output_dir = DATA_DIR / "annotated_dataset"

        self.output_dir.mkdir(exist_ok=True)

        self.json_manager = AnnotationFileManager(
            os.path.join(self.output_dir, 'annotations.json')
        )

        self.annotations_file = self.output_dir / "annotations.json"

    def save_annotations(self, image_path: str, annotations: List[Annotation]):
        # Получаем полный путь к исходному изображению
        full_image_path = self.source_folder / Path(image_path).name
        img_name = full_image_path.name

        self._copy_image_to_output(full_image_path)

        annotations_data = [ann.to_dict() for ann in annotations]

        self.json_manager.delete_file(
            str(self.source_folder),
            img_name
        )

        self.json_manager.add_file_info(
            str(self.source_folder),
            img_name,
            annotations_data
        )

    def _copy_image_to_output(self, src_path: Path):
        if not src_path.exists():
            return

        dst_path = self.output_dir / "images" / src_path.name

        if not dst_path.exists():
            shutil.copy2(src_path, dst_path)

    def get_annotations(self, image_path: str) -> List[Annotation]:
        img_name = Path(image_path).name
        return [
            Annotation.from_dict(annotation_dict)
            for annotation_dict in self.json_manager.get_file_info(str(self.source_folder), img_name)
        ]

    def delete_annotation_from_file(self, image_path: str, annotation: Annotation) -> None:
        self.json_manager.delete_annotation(str(self.source_folder), image_path, annotation.to_dict())

    def add_annotation_to_file(self, image_path: str, annotation: Annotation) -> None:
        self.json_manager.add_file_info(str(self.source_folder), image_path, [annotation.to_dict()])
