import os
from PIL import Image


class ImageLoader:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.image_files = self._get_image_files()
        self.current_index = 0

    def _get_image_files(self):
        return [f for f in os.listdir(self.folder_path)
                if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

    def get_next_image(self):
        if self.current_index >= len(self.image_files):
            return None

        image_path = os.path.join(self.folder_path, self.image_files[self.current_index])
        self.current_index += 1
        return Image.open(image_path)

    def get_current_filename(self):
        """Возвращает имя текущего файла (без пути)"""
        if 0 <= self.current_index - 1 < len(self.image_files):
            return self.image_files[self.current_index - 1]
        return None

    def get_current_image_path(self):
        """Возвращает полный путь к текущему изображению"""
        filename = self.get_current_filename()
        if filename:
            return os.path.join(self.folder_path, filename)
        return None