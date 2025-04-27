import os
from PIL import Image
from typing import Optional, List

from utils.json_manager import JsonManager, AnnotationFileManager
from utils.logger import log_method
from utils.paths import DATA_DIR


class ImageLoader:
    @log_method
    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self.image_files = self._get_image_files()
        self.current_index = -1

        self.get_first_unannotated_image()

    @log_method
    def _get_image_files(self) -> List[str]:
        return list(sorted([
            f for f in os.listdir(self.folder_path)
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ]))

    @log_method
    def get_first_unannotated_image(self) -> None:
        images_files = self._get_image_files()
        output_dir = DATA_DIR / "annotated_dataset"
        annotation_manager = AnnotationFileManager(os.path.join(output_dir, 'annotations.json'))

        for i, image_file in enumerate(images_files):
            if image_file not in annotation_manager[str(self.folder_path)].keys():
                print("image_file", image_file, i)
                self.current_index = i - 1
                break

    @log_method
    def get_image(self, direction: str = "next") -> Optional[Image.Image]:
        if direction == "next":
            if self.current_index >= len(self.image_files) - 1:
                return None
            self.current_index += 1
        elif direction == "prev":
            if self.current_index <= 0:
                return None
            self.current_index -= 1
        elif direction != "current":
            raise ValueError(f"Invalid direction: {direction}")

        return self._load_current_image()

    @log_method
    def _load_current_image(self) -> Optional[Image.Image]:
        if 0 <= self.current_index < len(self.image_files):
            image_path = os.path.join(self.folder_path, self.image_files[self.current_index])
            return Image.open(image_path)
        return None

    @log_method
    def get_current_image_path(self) -> Optional[str]:
        if 0 <= self.current_index < len(self.image_files):
            return self.image_files[self.current_index]
        return None
