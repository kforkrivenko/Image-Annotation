import shutil
import hashlib
from utils.errors import NoImagesError
from utils.logger import log_method
from data_processing.annotation_saver import AnnotationSaver
from data_processing.image_loader import ImageLoader
from ui.canvas import AnnotationCanvas
from tkinter import ttk, filedialog, messagebox, simpledialog
import tkinter as tk
import os
from pathlib import Path
from utils.json_manager import JsonManager, AnnotationFileManager
from utils.paths import DATA_DIR


def get_unique_folder_name(source_path: Path) -> str:
    unique_str = source_path.name
    return str(hashlib.md5(unique_str.encode()).hexdigest()[:8])


class AnnotationPopover(tk.Toplevel):
    def __init__(self, parent, app, readonly=False):
        super().__init__(parent)
        self.app = app
        self.title("Разметка датасета")
        self.geometry("1200x800")
        self.readonly = readonly

        # Блокируем главное окно
        self.grab_set()
        self.focus_set()

        # Инициализация состояния
        self.image_loader = None
        self.annotation_saver = None
        self.folder_path = None
        self.json_manager = None  # Управление hash_to_name
        self.current_blazon = None

        # Рисовка графики
        self._setup_ui()

    def _setup_ui(self):
        style = ttk.Style()
        style.configure("Popover.TFrame", background="#f5f5f5")
        style.configure("Popover.TButton", padding=6)

        style.configure('TLabel', font=('Arial', 10))
        style.configure('TEntry', padding=5)

        # Главный контейнер
        main_frame = ttk.Frame(self, style="Popover.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Левая панель
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Правая панель (кнопка дефолтной разметки)
        right_frame = ttk.Frame(main_frame, padding=10)
        right_frame.pack(side=tk.RIGHT)
        text_var = tk.StringVar()

        def on_text_change(*args):
            current_text = text_var.get()
            self.canvas.set_default_label(current_text)

        text_var.trace_add("write", on_text_change)

        self.current_blazon_label = ttk.Label(
            right_frame,
            text=f"{self.current_blazon}",
            wraplength=300,  # Ширина в пикселях, после которой будет перенос
            justify='left'  # Выравнивание текста (left/center/right)
        )
        self.current_blazon_label.pack(pady=5)

        if not self.readonly:
            ttk.Label(right_frame, text="Разметка:").pack(pady=10)
            ttk.Entry(right_frame, textvariable=text_var, width=30).pack(pady=5)

        # Canvas для изображений
        self.canvas = AnnotationCanvas(left_frame, self.image_loader, self.annotation_saver, readonly=self.readonly)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Панель управления
        control_frame = ttk.Frame(left_frame)
        control_frame.pack(fill=tk.X, pady=10)

        ttk.Button(
            control_frame,
            text="← Назад",
            style="Popover.TButton",
            command=self._prev_image
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            control_frame,
            text="Вперед →",
            style="Popover.TButton",
            command=self._next_image
        ).pack(side=tk.LEFT, padx=5)

        self.status_var = tk.StringVar()
        ttk.Label(
            control_frame,
            textvariable=self.status_var,
            style="Popover.TLabel"
        ).pack(side=tk.LEFT, padx=10)

        self.entry_var = tk.StringVar()
        self.image_entry = tk.Entry(
            control_frame,
            textvariable=self.entry_var,
            width=5
        )
        self.image_entry.pack(side=tk.LEFT, padx=5)

        self.update_button = tk.Button(
            control_frame,
            text="Перейти",
            command=self._go_to_image
        )
        self.update_button.pack(side=tk.LEFT, padx=5)

        # Кнопка закрытия
        ttk.Button(
            control_frame,
            text="Готово",
            style="Popover.TButton",
            command=self.close
        ).pack(side=tk.RIGHT, padx=5, pady=10)

    def _go_to_image(self):
        """Обновить изображение по номеру, введенному пользователем."""
        try:
            # Получаем номер из текстового поля
            index = int(self.entry_var.get()) - 1  # Номера изображений начинаются с 1, поэтому вычитаем 1
            if 0 <= index < len(self.image_loader.image_files):
                self.image_loader.current_index = index
                self._load_image('current')
                self._update_status()
            else:
                # Если введенный номер вне допустимого диапазона
                self.status_var.set("Неверный номер изображения!")
        except ValueError:
            # Если введено не число
            self.status_var.set("Введите валидный номер изображения!")

    def _copy_to_folder_and_rename(self, folder_path):
        """Копируем в защищенную папку, переименовываем с помощью хэша"""
        folder_path = Path(folder_path)

        if folder_path.exists():
            output_dir = DATA_DIR / "annotated_dataset"

            hash_name = get_unique_folder_name(folder_path)
            self.json_manager = JsonManager(
                os.path.join(output_dir, 'hash_to_name.json')
            )

            dst_path = output_dir / hash_name
            if hash_name not in self.json_manager.keys():
                shutil.copytree(folder_path, dst_path)
                self.folder_path = dst_path
                self.json_manager[hash_name] = str(folder_path)
            else:
                self.folder_path = dst_path

    def load_folder(self, path=None):
        if path:
            folder_path = Path(path)
            self.folder_path = path
        else:
            folder_path = filedialog.askdirectory(title="Выберите папку с изображениями")
        if folder_path:
            images = [
                f for f in os.listdir(folder_path)
                if f.lower().endswith(('.jpg', '.jpeg', '.png'))
            ]
            if not images:
                raise NoImagesError()

            if not path:
                self._copy_to_folder_and_rename(folder_path)
            self.image_loader = ImageLoader(self.folder_path)

            self.canvas.image_loader = self.image_loader

            self.annotation_saver = AnnotationSaver(self.folder_path)
            self.canvas.annotation_saver = self.annotation_saver
            self._load_image()
        else:
            self.destroy()

    @log_method
    def _load_image(self, direction="next"):
        output_dir = DATA_DIR / "annotated_dataset"

        if self.image_loader:
            json_manager = JsonManager(os.path.join(output_dir, 'blazons.json'))

            img = self.image_loader.get_image(direction)
            if img:
                current_image_path = self.image_loader.get_current_image_path()
                folder_path = self.image_loader.folder_path
                hash = str(folder_path).split('/')[-1]

                try:
                    self.current_blazon = json_manager[hash][current_image_path]
                except Exception:
                    self.current_blazon = ""

                self.current_blazon_label.config(
                    text=f"{self.current_blazon}"
                )

                self.canvas.display_image(img, current_image_path)
                self._load_existing_annotations(current_image_path)
                self._update_status()

    def _load_existing_annotations(self, current_image_path):
        annotations = self.annotation_saver.get_annotations(current_image_path)

        for annotation in annotations:
            self.canvas.add_annotation(annotation)

    def _prev_image(self):
        self._load_image("prev")

    def _next_image(self):
        self._load_image("next")

    def _update_status(self):
        if self.image_loader:
            self.status_var.set(
                f"Изображение {self.image_loader.current_index + 1}/{len(self.image_loader.image_files)}"
            )

    def close(self):
        self.destroy()
        self.app.get_annotated_datasets()