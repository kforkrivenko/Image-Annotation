import tkinter as tk
from tkinter import simpledialog
from PIL import Image, ImageTk


class CanvasTool:
    def __init__(self, parent):
        self.canvas = tk.Canvas(parent, width=800, height=600, cursor="cross")
        self.canvas.pack()

        self.image_on_canvas = None
        self.rectangles = []
        self.current_rect = None
        self.start_x = None
        self.start_y = None

        # Привязка событий
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

    def display_image(self, image):
        """Отображение изображения на Canvas"""
        self.clear_canvas()

        # Масштабирование изображения
        img_width, img_height = image.size
        ratio = min(800 / img_width, 600 / img_height)
        new_size = (int(img_width * ratio), int(img_height * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

        # Отображение
        self.tk_image = ImageTk.PhotoImage(image)
        self.image_on_canvas = self.canvas.create_image(
            0, 0, anchor=tk.NW, image=self.tk_image
        )

    def _on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.current_rect = self.canvas.create_rectangle(
            self.start_x, self.start_y,
            self.start_x, self.start_y,
            outline="red", width=2
        )

    def _on_drag(self, event):
        if self.current_rect:
            self.canvas.coords(
                self.current_rect,
                self.start_x, self.start_y,
                event.x, event.y
            )

    def _on_release(self, event):
        if not self.current_rect:
            return

        # Получаем координаты
        coords = self.canvas.coords(self.current_rect)

        # Запрашиваем подпись
        label = simpledialog.askstring(
            "Label", "Enter object label:",
            parent=self.canvas
        )

        if label:
            self.rectangles.append({
                "coords": coords,
                "label": label
            })

            # Добавляем текст на Canvas
            x_center = (coords[0] + coords[2]) / 2
            y_center = (coords[1] + coords[3]) / 2
            self.canvas.create_text(
                x_center, y_center,
                text=label, fill="red",
                font=("Arial", 10, "bold")
            )
        else:
            self.canvas.delete(self.current_rect)

        self.current_rect = None

    def get_regions(self):
        return self.rectangles

    def clear_canvas(self):
        self.canvas.delete("all")
        self.rectangles = []