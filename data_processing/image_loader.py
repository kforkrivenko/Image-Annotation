import os
from PIL import Image


class ImageLoader:
    def __init__(self, folder_path=""):
        self.folder_path = folder_path
        self.image_files = []
        self.current_index = -1

    def load_images(self):
        if not self.image_files:
            self.image_files = [
                f for f in os.listdir(self.folder_path)
                if f.lower().endswith(('.jpg', '.jpeg', '.png'))
            ]
            self.current_index = 0 if self.image_files else -1

    def get_current_image(self):
        if 0 <= self.current_index < len(self.image_files):
            return Image.open(os.path.join(
                self.folder_path,
                self.image_files[self.current_index]
            ))
        return None

    def get_current_filename(self):
        if 0 <= self.current_index < len(self.image_files):
            return self.image_files[self.current_index]
        return None

    def next_image(self):
        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            return True
        return False

    def prev_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            return True
        return False

    def has_next(self):
        return self.current_index < len(self.image_files) - 1

    def has_prev(self):
        return self.current_index > 0