import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import os
import json
from data_processing.image_loader import ImageLoader
from data_processing.annotation_saver import AnnotationSaver
from ui.canvas_tools import CanvasTool


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Annotation Tool")

        # Инициализация компонентов
        self.canvas_tool = CanvasTool(self.root)
        self.image_loader = ImageLoader()
        self.annotation_saver = AnnotationSaver()
        self.selection_memory = {}

        # UI элементы
        self._setup_ui()

        # Горячие клавиши
        self.root.bind("<Left>", lambda e: self._prev_image())
        self.root.bind("<Right>", lambda e: self._next_image())
        self.root.bind("<Delete>", lambda e: self.canvas_tool.delete_selected())
        self.root.bind("<e>", lambda e: self.canvas_tool.edit_selected())

    def _setup_ui(self):
        # Панель управления
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=10)

        self.load_btn = tk.Button(
            control_frame,
            text="Загрузить папку",
            command=self._load_folder
        )
        self.load_btn.pack(side=tk.LEFT, padx=5)

        # Панель навигации
        nav_frame = tk.Frame(self.root)
        nav_frame.pack(pady=5)

        self.prev_btn = tk.Button(
            nav_frame,
            text="← Назад",
            command=self._prev_image,
            state=tk.DISABLED
        )
        self.prev_btn.pack(side=tk.LEFT, padx=5)

        self.next_btn = tk.Button(
            nav_frame,
            text="Вперед →",
            command=self._next_image,
            state=tk.DISABLED
        )
        self.next_btn.pack(side=tk.LEFT)

        self.progress_var = tk.StringVar()
        tk.Label(
            nav_frame,
            textvariable=self.progress_var
        ).pack(side=tk.LEFT, padx=10)

    def _load_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.image_loader = ImageLoader(folder_path)
            self.image_loader.load_images()
            self._update_navigation()
            self._load_current_image()

    def _update_navigation(self):
        self.prev_btn.config(state=tk.NORMAL if self.image_loader.has_prev() else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if self.image_loader.has_next() else tk.DISABLED)
        self.progress_var.set(
            f"{self.image_loader.current_index + 1}/{len(self.image_loader.image_files)}"
        )

    def _load_current_image(self):
        if not self.image_loader.image_files:
            return

        self._save_current_state()

        image = self.image_loader.get_current_image()
        if image:
            filename = self.image_loader.get_current_filename()
            self.canvas_tool.clear_canvas()
            self.canvas_tool.display_image(image)

            # Загружаем аннотации
            ann_path = os.path.join(
                "annotated_dataset/annotations",
                f"{os.path.splitext(filename)[0]}.json"
            )

            if os.path.exists(ann_path):
                with open(ann_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for ann in data.get("regions", []):
                        self.canvas_tool.draw_annotation(
                            ann,
                            is_selected=filename in self.selection_memory and
                                        len(self.canvas_tool.rectangles) in self.selection_memory[filename]
                        )

            # Восстанавливаем выделения
            if filename in self.selection_memory:
                for idx in self.selection_memory[filename]:
                    if idx < len(self.canvas_tool.rectangles):
                        self.canvas_tool._select_annotation(idx)

            self._update_navigation()

    def _save_current_state(self):
        if hasattr(self.image_loader, 'get_current_filename'):
            filename = self.image_loader.get_current_filename()
            if filename:
                self.selection_memory[filename] = list(self.canvas_tool.selected_annotations)
                regions = self.canvas_tool.get_regions()
                if regions:
                    self.annotation_saver.save_annotation(
                        os.path.join(self.image_loader.folder_path, filename),
                        regions
                    )

    def _prev_image(self, event=None):
        self._save_current_state()
        if self.image_loader.prev_image():
            self._load_current_image()

    def _next_image(self, event=None):
        self._save_current_state()
        if self.image_loader.next_image():
            self._load_current_image()
