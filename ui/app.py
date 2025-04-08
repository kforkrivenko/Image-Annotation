import hashlib
import os
import shutil
import sys
import tempfile
import tkinter as tk
import time
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk

from utils.json_manager import JsonManager
from utils.logger import log_method
from data_processing.annotation_saver import AnnotationSaver
from data_processing.image_loader import ImageLoader
from ui.canvas import AnnotationCanvas
from utils.paths import DATA_DIR, BASE_DIR


def get_unique_folder_name(source_path: Path) -> str:
    unique_str = source_path.name
    return str(hashlib.md5(unique_str.encode()).hexdigest()[:8])


class FolderLoadError(Exception):
    def __init__(self, message="Произошла ошибка загрузки"):
        self.message = message
        super().__init__(self.message)

    def show_tkinter_error(self, parent=None):
        """Отображение ошибки в Tkinter"""
        messagebox.showerror("Ошибка загрузки", self.message)


class NoImagesError(FolderLoadError):
    def __init__(self):
        self.message = "В папке нет картинок!"
        super().__init__(self.message)


class AnnotationPopover(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Разметка датасета")
        self.geometry("1200x800")

        # Блокируем главное окно
        self.grab_set()
        self.focus_set()

        # Инициализация состояния
        self.image_loader = None
        self.annotation_saver = None
        self.folder_path = None
        self.json_manager = None  # Управление hash_to_name

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

        ttk.Label(right_frame, text="Разметка:").pack(pady=5)
        ttk.Entry(right_frame, textvariable=text_var, width=30).pack(pady=5)

        # Canvas для изображений
        self.canvas = AnnotationCanvas(left_frame, self.image_loader, self.annotation_saver)
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

        # Кнопка закрытия
        ttk.Button(
            control_frame,
            text="Готово",
            style="Popover.TButton",
            command=self.destroy
        ).pack(side=tk.RIGHT, padx=5, pady=10)

    def _copy_to_folder_and_rename(self, folder_path):
        """Копируем в защищенную папку, переименовываем с помощью хэша"""
        folder_path = Path(folder_path)
        if folder_path.exists():
            if getattr(sys, 'frozen', False):
                output_dir = DATA_DIR / "annotated_dataset"
            else:
                output_dir = BASE_DIR / "annotated_dataset"

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

    def load_folder(self):
        folder_path = filedialog.askdirectory(title="Выберите папку с изображениями")
        if folder_path:
            images = [
                f for f in os.listdir(folder_path)
                if f.lower().endswith(('.jpg', '.jpeg', '.png'))
            ]
            if not images:
                raise NoImagesError()

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
        if self.image_loader:
            img = self.image_loader.get_image(direction)
            if img:
                current_image_path = self.image_loader.get_current_image_path()
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


def get_resource_path(relative_path):
    """Возвращает корректный путь к ресурсам для разных режимов выполнения"""
    try:
        # Режим собранного приложения (PyInstaller)
        base_path = sys._MEIPASS
    except AttributeError:
        # Режим разработки
        base_path = os.path.abspath(".")

    # Построение полного пути
    path = os.path.join(base_path, relative_path)

    # Нормализация пути (убираем лишние слеши и т.д.)
    return os.path.normpath(path)


class ImageAnnotationApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.geometry("1200x800")
        self.root.title("Image Annotation Tool")
        self._set_window_icon()
        self._setup_ui()

    def _set_window_icon(self):
        """Устанавливает иконку в зависимости от ОС"""
        try:
            if sys.platform == 'darwin':  # macOS
                # Для .icns на macOS используем специальный метод
                icns_path = get_resource_path('favicons/favicon.icns')
                if os.path.exists(icns_path):
                    # Создаем временный .png для tkinter (на MacOS лучше работает через iconphoto)
                    temp_png = os.path.join(tempfile.gettempdir(), 'temp_icon.png')

                    # Конвертируем .icns в .png если нужно
                    if not os.path.exists(temp_png):
                        try:
                            from PIL import Image
                            img = Image.open(icns_path)
                            img.save(temp_png)
                        except:
                            # Если конвертация не удалась, копируем как есть
                            shutil.copy2(icns_path, temp_png)

                    img = tk.PhotoImage(file=temp_png)
                    self.root.tk.call('wm', 'iconphoto', self.root._w, img)
            elif sys.platform == 'win32':  # Windows
                ico_path = get_resource_path('favicons/favicon.ico')
                if os.path.exists(ico_path):
                    self.root.iconbitmap(ico_path)

        except Exception as e:
            print(f"Ошибка установки иконки: {str(e)}")
            # Попробуем установить стандартную иконку Tkinter как fallback
            try:
                self.root.tk.call('wm', 'iconphoto', self.root._w,
                                  tk.PhotoImage(file=get_resource_path('favicons/favicon.png')))
            except:
                pass

    def _setup_ui(self):
        # Главная кнопка
        self.annotate_btn = tk.Button(
            self.root,
            text="Загрузить папку для разметки",
            command=self._show_popover,
            bg="#e1e1e1"
        )
        self.annotate_btn.pack(pady=50, padx=20, ipadx=20, ipady=10)

        # Настройка стилей
        style = ttk.Style()
        style.configure("Accent.TButton",
                        background="#4285f4",
                        foreground="white",
                        font=("Helvetica", 12, "bold"),
                        padding=10)

        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.dataset_frame = tk.Frame(self.main_frame)
        self.dataset_frame.pack(fill=tk.BOTH, expand=True)

        self.dataset_tree = ttk.Treeview(
            self.dataset_frame,
            columns="Images",
            show="headings",
            height=15
        )
        self.dataset_tree.heading("#0", text="Dataset Name")
        self.dataset_tree.heading("Images", text="Размеченные датасеты")
        self.dataset_tree.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Кнопка для открытия выбранного
        ttk.Button(
            self.dataset_frame,
            text="Открыть для редактирования",
            command=lambda: None
        ).pack(pady=10)

    def _show_popover(self):
        """Показывает Popover с интерфейсом разметки"""
        popover = AnnotationPopover(self.root)

        # Центрируем Popover относительно главного окна
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 600
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 400
        popover.geometry(f"+{x}+{y}")

        # Пытаемся загрузить папку с картинками
        try:
            popover.load_folder()
        except NoImagesError as e:
            e.show_tkinter_error()
            popover.destroy()

    def run(self):
        self.root.mainloop()
