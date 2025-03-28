import tkinter as tk
from tkinter import simpledialog
from PIL import Image, ImageTk
from logger.logger import log_method


class CanvasTool:
    def __init__(self, parent):
        self.parent = parent
        self.canvas = tk.Canvas(parent, width=800, height=600, cursor="cross")
        self.canvas.pack()

        # Данные аннотаций
        self.rectangles = []
        self.selected_annotations = set()
        self.highlight_color = "#4A89DC"

        # Привязка событий
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Control-Button-1>", self._on_canvas_click)
        self.canvas.bind("<Shift-Button-1>", self._on_canvas_click)
        parent.bind("<Control-a>", lambda e: self._select_all())
        parent.bind("<Escape>", lambda e: self.clear_selections())

        self.current_rect = None
        self.tk_image = None
        self.image_on_canvas = None

    def display_image(self, image):
        """Отображает изображение на Canvas"""
        self.clear_canvas()
        img_width, img_height = image.size
        ratio = min(800 / img_width, 600 / img_height)
        new_size = (int(img_width * ratio), int(img_height * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

        self.tk_image = ImageTk.PhotoImage(image)
        self.image_on_canvas = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

    @log_method
    def _on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.current_rect = self.canvas.create_rectangle(
            self.start_x, self.start_y,
            self.start_x, self.start_y,
            outline="red", width=2
        )

    @log_method
    def _on_drag(self, event):
        if self.current_rect:
            self.canvas.coords(
                self.current_rect,
                self.start_x, self.start_y,
                event.x, event.y
            )

    @log_method
    def _on_release(self, event):
        if not self.current_rect:
            return

        coords = self.canvas.coords(self.current_rect)
        label = self.ask_annotation(coords)

        if label:
            rect_id = self.current_rect
            self.rectangles.append({
                "coords": coords,
                "label": label,
                "rect_id": rect_id
            })
            self._update_annotation_text(len(self.rectangles) - 1)
        else:
            self.canvas.delete(self.current_rect)

        self.current_rect = None

    def _on_canvas_click(self, event):
        """Обработка кликов для выделения аннотаций"""
        # Координаты клика с небольшим допуском
        x, y = event.x, event.y
        tolerance = 5

        # Ищем все аннотации в области клика
        clicked_annotations = []
        for i, ann in enumerate(self.rectangles):
            x1, y1, x2, y2 = ann["coords"]
            if (x1 - tolerance <= x <= x2 + tolerance and
                    y1 - tolerance <= y <= y2 + tolerance):
                clicked_annotations.append(i)

        # Обрабатываем модификаторы
        ctrl_pressed = (event.state & 0x0004) != 0  # Ctrl
        shift_pressed = (event.state & 0x0001) != 0  # Shift

        if not clicked_annotations:
            # Клик мимо аннотаций - снимаем выделение
            if not (ctrl_pressed or shift_pressed):
                self.clear_selections()
            return

        # Берем последнюю (визуально верхнюю) аннотацию
        target_idx = clicked_annotations[-1]

        if shift_pressed and self.selected_annotations:
            # Выделение диапазона
            first_idx = min(self.selected_annotations)
            last_idx = max(self.selected_annotations)
            for i in range(min(first_idx, target_idx), max(last_idx, target_idx) + 1):
                if i < len(self.rectangles):
                    self._select_annotation(i)
        elif ctrl_pressed:
            # Добавляем/убираем из выделения
            self.toggle_annotation_selection(target_idx)
        else:
            # Одиночное выделение
            self.clear_selections()
            self._select_annotation(target_idx)

    def _select_annotation(self, ann_index):
        """Выделяет аннотацию с анимацией"""
        if 0 <= ann_index < len(self.rectangles):
            ann = self.rectangles[ann_index]

            # Анимация выделения
            for _ in range(2):
                self.canvas.itemconfig(
                    ann["rect_id"],
                    outline="yellow",
                    width=4,
                    dash=(3, 3)
                )
                self.canvas.update()
                self.parent.after(100)

            self.canvas.itemconfig(
                ann["rect_id"],
                outline=self.highlight_color,
                width=3,
                dash=()
            )
            self.selected_annotations.add(ann_index)

    def toggle_annotation_selection(self, ann_index):
        """Переключает выделение аннотации"""
        if ann_index in self.selected_annotations:
            self._deselect_annotation(ann_index)
        else:
            self._select_annotation(ann_index)

    def _deselect_annotation(self, ann_index):
        if 0 <= ann_index < len(self.rectangles):
            ann = self.rectangles[ann_index]
            self.canvas.itemconfig(ann["rect_id"], outline="red", width=2)
            self.selected_annotations.discard(ann_index)

    def clear_selections(self):
        for idx in list(self.selected_annotations):
            self._deselect_annotation(idx)

    def _select_all(self):
        for i in range(len(self.rectangles)):
            self._select_annotation(i)

    def _update_annotation_text(self, ann_index):
        if 0 <= ann_index < len(self.rectangles):
            ann = self.rectangles[ann_index]
            self.canvas.delete(f"text_{ann['label']}")
            coords = ann["coords"]
            x_center = (coords[0] + coords[2]) / 2
            y_center = (coords[1] + coords[3]) / 2
            self.canvas.create_text(
                x_center, y_center,
                text=ann["label"],
                fill="red",
                font=("Arial", 10, "bold"),
                tags=("annotation", f"text_{ann['label']}")
            )

    def delete_selected(self):
        for idx in sorted(self.selected_annotations, reverse=True):
            ann = self.rectangles[idx]
            self.canvas.delete(ann["rect_id"])
            self.canvas.delete(f"text_{ann['label']}")
            self.rectangles.pop(idx)
        self.selected_annotations = set()

    def edit_selected(self):
        if not self.selected_annotations:
            return

        first_idx = next(iter(self.selected_annotations))
        coords = self.rectangles[first_idx]["coords"]
        new_label = self.ask_annotation(coords)

        if new_label:
            for idx in self.selected_annotations:
                self.rectangles[idx]["label"] = new_label
                self._update_annotation_text(idx)

    def ask_annotation(self, coords):
        dialog = tk.Toplevel(self.parent)
        dialog.title("Введите аннотацию")

        tk.Label(dialog, text="Метка:").pack()
        entry = tk.Entry(dialog, width=30)
        entry.pack(pady=5)
        entry.focus_set()

        result = []

        def on_ok():
            result.append(entry.get())
            dialog.destroy()

        tk.Button(dialog, text="OK", command=on_ok).pack()
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.wait_window()

        return result[0] if result else None

    def clear_canvas(self):
        self.canvas.delete("all")
        self.rectangles = []
        self.selected_annotations = set()

    def get_regions(self):
        return [{
            "coords": r["coords"],
            "label": r["label"]
        } for r in self.rectangles]

    def draw_annotation(self, annotation, is_selected=False):
        coords = annotation["coords"]
        label = annotation["label"]

        rect_id = self.canvas.create_rectangle(
            *coords,
            outline=self.highlight_color if is_selected else "red",
            width=3 if is_selected else 2,
            tags=("annotation",)
        )

        x_center = (coords[0] + coords[2]) / 2
        y_center = (coords[1] + coords[3]) / 2

        self.canvas.create_text(
            x_center, y_center,
            text=label,
            fill="red",
            font=("Arial", 10, "bold"),
            tags=("annotation", f"text_{label}")
        )

        self.rectangles.append({
            "coords": coords,
            "label": label,
            "rect_id": rect_id
        })

        if is_selected:
            self.selected_annotations.add(len(self.rectangles) - 1)