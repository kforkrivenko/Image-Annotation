import os
import json
import shutil
from datetime import datetime


class AnnotationSaver:
    def __init__(self):
        self.output_dir = "annotated_dataset"
        os.makedirs(self.output_dir, exist_ok=True)

        self.images_dir = os.path.join(self.output_dir, "images")
        self.annotations_dir = os.path.join(self.output_dir, "annotations")
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.annotations_dir, exist_ok=True)

    def save_annotation(self, original_path, regions):
        if not os.path.exists(original_path):
            return

        img_name = os.path.basename(original_path)
        img_dst = os.path.join(self.images_dir, img_name)

        if not os.path.exists(img_dst):
            shutil.copy2(original_path, img_dst)

        annotation = {
            "image": img_name,
            "timestamp": datetime.now().isoformat(),
            "regions": regions
        }

        ann_name = f"{os.path.splitext(img_name)[0]}.json"
        ann_path = os.path.join(self.annotations_dir, ann_name)

        with open(ann_path, 'w', encoding='utf-8') as f:
            json.dump(annotation, f, indent=2, ensure_ascii=False)
