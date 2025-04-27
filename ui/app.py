import hashlib
import os
import shutil
import sys
import tempfile
import threading
import tkinter as tk
from collections import defaultdict
from datetime import datetime
from time import sleep

from api.api import get_dataset, get_datasets_info
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path
from PIL import Image, ImageTk

from utils.dataset_deleter import DatasetDeleter
from utils.json_manager import JsonManager, AnnotationFileManager
from utils.logger import log_method
from data_processing.annotation_saver import AnnotationSaver
from data_processing.image_loader import ImageLoader
from ui.canvas import AnnotationCanvas
from utils.paths import DATA_DIR
from utils.errors import FolderLoadError, NoImagesError


def get_unique_folder_name(source_path: Path) -> str:
    unique_str = source_path.name
    return str(hashlib.md5(unique_str.encode()).hexdigest()[:8])


class AnnotationPopover(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
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
        ttk.Label(right_frame, text="Разметка:").pack(pady=10)
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
        self.deleter = DatasetDeleter(self.root)
        self.root.bind("<<RefreshDatasets>>", lambda e: self.get_annotated_datasets())

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
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=50)

        self.annotate_btn = tk.Button(
            button_frame,
            text="Загрузить папку для разметки",
            command=self._show_popover,
            bg="#e1e1e1"
        )
        self.annotate_btn.pack(side=tk.LEFT, padx=20, ipadx=20, ipady=10)

        self.annotate_btn_googledrive = tk.Button(
            button_frame,
            text="Загрузить папку для разметки из Google Drive",
            command=self._show_gdrive_folder_selector,
            bg="#e1e1e1"
        )
        self.annotate_btn_googledrive.pack(side=tk.LEFT, padx=20, ipadx=20, ipady=10)

        # Настройка стилей
        style = ttk.Style()
        style.configure("Accent.TButton",
                        background="#4285f4",
                        foreground="white",
                        font=("Helvetica", 12, "bold"),
                        padding=10)

        # Основной фрейм
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Нижняя часть: разделяем на две колонки
        self.bottom_frame = tk.Frame(self.main_frame)
        self.bottom_frame.pack(fill=tk.BOTH, expand=True)

        # Основной контейнер для левой колонки
        left_container = tk.Frame(self.bottom_frame, bg="white")
        left_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Заголовок
        tk.Label(
            left_container,
            text="Аннотированные датасеты",
            font=("Arial", 12),
            bg="white"
        ).pack(pady=5)

        # Создаем Canvas с двойной прокруткой
        self.canvas = tk.Canvas(left_container, bg="white")
        h_scroll = tk.Scrollbar(left_container, orient="horizontal", command=self.canvas.xview)
        v_scroll = tk.Scrollbar(left_container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)

        # Фрейм для содержимого внутри Canvas
        self.scrollable_frame = tk.Frame(self.canvas, bg="white")
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # Упаковка скроллбаров и canvas
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Виджеты датасетов
        self.annotated_datasets = []
        self.get_annotated_datasets()

        # Правая колонка
        self.right_frame = tk.Frame(self.bottom_frame, bg="white", relief=tk.SUNKEN, borderwidth=1)
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Заголовок для правой части
        tk.Label(
            self.right_frame,
            text="Дообучение",
            font=("Arial", 12),
            bg="white"
        ).pack(pady=10)

    def get_annotated_datasets(self):
        output_dir = DATA_DIR / "annotated_dataset"

        # Очищаем предыдущие датасеты
        for dataset in self.annotated_datasets:
            dataset.destroy()
        self.annotated_datasets = []
        self.selected_datasets = set()  # Для хранения выбранных датасетов

        if not output_dir.exists():
            return

        self.scrollable_frame.bind("<Configure>", lambda _: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Панель инструментов
        toolbar = tk.Frame(self.scrollable_frame, bg="#f0f0f0")
        toolbar.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 10), padx=5)

        merge_btn = tk.Button(
            toolbar,
            text="Объединить выбранные",
            command=self._merge_selected_datasets,
            bg="#e1e1e1",
            relief=tk.FLAT
        )
        merge_btn.pack(side=tk.LEFT, padx=5)

        delete_btn = tk.Button(
            toolbar,
            text="Удалить выбранные",
            command=self._delete_selected_datasets,
            bg="#e1e1e1",
            relief=tk.FLAT
        )
        delete_btn.pack(side=tk.LEFT, padx=5)

        select_all_btn = tk.Button(
            toolbar,
            text="Выбрать все",
            command=self._select_all_datasets,
            bg="#e1e1e1",
            relief=tk.FLAT
        )
        select_all_btn.pack(side=tk.RIGHT, padx=5)

        # Получаем список датасетов
        sub_folders = [f for f in output_dir.iterdir() if f.is_dir()]
        json_manager = JsonManager(os.path.join(output_dir, 'hash_to_name.json'))

        # Параметры сетки
        ITEMS_PER_ROW = 3
        ITEM_WIDTH = 250
        PREVIEW_SIZE = 150

        for i, sub_folder in enumerate(sub_folders):
            real_name = Path(json_manager[sub_folder.name]).name

            # Фрейм для одного датасета
            item_frame = tk.Frame(
                self.scrollable_frame,
                width=ITEM_WIDTH,
                height=ITEM_WIDTH + 60,
                bg="white",
                bd=1,
                relief=tk.RAISED,
                highlightbackground="#e0e0e0",
                highlightthickness=1
            )
            item_frame.grid(
                row=(i // ITEMS_PER_ROW) + 1,
                column=i % ITEMS_PER_ROW,
                padx=10,
                pady=10,
                sticky="nsew"
            )
            item_frame.grid_propagate(False)

            # Чекбокс для выбора
            var = tk.IntVar()
            chk = tk.Checkbutton(
                item_frame,
                variable=var,
                bg="white",
                command=lambda f=sub_folder, v=var: self._toggle_dataset_selection(f, v)
            )
            chk.var = var  # Сохраняем ссылку на переменную
            chk.place(x=5, y=5)

            # Инициализируем состояние чекбокса
            var.set(1 if sub_folder in self.selected_datasets else 0)

            # Контейнер для изображения
            img_container = tk.Frame(item_frame, bg="white", height=PREVIEW_SIZE + 10)
            img_container.pack(fill=tk.X, pady=(25, 5))
            img_container.pack_propagate(False)

            # Загрузка превью изображения
            image_files = (list(sub_folder.glob("*.jpg")) +
                           list(sub_folder.glob("*.jpeg")) +
                           list(sub_folder.glob("*.png")))

            if image_files:
                try:
                    img = Image.open(image_files[0])
                    img.thumbnail((PREVIEW_SIZE, PREVIEW_SIZE))
                    photo = ImageTk.PhotoImage(img)

                    img_label = tk.Label(img_container, image=photo, bg="white", cursor="hand2")
                    img_label.image = photo
                    img_label.pack()
                    img_label.bind("<Button-1>", lambda _, s=sub_folder: self._modify_dataset(s))
                except Exception as e:
                    print(f"Ошибка загрузки изображения: {e}")
                    no_img = tk.Label(img_container, text="No preview", bg="white", fg="gray")
                    no_img.pack(pady=20)

            # Название датасета
            name_label = tk.Label(
                item_frame,
                text=real_name,
                bg="white",
                wraplength=ITEM_WIDTH - 20,
                cursor="hand2"
            )
            name_label.pack(fill=tk.X, padx=5, pady=(0, 5))
            name_label.bind("<Button-1>", lambda _, s=sub_folder: self._modify_dataset(s))

            # Статистика и кнопка удаления
            stat_frame = tk.Frame(item_frame, bg="white")
            stat_frame.pack(fill=tk.X, pady=(0, 5))

            annotated_imgs, imgs = self._get_dataset_stat(sub_folder)
            stat_label = tk.Label(
                stat_frame,
                text=f"Аннотировано: {annotated_imgs}/{imgs}",
                bg="white",
                font=("Arial", 8)
            )
            stat_label.pack(side=tk.LEFT, padx=5)

            # Кнопка редактирования (карандаш)
            edit_btn = tk.Button(
                stat_frame,
                text="✏️",
                fg="blue",
                bg="white",
                bd=0,
                font=("Arial", 12, "bold"),
                command=lambda s=sub_folder: self._edit_dataset(s)
            )
            edit_btn.pack(side=tk.RIGHT, padx=5)

            # Кнопка удаления (крестик)
            del_btn = tk.Button(
                stat_frame,
                text="×",
                fg="red",
                bg="white",
                bd=0,
                font=("Arial", 12, "bold"),
                command=lambda s=sub_folder: self._delete_single_dataset(s)
            )
            del_btn.pack(side=tk.RIGHT, padx=5)

            self.annotated_datasets.append(item_frame)

    def _toggle_dataset_selection(self, dataset, var):
        """Переключает выбор датасета"""
        if var.get() == 1:
            self.selected_datasets.add(dataset)
        else:
            self.selected_datasets.discard(dataset)

    def _edit_dataset(self, dataset):
        output_dir = DATA_DIR / "annotated_dataset"
        hash_to_name_path = output_dir / 'hash_to_name.json'
        hash_to_name_manager = JsonManager(hash_to_name_path)

        current_value = Path(hash_to_name_manager[dataset.name]).name
        new_value = simpledialog.askstring("Редактирование", "Введите новое значение:", initialvalue=current_value)
        if new_value:
            # Обработка нового значения
            print(f"Новый введенный текст: {new_value}")

            hash_to_name_manager[dataset.name] = new_value
            hash_to_name_manager.save()

        self.root.event_generate("<<RefreshDatasets>>")

    def _select_all_datasets(self):
        """Выбирает или снимает выбор со всех датасетов"""
        # Проверяем текущее состояние (если хотя бы один не выбран - выбираем все)
        select_all = not all(dataset in self.selected_datasets for dataset in self._get_all_dataset_folders())

        # Получаем все датасеты
        all_datasets = self._get_all_dataset_folders()

        if select_all:
            self.selected_datasets = set(all_datasets)
        else:
            self.selected_datasets = set()

        # Обновляем чекбоксы во всех фреймах датасетов
        for widget in self.scrollable_frame.winfo_children():
            if isinstance(widget, tk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, tk.Checkbutton):
                        child.var.set(1 if select_all else 0)

    def _get_all_dataset_folders(self):
        """Возвращает список всех папок с датасетами"""
        output_dir = DATA_DIR / "annotated_dataset"
        return [f for f in output_dir.iterdir() if f.is_dir()] if output_dir.exists() else []

    def _merge_selected_datasets(self):
        if not self.selected_datasets:
            return

        confirm = messagebox.askyesno(
            "Подтверждение",
            f"Объединить {len(self.selected_datasets)} датасетов в один?",
            parent=self.root
        )
        if not confirm:
            return

        # Куда объединять
        output_dir = DATA_DIR / "annotated_dataset"
        annotations_path = output_dir / 'annotations.json'
        hash_to_name_path = output_dir / 'hash_to_name.json'
        annotations_manager = JsonManager(annotations_path)
        hash_to_name_manager = JsonManager(hash_to_name_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        merged_folder = output_dir / f"merged_{timestamp}"

        merged_folder_path = str(merged_folder)

        hash_merged_folder_path = get_unique_folder_name(merged_folder)
        hash_to_name_manager[hash_merged_folder_path] = merged_folder_path
        merged_folder_path = str(output_dir / hash_merged_folder_path)
        Path(merged_folder_path).mkdir(parents=True, exist_ok=True)

        try:
            for dataset in self.selected_datasets:
                if not dataset.exists() or not dataset.is_dir():
                    continue

                for item in dataset.iterdir():
                    dest = Path(merged_folder_path) / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, dest)

                dataset_path = str(output_dir / dataset.name)

                if merged_folder_path not in annotations_manager.keys():
                    if dataset_path in annotations_manager.keys() and annotations_manager[dataset_path] is not None:
                        annotations_manager[merged_folder_path] = annotations_manager[dataset_path]
                    else:
                        annotations_manager[merged_folder_path] = {}
                else:
                    if dataset_path in annotations_manager.keys() and annotations_manager[dataset_path] is not None:
                        annotations_manager[merged_folder_path] = (annotations_manager[merged_folder_path] |
                                                                   annotations_manager[dataset_path])

            annotations_manager.save()
            self.root.event_generate("<<RefreshDatasets>>")
            messagebox.showinfo("Готово", f"Датасеты объединены в папку:\n{merged_folder}", parent=self.root)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при объединении: {str(e)}", parent=self.root)

    def _delete_single_dataset(self, dataset_folder):
        self.deleter.delete_datasets([dataset_folder])

    def _delete_selected_datasets(self):
        if not self.selected_datasets:
            messagebox.showwarning("Внимание", "Не выбраны датасеты для удаления")
            return
        self.deleter.delete_datasets(list(self.selected_datasets))

    def _translate_from_hash(self, hash_folder: Path):
        output_dir = DATA_DIR / "annotated_dataset"

        json_manager = JsonManager(
            os.path.join(output_dir, 'hash_to_name.json')
        )

        real_path = json_manager[hash_folder.name]
        return real_path

    def _get_dataset_stat(self, folder):
        output_dir = DATA_DIR / "annotated_dataset"

        json_manager = AnnotationFileManager(
            os.path.join(output_dir, 'annotations.json')
        )

        imgs = len([
            f for f in os.listdir(folder)
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ])

        annotated_imgs = len(json_manager.get_folder_info(str(folder)).keys())

        return annotated_imgs, imgs

    def _modify_dataset(self, folder_path):
        popover = AnnotationPopover(self.root, self)

        # Центрируем Popover относительно главного окна
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 600
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 400
        popover.geometry(f"+{x}+{y}")

        # Пытаемся загрузить папку с картинками
        try:
            popover.load_folder(folder_path)
        except NoImagesError as e:
            e.show_tkinter_error()
            popover.destroy()

    def _show_popover(self):
        """Показывает Popover с интерфейсом разметки"""
        popover = AnnotationPopover(self.root, self)

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

    def _show_gdrive_folder_selector(self):
        """Всплывающее окно с множественным выбором папок"""
        self.selector_window = tk.Toplevel(self.root)
        self.selector_window.title("Выберите папки (Ctrl+ЛКМ для множественного выбора)")
        self.selector_window.geometry("500x600")

        # Контейнер для списка папок
        frame = tk.Frame(self.selector_window)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Список папок с множественным выбором
        self.folder_listbox = tk.Listbox(
            frame,
            selectmode=tk.MULTIPLE,
            font=('Arial', 11),
            height=20,
            bg='white',
            fg='#333',
            selectbackground='#4285F4',
            activestyle='none'
        )

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.folder_listbox.pack(fill=tk.BOTH, expand=True)
        self.folder_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.folder_listbox.yview)

        # Загрузка папок
        self._load_folders()

        # Кнопки управления
        btn_frame = tk.Frame(self.selector_window)
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame,
            text="Выбрать",
            command=self._confirm_selection,
            bg="#34A853",
            fg="black",
            padx=20
        ).pack(side=tk.LEFT, padx=10)

        tk.Button(
            btn_frame,
            text="Отмена",
            command=self.selector_window.destroy,
            bg="#EA4335",
            fg="black",
            padx=20
        ).pack(side=tk.LEFT, padx=10)

    def _load_folders(self):
        """Загрузка папок через API"""
        try:
            # Ваш API-запрос для получения папок
            df = get_datasets_info()
            folders = list(sorted(list(set(df['Регион']))))

            self.folder_listbox.delete(0, tk.END)
            self.all_folders = []  # Сохраняем полные данные

            for folder in folders:
                self.folder_listbox.insert(tk.END, folder)
                self.all_folders.append(folder)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить папки:\n{str(e)}")

    def _confirm_selection(self):
        """Обработка выбранных папок"""
        selected_indices = self.folder_listbox.curselection()

        if not selected_indices:
            messagebox.showwarning("Внимание", "Выберите хотя бы одну папку")
            return

        selected_folders = [self.all_folders[i] for i in selected_indices]

        # Создаем окно прогресса
        self.progress_window = tk.Toplevel(self.selector_window)
        self.progress_window.title("Загрузка файлов")
        self.progress_window.geometry("400x200")

        # Элементы отображения прогресса
        tk.Label(self.progress_window, text="Идет загрузка файлов...", font=('Arial', 12)).pack(pady=10)

        self.progress_label = tk.Label(self.progress_window, text="Подготовка к загрузке...")
        self.progress_label.pack(pady=5)

        self.progress_bar = ttk.Progressbar(
            self.progress_window,
            orient=tk.HORIZONTAL,
            length=300,
            mode='determinate'
        )
        self.progress_bar.pack(pady=10)

        self.current_file_label = tk.Label(self.progress_window, text="", wraplength=350)
        self.current_file_label.pack(pady=5)

        # Кнопка отмены
        tk.Button(
            self.progress_window,
            text="Отменить",
            command=self._cancel_processing,
            bg="#EA4335",
            fg="black"
        ).pack(pady=10)

        # Запускаем обработку в отдельном потоке
        self.processing_cancelled = False
        threading.Thread(
            target=self._process_folders_with_progress,
            args=(selected_folders,),
            daemon=True
        ).start()

    def _process_folders_with_progress(self, folders):
        """Обработка папок с обновлением прогресса"""
        try:
            df = get_datasets_info()
            self.progress_bar["maximum"] = len(df[df['Регион'].isin(folders)])

            # Получаем итератор
            dataset_iterator = get_dataset(folders)
            window_active = True

            images_from_google_drive = defaultdict(list[tuple])

            for i, (blazon, image, name, region) in enumerate(dataset_iterator):
                if self.processing_cancelled or not window_active:
                    break  # Прерываем цикл при отмене

                if not self.progress_window.winfo_exists():  # Проверяем, существует ли окно
                    window_active = False
                    break

                # Обновляем UI
                try:
                    self.root.after(0, self._update_progress, {
                        'current': i + 1,
                        'total': self.progress_bar["maximum"],
                        'name': name,
                        'region': region
                    })
                except tk.TclError:
                    window_active = False
                    break

                images_from_google_drive[region].append((image, blazon, name))

                # Добавляем небольшую задержку для обработки событий
                sleep(0.01)

            # Завершение обработки
            if window_active and self.progress_window.winfo_exists():
                self.root.after(0, self._finish_processing, not self.processing_cancelled)

            if not self.processing_cancelled and window_active:
                self._save_google_drive_files(images_from_google_drive)

        except Exception as e:
            self.root.after(0, self._show_error, str(e))

    def _save_google_drive_files(self, files):
        output_dir = DATA_DIR / "annotated_dataset"

        for folder, images in files.items():
            real_name = output_dir / (folder + "_drive")
            hash_name = get_unique_folder_name(real_name)
            os.makedirs(output_dir / hash_name, exist_ok=True)

            json_manager = JsonManager(
                os.path.join(output_dir, 'hash_to_name.json')
            )

            if hash_name not in json_manager.keys():
                json_manager[hash_name] = str(real_name)
            else:
                real_name = str(real_name) + "_copy"
                hash_name = get_unique_folder_name(Path(real_name))
                json_manager[hash_name] = str(real_name)

                os.makedirs(output_dir / hash_name, exist_ok=True)

            for i, (img, blazon, name) in enumerate(images):
                if not isinstance(img, Image.Image):
                    print(f"Элемент с индексом {i} не является изображением PIL")
                    continue

                filepath = os.path.join(output_dir / hash_name, name + '.jpg')

                # Сохраняем в формате JPG
                img.save(filepath, format="JPEG")

                # Cохраняем блазон
                json_manager = JsonManager(
                    os.path.join(output_dir, 'blazons.json')
                )

                if hash_name not in json_manager.keys():
                    json_manager[hash_name] = {name + '.jpg': blazon}
                else:
                    d = json_manager[hash_name]
                    d[name + '.jpg'] = blazon
                    json_manager[hash_name] = d

                print(f"Сохранено: {filepath}")
        self.get_annotated_datasets()

    def _update_progress(self, data):
        """Обновление элементов прогресса"""
        try:
            if not hasattr(self, 'progress_window') or not self.progress_window.winfo_exists():
                return
            self.progress_bar["value"] = data['current']
            self.progress_label.config(
                text=f"Обработано: {data['current']} из {data['total']} файлов "
                     f"({data['current'] / data['total'] * 100:.1f}%)"
            )
            self.current_file_label.config(
                text=f"Текущий файл: {data['name']}"
            )
        except tk.TclError:
            pass

    def _finish_processing(self, success):
        """Завершение обработки с разными сценариями"""
        try:
            if not self.progress_window.winfo_exists():
                return
            if success:
                messagebox.showinfo("Готово", "Все файлы успешно обработаны!")
            elif not success and self.processing_cancelled:
                messagebox.showinfo("Отменено", "Обработка прервана пользователем")
            self.progress_window.destroy()
            self.selector_window.destroy()
        except tk.TclError:
            pass

    def _cancel_processing(self):
        """Обработка отмены с четким разделением состояний"""
        self.processing_cancelled = True
        try:
            if hasattr(self, 'progress_window') and self.progress_window.winfo_exists():
                self.progress_label.config(text="Завершение процесса...")
                self.progress_window.after(500, self.progress_window.destroy)
        except tk.TclError:
            pass

    def _show_error(self, error_msg):
        """Отображение ошибки"""
        self.progress_window.destroy()
        messagebox.showerror("Ошибка", f"Произошла ошибка:\n{error_msg}")

    def run(self):
        self.root.mainloop()
