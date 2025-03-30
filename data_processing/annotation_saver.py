import os
import json
import shutil
from utils.annotations_manager import JsonManager


class AnnotationSaver:
    def __init__(self, folder_path):
        self.output_dir = "annotated_dataset"
        os.makedirs(self.output_dir, exist_ok=True)

        self.images_dir = os.path.join(self.output_dir, "images")
        os.makedirs(self.images_dir, exist_ok=True)
        self.folder_path = folder_path

        self.json_manager = JsonManager(
            os.path.join(self.output_dir, 'annotations.json')
        )

    def save_annotation(self, original_path, annotations):
        if not os.path.exists(original_path):
            return

        img_name = os.path.basename(original_path)
        img_dst = os.path.join(self.images_dir, img_name)

        if not os.path.exists(img_dst):
            shutil.copy2(original_path, img_dst)

        annotations_undouble = []

        # Дедубликация аннотаций
        for annotation in annotations:
            annotation_jsoned = {
                'text': annotation['text'],
                'coords': annotation['coords'],
                'ratio': annotation['ratio']
            }
            if annotation_jsoned not in annotations_undouble:
                annotations_undouble.append(annotation_jsoned)

        self.json_manager.delete_file(
            self.folder_path,
            img_name
        )

        self.json_manager.add_file_info(
            self.folder_path,
            img_name,
            annotations_undouble
        )

    def get_annotation_from_file(self, original_path):
        img_name = os.path.basename(original_path)

        return self.json_manager.get_file_info(self.folder_path, img_name)

