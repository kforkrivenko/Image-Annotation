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
import tempfile
import zipfile


def get_unique_folder_name(source_path: Path) -> str:
    unique_str = source_path.name
    return str(hashlib.md5(unique_str.encode()).hexdigest()[:8])


class AnnotationPopover(tk.Toplevel):
    def __init__(self, parent, app, readonly=False, annotated_path=None):
        super().__init__(parent)
        self.app = app
        self.title("Разметка датасета")
        self.geometry("1200x800")
        self.readonly = readonly
        self.annotated_path = annotated_path

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

        self.prev_button = ttk.Button(
            control_frame,
            text="← Назад",
            style="Popover.TButton",
            command=self._prev_image
        )
        self.prev_button.pack(side=tk.LEFT, padx=5)

        self.next_button = ttk.Button(
            control_frame,
            text="Вперед →",
            style="Popover.TButton",
            command=self._next_image
        )
        self.next_button.pack(side=tk.LEFT, padx=5)

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

    def _copy_to_folder_and_rename(self, folder_path, is_zip=False):
        """Копируем в защищенную папку, переименовываем с помощью хэша"""
        import json
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

                if is_zip:
                    json_files = list(folder_path.glob("*.json"))
                    if json_files:
                        annotations_path = json_files[0]  # ← путь к первому JSON-файлу
                    else:
                        raise FileNotFoundError("JSON файл не найден в распакованной папке.")

                    annotations_manager = JsonManager(output_dir / 'annotations.json')
                    annotations_file = Path(folder_path) / annotations_path
                    with open(annotations_file, 'r', encoding='utf-8') as f:
                        new_annotations = json.load(f)
                    # new_annotations: {image_name: [anns]}
                    for image_name, anns in new_annotations.items():
                        annotations_manager.data.setdefault(str(dst_path), {}).setdefault(image_name, []).extend(anns)
                    annotations_manager.save()

                    print(annotations_manager.data)

            else:
                self.folder_path = dst_path

    def load_folder(self, path=None, is_zip=False):
        if path:
            folder_path = Path(path)
            self.folder_path = path

            images = [
                f for f in os.listdir(folder_path)
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))
            ]

            if not images:
                self.destroy()
                raise NoImagesError()
        else:
            if is_zip == False:
                folder_path = filedialog.askdirectory(title="Выберите папку с изображениями")

                if not folder_path:
                    self.destroy()
                    return

                images = [
                    f for f in os.listdir(folder_path)
                    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))
                ]

                if not images:
                    self.destroy()
                    raise NoImagesError()
            else:
                zip_path = filedialog.askopenfilename(
                    title="Выберите архив с изображениями",
                    filetypes=(("Архивы", "*.zip"),)
                )

                if not zip_path:
                    self.destroy()
                    return

                # Шаг 2: Распаковка во временную папку
                temp_dir = tempfile.mkdtemp()  # создаёт временную директорию
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    print(zip_ref.namelist())
                    zip_ref.extractall(temp_dir)

                folder_path = temp_dir

                images = [
                    f for f in os.listdir(temp_dir)
                    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))
                ]

                if not images:
                    self.destroy()
                    raise NoImagesError()
            
            print("images: ", images)

        if not path:
            try:
                self._copy_to_folder_and_rename(folder_path, is_zip=is_zip)
            except FileNotFoundError as e:
                self.destroy()
                messagebox.showerror("Ошибка", f"Нет .json файл с разметкой в архиве:\n\n{e}")

        self.image_loader = ImageLoader(
            self.folder_path,
            annotated_path=self.annotated_path
        )

        self.canvas.image_loader = self.image_loader

        self.annotation_saver = AnnotationSaver(
            self.folder_path,
            annotated_path=self.annotated_path
        )
        self.canvas.annotation_saver = self.annotation_saver
        self._load_image()

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
        print("_load_existing_annotations", current_image_path)
        annotations = self.annotation_saver.get_annotations(current_image_path)
        print(annotations)

        for annotation in annotations:
            self.canvas.add_annotation(annotation)

    def _prev_image(self):
        self._load_image("prev")

    def _next_image(self):
        self._load_image("next")

    def _update_status(self):
        if self.image_loader:
            current_index = self.image_loader.current_index
            total_images = len(self.image_loader.image_files)
            self.status_var.set(
                f"Изображение {current_index + 1}/{total_images}"
            )
            
            # Update button states
            self.prev_button.configure(state='normal' if current_index > 0 else 'disabled')
            self.next_button.configure(state='normal' if current_index < total_images - 1 else 'disabled')

    def close(self):
        self.destroy()
        self.app.get_annotated_datasets()