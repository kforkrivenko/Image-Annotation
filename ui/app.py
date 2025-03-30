import os
import tkinter as tk
from tkinter import filedialog, messagebox
from data_processing.image_loader import ImageLoader
from data_processing.annotation_saver import AnnotationSaver
from ui.canvas import AnnotationCanvas
from ui.widgets import ControlPanel
from models.annotation import Annotation


class ImageAnnotationApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Image Annotation Tool")
        self._setup_ui()
        self._initialize_state()

    def _setup_ui(self):
        self.canvas = AnnotationCanvas(self.root)
        self.canvas.pack()

        self.control_panel = ControlPanel(self.root)
        self.control_panel.pack(pady=10)

        self._bind_events()

    def _initialize_state(self):
        self.image_loader = None
        self.annotation_saver = None
        self.current_image = None
        self.current_image_path = None

    def _bind_events(self):
        self.control_panel.load_btn.config(command=self._load_folder)
        self.control_panel.prev_btn.config(command=self._prev_image)
        self.control_panel.next_btn.config(command=self._next_image)
        self.control_panel.close_btn.config(command=self._close_image)

    def _load_folder(self):
        folder_path = filedialog.askdirectory()
        if not folder_path:
            return

        self.image_loader = ImageLoader(folder_path)
        self.annotation_saver = AnnotationSaver(folder_path)

        if not self.image_loader.image_files:
            messagebox.showerror("Error", "No images found!")
            return

        self._load_image()
        self._update_ui()

    def _load_image(self):
        self.current_image = self.image_loader.get_image("next")
        self.current_image_path = self.image_loader.get_current_image_path()

        if self.current_image is None:
            messagebox.showinfo("Complete", "All images annotated!")
            return

        self.canvas.display_image(self.current_image, self.current_image_path)
        self._load_existing_annotations()

    def _load_existing_annotations(self):
        annotations = self.annotation_saver.get_annotations(self.current_image_path)
        for ann in annotations:
            self.canvas.add_annotation(ann)

    def _prev_image(self):
        self._save_current_annotations()
        self.current_image = self.image_loader.get_image("prev")
        self.current_image_path = self.image_loader.get_current_image_path()
        self.canvas.clear()  # Очищаем canvas перед загрузкой нового изображения
        self._update_image_display()

    def _next_image(self):
        self._save_current_annotations()
        self.current_image = self.image_loader.get_image("next")
        self.current_image_path = self.image_loader.get_current_image_path()
        self.canvas.clear()  # Очищаем canvas перед загрузкой нового изображения
        self._update_image_display()

    def _close_image(self):
        self.image_loader.current_index = -1
        self._save_current_annotations()
        self.canvas.clear()
        self._update_ui()
        self.control_panel.status_var.set("")

    def _save_current_annotations(self):
        try:
            if self.current_image_path and hasattr(self, 'annotation_saver'):
                annotations = self.canvas.get_annotations()
                full_image_path = os.path.join(
                    self.image_loader.folder_path,
                    self.current_image_path
                )
                if os.path.exists(full_image_path):
                    self.annotation_saver.save_annotations(full_image_path, annotations)
                else:
                    print(f"Warning: Image file not found: {full_image_path}")
        except Exception as e:
            print(f"Error saving annotations: {str(e)}")

    def _update_image_display(self):
        if self.current_image is not None and self.current_image_path is not None:
            self.canvas.clear()
            self.canvas.display_image(self.current_image, self.current_image_path)
            self._load_existing_annotations()
        self._update_ui()

    def _update_ui(self):
        if self.image_loader:
            self.control_panel.update_state(
                current_index=self.image_loader.current_index,
                total_images=len(self.image_loader.image_files),
                has_image=self.current_image is not None
            )

    def run(self):
        self.root.mainloop()
