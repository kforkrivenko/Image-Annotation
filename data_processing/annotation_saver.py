import os
import shutil
import json
from PIL import Image


class AnnotationSaver:
    def __init__(self):
        self.output_dir = "annotated_dataset"
        os.makedirs(self.output_dir, exist_ok=True)

        self.images_dir = os.path.join(self.output_dir, "images")
        self.annotations_dir = os.path.join(self.output_dir, "annotations")
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.annotations_dir, exist_ok=True)

    def save_annotation(self, original_path, rectangles):
        """Сохраняет копию изображения и аннотацию"""
        if not os.path.exists(original_path):
            raise FileNotFoundError(f"Source image not found: {original_path}")

        img_name = os.path.basename(original_path)
        img_dst = os.path.join(self.images_dir, img_name)

        try:
            if not os.path.exists(img_dst):
                shutil.copy2(original_path, img_dst)
        except Exception as e:
            raise RuntimeError(f"Failed to copy image: {e}")

        # Сохраняем аннотацию
        annotation = {
            "image": img_name,
            "regions": rectangles
        }

        ann_name = f"{os.path.splitext(img_name)[0]}.json"
        ann_path = os.path.join(self.annotations_dir, ann_name)

        with open(ann_path, 'w') as f:
            json.dump(annotation, f, indent=2)