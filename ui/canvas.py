import tkinter as tk
from tkinter import simpledialog
from PIL import Image, ImageTk
from models.annotation import Annotation
from utils.logger import log_method


class AnnotationCanvas(tk.Canvas):
    @log_method
    def __init__(self, parent, **kwargs):
        super().__init__(parent, width=800, height=600, **kwargs)
        self._setup_canvas()

        self.current_rect = None
        self.image_on_canvas = None
        self.tk_image = None
        self.annotations = []
        self.ratio = 1.0

    def _setup_canvas(self):
        self.configure(
            cursor="arrow",
            highlightthickness=0,
            bd=0
        )
        self.image_on_canvas = None
        self.tk_image = None
        self.ratio = 1.0
        self.annotations = []
        self._bind_events()

    def _bind_events(self):
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)

    def display_image(self, image, image_path):
        self.clear()  # Сначала очищаем canvas
        self.configure(cursor="cross")
        self._draw_image(image)
        self._draw_image_path(image_path)

    def _draw_image(self, image):
        img_width, img_height = image.size
        self.ratio = min(800 / img_width, 600 / img_height)
        new_size = (int(img_width * self.ratio), int(img_height * self.ratio))
        resized_image = image.resize(new_size, Image.Resampling.LANCZOS)

        self.tk_image = ImageTk.PhotoImage(resized_image)
        self.image_on_canvas = self.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

    def _draw_image_path(self, image_path):
        self.create_text(
            10, 10,
            anchor=tk.NW,
            text=image_path,
            fill="red",
            font=("Arial", 15)
        )

    def _on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.current_rect = self.create_rectangle(
            event.x, event.y, event.x, event.y,
            outline="red", width=2
        )

    def _on_drag(self, event):
        if self.current_rect:
            self.coords(
                self.current_rect,
                self.start_x, self.start_y,
                event.x, event.y
            )

    def _on_release(self, event):
        if not self.current_rect:
            return

        coords = self.coords(self.current_rect)
        label = simpledialog.askstring("Label", "Enter object label:", parent=self)

        if label:
            self._create_annotation(coords, label)
        else:
            self.delete(self.current_rect)

        self.current_rect = None

    def _create_annotation(self, coords, label):
        x_center = (coords[0] + coords[2]) / 2
        y_center = (coords[1] + coords[3]) / 2

        self.create_text(
            x_center, y_center,
            text=label, fill="red",
            font=("Arial", 10, "bold")
        )

        annotation = Annotation(
            coords=coords,
            text=label,
            ratio=self.ratio
        )
        self.annotations.append(annotation)

    def add_annotation(self, annotation):
        rect = self.create_rectangle(
            *annotation.coords,
            outline="red", width=2
        )

        x_center = (annotation.coords[0] + annotation.coords[2]) / 2
        y_center = (annotation.coords[1] + annotation.coords[3]) / 2

        self.create_text(
            x_center, y_center,
            text=annotation.text, fill="red",
            font=("Arial", 10, "bold")
        )

        self.annotations.append(annotation)

    def get_annotations(self):
        return self.annotations

    def clear(self):
        """Полностью очищает canvas и сбрасывает все аннотации"""
        self.delete("all")  # Удаляем все элементы с canvas
        self.image_on_canvas = None
        self.tk_image = None
        self.annotations = []  # Очищаем список аннотаций
        self.ratio = 1.0
        self.current_rect = None
        self.configure(cursor="arrow")
