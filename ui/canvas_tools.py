import tkinter as tk
from tkinter import simpledialog
from PIL import Image, ImageTk
from logger.logger import log_method
import json


class CanvasTool:
    @log_method
    def __init__(self, parent, ):
        self.canvas = tk.Canvas(parent, width=800, height=600, cursor="arrow", highlightthickness=0, bd=0)
        self.canvas.pack()

        self.image_on_canvas = None
        self.text_on_canvas = None
        self.rectangles = []
        self.current_rect = None
        self.selected_rect = None
        self.start_x = None
        self.start_y = None
        self.tk_image = None
        self.ratio = None

        # Привязка событий
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

    @log_method
    def display_image(self, image, image_path):
        """Отображение изображения на Canvas"""
        self.clear_canvas()
        self.canvas.config(cursor='cross')

        # # Масштабирование изображения
        img_width, img_height = image.size
        ratio = min(800 / img_width, 600 / img_height)
        new_size = (int(img_width * ratio), int(img_height * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

        self.ratio = ratio

        # Отображение
        self.tk_image = ImageTk.PhotoImage(image)
        self.image_on_canvas = self.canvas.create_image(
            0, 0, anchor=tk.NW, image=self.tk_image
        )

        # Отображение пути к изображению поверх картинки
        self.text_on_canvas = self.canvas.create_text(
            10, 10,  # Позиция текста (x, y)
            anchor=tk.NW,  # Выравнивание по северо-западу (верхний левый угол)
            text=image_path,  # Текст для отображения
            fill="red",  # Цвет текста
            font=("Arial", 15),  # Шрифт и размер
            width=img_width - 20  # Максимальная ширина текста (ширина изображения минус отступы)
        )

    @log_method
    def _on_press(self, event):
        if not self.image_on_canvas:
            return
        self.start_x = event.x
        self.start_y = event.y
        self.current_rect = {
            'rect': self.canvas.create_rectangle(
                event.x, event.y, event.x, event.y,
                outline='red', width=2
            ),
            'text': None,
            'coords': [event.x, event.y, event.x, event.y],
            'ratio': self.ratio
        }

    @log_method
    def _on_drag(self, event):
        if self.current_rect:
            self.canvas.coords(
                self.current_rect['rect'],
                self.start_x, self.start_y,
                event.x, event.y
            )
            self.current_rect['coords'] = [self.start_x, self.start_y, event.x, event.y]

    @log_method
    def _on_release(self, _):
        if not self.current_rect:
            return

        # Получаем координаты
        coords = self.canvas.coords(self.current_rect['rect'])

        # Запрашиваем подпись
        label = simpledialog.askstring(
            "Label", "Enter object label:",
            parent=self.canvas
        )

        if label:
            rect_data = {
                'rect': self.current_rect['rect'],
                'text': label,
                'coords': self.current_rect['coords'],
                'ratio': self.ratio
            }
            self.rectangles.append(rect_data)

            # Добавляем текст на Canvas
            x_center = (coords[0] + coords[2]) / 2
            y_center = (coords[1] + coords[3]) / 2
            self.canvas.create_text(
                x_center, y_center,
                text=label, fill="red",
                font=("Arial", 10, "bold")
            )
            self.canvas.config(cursor="")
        else:
            self.canvas.delete(self.current_rect['rect'])

        self.current_rect = None

    @log_method
    def select_rectangle(self, event):
        """Выбор прямоугольника по клику"""
        if self.canvas.cget("cursor") == "cross":
            return

        # Поиск прямоугольника под курсором
        clicked_items = self.canvas.find_overlapping(
            event.x - 1, event.y - 1, event.x + 1, event.y + 1
        )

        self.deselect_all()

        for rect in self.rectangles:
            if rect['rect'] in clicked_items or rect['text_id'] in clicked_items:
                # Выделение прямоугольника
                self.canvas.itemconfig(rect['rect'], outline='red', width=3)
                self.selected_rect = rect
                break

    @log_method
    def deselect_all(self):
        """Снятие выделения со всех прямоугольников"""
        if self.selected_rect:
            self.canvas.itemconfig(self.selected_rect['rect'], outline='blue', width=2)
            self.selected_rect = None

    @log_method
    def save_to_file(self):
        """Сохранение данных в файл"""
        data_to_save = []
        for rect in self.rectangles:
            data_to_save.append({
                'image': rect['image'],
                'coords': rect['coords'],
                'text': rect['text']
            })

        with open('rectangles.json', 'w') as f:
            json.dump(data_to_save, f)

        print("Данные сохранены в rectangles.json")

    @log_method
    def get_annotations(self):
        return self.rectangles

    @log_method
    def clear_canvas(self):
        self.image_on_canvas = None
        self.canvas.delete("all")
        self.rectangles = []

    @log_method
    def delete_canvas(self):
        self.clear_canvas()
        self.canvas.destroy()

    @log_method
    def add_rectangle(self, coords, text):
        rect = {
            'rect': self.canvas.create_rectangle(
                *coords,
                outline='red', width=2
            ),
            'text': text,
            'coords': [*coords],
            'ratio': self.ratio
        }

        self.rectangles.append(rect)

