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

        self.annotation_file = 'annotations.json'

    def save_annotation(self, original_path, annotations):
        if not os.path.exists(original_path):
            return

        img_name = os.path.basename(original_path)
        img_dst = os.path.join(self.images_dir, img_name)

        if not os.path.exists(img_dst):
            shutil.copy2(original_path, img_dst)

        # Проверяем, есть ли уже запись.
        try:
            with open(self.annotation_file, 'r') as f:
                data = json.load(f)
        except Exception:
            data = {}

        # Если есть, то удаляем
        if img_name in data:
            del data[img_name]

        annotations_undouble = []

        for annotation in annotations:
            if annotation not in annotations_undouble:
                annotations_undouble.append(
                    {
                        'text': annotation['text'],
                        'coords': annotation['coords']
                    }
                )

        data[img_name] = annotations_undouble

        print("DATA", annotations_undouble)

        with open(self.annotation_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def get_annotation_from_file(self, original_path):
        if not os.path.exists(original_path):
            print("No original path", original_path)
            return []

        img_name = os.path.basename(original_path)

        try:
            with open(self.annotation_file, 'r') as f:
                data = json.load(f)
        except Exception:
            data = {}

        print(data, img_name)
        if img_name in data:
            return data[img_name]

        return []

