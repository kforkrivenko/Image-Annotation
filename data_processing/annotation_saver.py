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

        # # Проверяем, есть ли уже запись.
        # try:
        #     with open(self.annotation_file, 'r') as f:
        #         data = json.load(f)
        # except Exception:
        #     data = {
        #         self.folder_path: {}
        #     }
        #
        # # Если есть, то удаляем
        # if self.folder_path in data:
        #     if img_name in data[self.folder_path]:
        #         del data[self.folder_path][img_name]
        #
        annotations_undouble = []

        for annotation in annotations:
            if annotation not in annotations_undouble:
                annotations_undouble.append(
                    {
                        'text': annotation['text'],
                        'coords': annotation['coords']
                    }
                )

        # if self.folder_path not in data:
        #     data[self.folder_path] = {}
        # data[self.folder_path][img_name] = annotations_undouble
        #
        # with open(self.annotation_file, 'w', encoding='utf-8') as f:
        #     json.dump(data, f, indent=2)

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

        # try:
        #     with open(self.annotation_file, 'r') as f:
        #         data = json.load(f)
        # except Exception:
        #     data = {}
        #
        # print(data, img_name)
        # if self.folder_path in data:
        #     if img_name in data[self.folder_path]:
        #         return data[self.folder_path][img_name]
        #
        # return []

        return self.json_manager.get_file_info(self.folder_path, img_name)

