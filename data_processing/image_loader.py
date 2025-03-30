import os
from PIL import Image
from typing import Optional, List
from utils.logger import log_method


class ImageLoader:
    @log_method
    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self.image_files = self._get_image_files()
        self.current_index = -1

    @log_method
    def _get_image_files(self) -> List[str]:
        return [
            f for f in os.listdir(self.folder_path)
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ]

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
