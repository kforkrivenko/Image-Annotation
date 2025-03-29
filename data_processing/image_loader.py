import os
from tkinter import messagebox

from PIL import Image


class ImageLoader:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.image_files = self._get_image_files()
        self.current_index = -1

    def _get_image_files(self):
        return [
            f for f in os.listdir(self.folder_path)
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ]

    def get_image(self, how):
        if how == "next":
            if self.current_index >= len(self.image_files):
                return None, None
            self.current_index += 1
            image_path = os.path.join(self.folder_path, self.image_files[self.current_index])
            return Image.open(image_path)
        elif how == "prev":
            if self.current_index <= 0:
                return None, None
            self.current_index -= 1
            image_path = os.path.join(self.folder_path, self.image_files[self.current_index])
            return Image.open(image_path)
        elif how == "current":
            if self.current_index == -1:
                return None, None
            image_path = os.path.join(self.folder_path, self.image_files[self.current_index])
            return Image.open(image_path)
        else:
            messagebox.showerror("How Error", str(TypeError(f"No such how: {how}")))

    def get_current_image_path(self):
        if 0 <= self.current_index < len(self.image_files):
            return self.image_files[self.current_index]

        return None
