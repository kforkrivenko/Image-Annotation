import tkinter as tk
from tkinter import filedialog, messagebox
from data_processing.image_loader import ImageLoader
from data_processing.annotation_saver import AnnotationSaver
from ui.canvas_tools import CanvasTool
import os


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Annotation Tool")

        # Инициализация компонентов
        self.canvas_tool = CanvasTool(self.root)
        self.image_loader = None
        self.annotation_saver = None

        # UI элементы
        self._setup_ui()

        # Текущая картинка
        self.image = None
        self.image_path = None

    def _setup_ui(self):
        # Кнопки управления
        self.btn_frame = tk.Frame(self.root)
        self.btn_frame.pack(pady=10)

        self.load_btn = tk.Button(
            self.btn_frame,
            text="Load Folder",
            command=self._load_folder
        )
        self.load_btn.pack(side=tk.LEFT, padx=5)

        self.prev_btn = tk.Button(
            self.btn_frame,
            text="Prev Image",
            command=self._prev_image,
            state=tk.DISABLED
        )
        self.prev_btn.pack(side=tk.LEFT, padx=5)

        self.next_btn = tk.Button(
            self.btn_frame,
            text="Next Image",
            command=self._next_image,
            state=tk.DISABLED
        )
        self.next_btn.pack(side=tk.LEFT, padx=5)

        self.btn_frame_close = tk.Frame(self.root)
        self.btn_frame_close.pack(pady=10)

        self.close_image = tk.Button(
            self.btn_frame,
            text="Close",
            command=self._clear_canvas,
            state=tk.NORMAL
        )

        self.close_image.pack(side=tk.RIGHT, padx=5)

        nav_frame = tk.Frame(self.root)
        nav_frame.pack(pady=5)

        self.progress_var = tk.StringVar()
        tk.Label(
            nav_frame,
            textvariable=self.progress_var
        ).pack(side=tk.LEFT, padx=10)

    def _clear_canvas(self):
        self.canvas_tool.clear_canvas()
        self.prev_btn.config(state=tk.DISABLED)
        self.next_btn.config(state=tk.DISABLED)
        self.canvas_tool.canvas.config(cursor='')

    def _load_folder(self):
        folder_path = filedialog.askdirectory()
        if not folder_path:
            return

        self.image_loader = ImageLoader(folder_path)
        self.annotation_saver = AnnotationSaver(folder_path)
        self.folder_path = folder_path
        if not self.image_loader.image_files:
            messagebox.showerror("Error", "No images found in selected folder!")
            return

        self._load_image(how='next')
        self._draw_current_image()
        self._update_button_state()
        current_annotations_from_file = self.annotation_saver.get_annotation_from_file(
            self.image_path
        )
        self._draw_annotations_from_file(current_annotations_from_file)

    def _load_image(self, how):
        self.image = self.image_loader.get_image(how=how)
        self.image_path = self.image_loader.get_current_image_path()

        if self.image is None:
            messagebox.showinfo("Complete", "All images annotated!")

        self._update_button_state()

    def _draw_current_image(self):
        if self.image is None:
            return
        self.canvas_tool.display_image(self.image, self.image_path)

    def _draw_annotations_from_file(self, annotations_from_file):
        if not annotations_from_file:
            return
        for annotation in annotations_from_file:
            coords = annotation['coords']
            label = annotation['text']
            self.canvas_tool.add_rectangle(
                coords,
                label
            )

            x_center = (coords[0] + coords[2]) / 2
            y_center = (coords[1] + coords[3]) / 2
            self.canvas_tool.canvas.create_text(
                x_center, y_center,
                text=label, fill="red",
                font=("Arial", 10, "bold")
            )

    def _next_image(self):
        if not self.image_loader:
            messagebox.showerror("Error", "No folder loaded!")
            return

        self._update_button_state()

        current_annotations = self.canvas_tool.get_annotations()
        current_image_path = os.path.join(
            self.image_loader.folder_path,
            self.image_loader.get_current_image_path()
        )
        #  Пытаемся подгрузить аннотации
        current_annotations_from_file = self.annotation_saver.get_annotation_from_file(current_image_path)
        self._load_image("next")

        next_image_path = os.path.join(
            self.image_loader.folder_path,
            self.image_loader.get_current_image_path()
        )
        next_annotations_from_file = self.annotation_saver.get_annotation_from_file(next_image_path)
        #  Убираем предыдущие творения
        self.canvas_tool.clear_canvas()
        #  Рисуем Картинку
        self._draw_current_image()
        #  Отображаем их
        self._draw_annotations_from_file(next_annotations_from_file)
        #  Сохраняем аннотации

        print('current_annotations', current_annotations)
        print('current_annotations_from_file', current_annotations_from_file)

        try:
            if current_annotations:
                self.annotation_saver.save_annotation(
                    current_image_path,
                    current_annotations + current_annotations_from_file
                )
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save annotation: {str(e)}")

    def _prev_image(self):
        if not self.image_loader:
            messagebox.showerror("Error", "No folder loaded!")
            return

        self._update_button_state()

        current_annotations = self.canvas_tool.get_annotations()
        current_image_path = os.path.join(
            self.image_loader.folder_path,
            self.image_loader.get_current_image_path()
        )
        #  Пытаемся подгрузить аннотации
        current_annotations_from_file = self.annotation_saver.get_annotation_from_file(current_image_path)
        self._load_image("prev")

        prev_image_path = os.path.join(
            self.image_loader.folder_path,
            self.image_loader.get_current_image_path()
        )
        prev_annotations_from_file = self.annotation_saver.get_annotation_from_file(prev_image_path)
        #  Убираем предыдущие творения
        self.canvas_tool.clear_canvas()
        #  Рисуем Картинку
        self._draw_current_image()
        #  Отображаем их
        self._draw_annotations_from_file(prev_annotations_from_file)

        try:
            #  Сохраняем аннотации
            if current_annotations:
                self.annotation_saver.save_annotation(
                    current_image_path,
                    current_annotations + current_annotations_from_file
                )
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save annotation: {str(e)}")

    def _update_button_state(self):
        if self.image_loader.current_index > 0:
            self.prev_btn.config(state=tk.NORMAL)
        else:
            self.prev_btn.config(state=tk.DISABLED)

        if self.image_loader.current_index < len(self.image_loader.image_files) - 1:
            self.next_btn.config(state=tk.NORMAL)
        else:
            self.next_btn.config(state=tk.DISABLED)

        self.progress_var.set(
            f"{self.image_loader.current_index + 1}/{len(self.image_loader.image_files)}"
        )
