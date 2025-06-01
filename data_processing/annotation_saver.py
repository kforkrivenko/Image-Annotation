from utils.json_manager import AnnotationFileManager
from typing import List
from utils.annotation import Annotation
from utils.paths import *


class AnnotationSaver:
    def __init__(self, folder_path: str, annotated_path=None):
        self.source_folder = Path(folder_path)
        self.annotated_path = annotated_path

        # Выбираем куда сохранять в зависимости от режима
        self.output_dir = DATA_DIR / "annotated_dataset"

        self.output_dir.mkdir(exist_ok=True)

        self.json_manager = AnnotationFileManager(
            os.path.join(self.output_dir, 'annotations.json')
        )

        self.annotations_file = self.output_dir / "annotations.json"

    def get_annotations(self, image_path: str) -> List[Annotation]:
        img_name = Path(image_path).name
        if self.annotated_path is None:
            return [
                Annotation.from_dict(annotation_dict)
                for annotation_dict in self.json_manager.get_file_info(str(self.source_folder), img_name)
            ]
        else:
            print("HERE", self.annotated_path, img_name)
            return [
                Annotation.from_dict(annotation_dict)
                for annotation_dict in self.json_manager.get_file_info(str(self.annotated_path), img_name)
            ]

    def delete_annotation_from_file(self, image_path: str, annotation: Annotation) -> None:
        self.json_manager.delete_annotation(str(self.source_folder), image_path, annotation.to_dict())

    def add_annotation_to_file(self, image_path: str, annotation: Annotation) -> None:
        self.json_manager.add_file_info(str(self.source_folder), image_path, [annotation.to_dict()])
