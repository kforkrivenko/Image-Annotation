import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox
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
        self.annotation_saver = AnnotationSaver()

        # UI элементы
        self._setup_ui()

    def _setup_ui(self):
        # Кнопки управления
        self.btn_frame = tk.Frame(self.root)
        self.btn_frame.pack(pady=10)

        self.load_btn = tk.Button(self.btn_frame, text="Load Folder",
                                  command=self._load_folder)
        self.load_btn.pack(side=tk.LEFT, padx=5)

        self.next_btn = tk.Button(self.btn_frame, text="Next Image",
                                  command=self._next_image, state=tk.DISABLED)
        self.next_btn.pack(side=tk.LEFT, padx=5)

    def _load_folder(self):
        folder_path = filedialog.askdirectory()
        if not folder_path:
            return

        self.image_loader = ImageLoader(folder_path)
        if not self.image_loader.image_files:
            messagebox.showerror("Error", "No images found in selected folder!")
            return

        self._load_next_image()

    def _load_next_image(self):
        image = self.image_loader.get_next_image()
        if image is None:
            messagebox.showinfo("Complete", "All images annotated!")
            self.next_btn.config(state=tk.DISABLED)
            return

        self.canvas_tool.display_image(image)
        self.next_btn.config(state=tk.NORMAL)

    def _next_image(self):
        if not self.image_loader:
            messagebox.showerror("Error", "No folder loaded!")
            return

        try:
            regions = self.canvas_tool.get_regions()
            if regions:
                # Получаем ПОЛНЫЙ путь к текущему изображению
                current_image_path = os.path.join(
                    self.image_loader.folder_path,
                    self.image_loader.get_current_filename()
                )
                self.annotation_saver.save_annotation(current_image_path, regions)

            self.canvas_tool.clear_canvas()
            self._load_next_image()

        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save annotation: {str(e)}")