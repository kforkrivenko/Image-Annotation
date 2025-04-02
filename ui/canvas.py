import tkinter as tk
from tkinter import simpledialog
from PIL import Image, ImageTk
from models.annotation import Annotation
from utils.logger import log_method


class AnnotationCanvas(tk.Canvas):
    @log_method
    def __init__(self, parent, image_loader, annotation_saver, **kwargs):
        super().__init__(parent, width=800, height=600, **kwargs)
        self.annotation_saver = annotation_saver
        self.image_loader = image_loader
        self._setup_canvas()

        self.current_rect = None
        self.image_on_canvas = None
        self.tk_image = None
        self.image_path = None
        self.annotations = []
        self.ratio = 1.0
        self.default_label = None

    def _setup_canvas(self):
        self.configure(bg="white", cursor="cross")
        self.current_rect = None
        self.annotations = []
        self.ratio = 1.0

        # Привязка событий
        self._bind_events()

    def _bind_events(self):
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)

        # Правая кнопка - контекстное меню
        self.bind("<ButtonPress-3>", self._on_right_click)  # Windows/Linux
        self.bind("<ButtonPress-2>", self._on_right_click)  # MacOS

    def _on_right_click(self, event):
        """Обработчик правой кнопки мыши"""
        # Создаем контекстное меню
        menu = tk.Menu(self, tearoff=0)

        # Добавляем команды
        menu.add_command(
            label="Удалить аннотацию",
            command=lambda: self._delete_annotation_near(event.x, event.y)
        )
        menu.add_command(
            label="Изменить метку",
            command=lambda: self._edit_annotation_label(event.x, event.y)
        )

        # Показываем меню
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _delete_annotation_near(self, x, y):
        """Удаляет ближайшую аннотацию"""
        for i, ann in enumerate(self.annotations):
            x1, y1, x2, y2 = ann.coords
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.delete(ann.rect)
                self.delete(ann.text_id)
                self.annotations.pop(i)

                self.configure(bg=self.cget("bg"))
                self._delete_annotation_from_file(ann)

                self._redraw_all_annotations()
                break

    def _delete_annotation_from_file(self, annotation):
        folder_path, image_path = self.image_loader.folder_path, self.image_loader.get_current_image_path()
        self.annotation_saver.delete_annotation_from_file(image_path, annotation)

    def _add_annotation_to_file(self, annotation):
        folder_path, image_path = self.image_loader.folder_path, self.image_loader.get_current_image_path()
        self.annotation_saver.add_annotation_to_file(image_path, annotation)

    def _edit_annotation_label(self, x, y):
        """Изменяет метку аннотации"""
        for ann in self.annotations:
            x1, y1, x2, y2 = ann.coords
            if x1 <= x <= x2 and y1 <= y <= y2:
                new_label = simpledialog.askstring("Изменить метку",
                                                   "Новая метка:",
                                                   initialvalue=ann.text)
                if new_label:
                    ann.text = new_label
                    self._update_annotation_display(ann)

                self._redraw_all_annotations()
                break

    def _update_annotation_display(self, annotation):
        """Обновляет визуальное отображение аннотации на Canvas"""
        # 1. Удаляем старые элементы
        self.delete(annotation.rect)  # Удаляем прямоугольник
        if hasattr(annotation, 'text_id'):
            self.delete(annotation.text_id)  # Удаляем старую текстовую метку
            self._delete_annotation_from_file(annotation)

        # 2. Пересчитываем координаты с учетом текущего масштаба
        ratio = self.ratio if hasattr(self, 'ratio') else 1.0
        coords = [
            annotation.coords[0] * ratio,
            annotation.coords[1] * ratio,
            annotation.coords[2] * ratio,
            annotation.coords[3] * ratio
        ]

        # 3. Перерисовываем прямоугольник
        annotation.rect = self.create_rectangle(
            *coords,
            outline='red',
            width=2
        )

        # 4. Перерисовываем текстовую метку
        x_center = (coords[0] + coords[2]) / 2
        y_center = (coords[1] + coords[3]) / 2

        annotation.text_id = self.create_text(
            x_center, y_center,
            text=annotation.text,
            fill='red',
            font=('Arial', 10, 'bold')
        )

        # 5. Обновляем ссылки в списке аннотаций
        for i, ann in enumerate(self.annotations):
            if ann == annotation:
                self.annotations[i] = annotation
                break

        self._add_annotation_to_file(annotation)

    def display_image(self, image, image_path):
        self.clear()
        self._draw_image(image)
        self._draw_image_path(image_path)

    def _draw_image(self, image):
        img_width, img_height = image.size
        self.ratio = min(800 / img_width, 600 / img_height)
        new_size = (int(img_width * self.ratio), int(img_height * self.ratio))
        resized_image = image.resize(new_size, Image.Resampling.LANCZOS)

        self.tk_image = ImageTk.PhotoImage(resized_image)
        self.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

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
        if self.default_label is not None:
            label = self.default_label
        else:
            label = simpledialog.askstring("Label", "Enter object label:", parent=self)

        if label:
            self._create_annotation(coords, label, self.current_rect)
        else:
            self.delete(self.current_rect)

        self.current_rect = None

    def _create_annotation(self, coords, label, rect):
        x_center = (coords[0] + coords[2]) / 2
        y_center = (coords[1] + coords[3]) / 2

        text_id = self.create_text(
            x_center, y_center,
            text=label, fill="red",
            font=("Arial", 10, "bold")
        )

        annotation = Annotation(
            coords=coords,
            text=label,
            ratio=self.ratio,
            rect=rect,
            text_id=text_id
        )
        self.annotations.append(annotation)
        self._add_annotation_to_file(annotation)

    def add_annotation(self, annotation):
        if annotation in self.annotations:
            return

        coords, label, rect = annotation.coords, annotation.text, annotation.rect

        rect = self.create_rectangle(
            *coords,
            outline="red", width=2
        )

        x_center = (coords[0] + coords[2]) / 2
        y_center = (coords[1] + coords[3]) / 2

        text_id = self.create_text(
            x_center, y_center,
            text=label, fill="red",
            font=("Arial", 10, "bold")
        )

        _ = Annotation(
            coords=coords,
            text=label,
            ratio=self.ratio,
            rect=rect,
            text_id=text_id
        )

        self.annotations.append(annotation)

    def get_annotations(self):
        return self.annotations

    def clear(self):
        """Полностью очищает canvas и сбрасывает все аннотации"""
        self.delete("all")  # Удаляем все элементы с canvas
        self.image_on_canvas = None
        self.tk_image = None
        self.image_path = None
        self.annotations = []  # Очищаем список аннотаций
        self.ratio = 1.0
        self.current_rect = None
        self.configure(cursor="arrow")

    def _redraw_all_annotations(self):
        """Полная перерисовка всех элементов"""
        # 1. Сохраняем текущее изображение
        current_image = self.tk_image
        current_image_path = self.image_path

        # 2. Полностью очищаем Canvas
        self.delete("all")

        # 3. Восстанавливаем изображение (если было)
        if current_image:
            self.image_on_canvas = self.create_image(0, 0, anchor=tk.NW, image=current_image)
            self._draw_image_path(current_image_path)

        # 4. Перерисовываем все аннотации
        for ann in self.annotations:
            ann.rect = self.create_rectangle(*ann.coords, outline="red", width=2)
            x_center = (ann.coords[0] + ann.coords[2]) / 2
            y_center = (ann.coords[1] + ann.coords[3]) / 2
            ann.text_id = self.create_text(x_center, y_center,
                                           text=ann.text, fill="red",
                                           font=("Arial", 10, "bold"))

    def set_default_label(self, label):
        if label.strip() != '':
            self.default_label = label.strip()
        else:
            self.default_label = None
