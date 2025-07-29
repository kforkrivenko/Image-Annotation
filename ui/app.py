import os
import shutil
import sys
import tempfile
import threading
import tkinter as tk
import time
from collections import defaultdict
from datetime import datetime
from time import sleep
from api.api import get_dataset, get_datasets_info
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path
import zipfile
import yaml

from data_processing.annotation_popover import AnnotationPopover, get_unique_folder_name
from utils.dataset_deleter import DatasetDeleter
from utils.dataset_download import download_dataset_with_notification
from utils.json_manager import JsonManager, AnnotationFileManager

from utils.paths import DATA_DIR
from utils.errors import FolderLoadError, NoImagesError

# Импорты для ML компонентов (загружаются при инициализации приложения)
try:
    import torch
    from ultralytics import YOLO
except ImportError:
    # Если библиотеки не установлены, они будут импортированы позже
    torch = None
    YOLO = None


class TextRedirector:
    """Безопасное перенаправление вывода в текстовый виджет"""

    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.root = text_widget._root()  # Получаем корневое окно

    def write(self, string):
        def safe_write():
            if self.text_widget.winfo_exists():  # Проверяем, существует ли виджет
                self.text_widget.insert(tk.END, string)
                self.text_widget.see(tk.END)

        try:
            self.root.after(0, safe_write)  # Запланировать в основном потоке
        except:
            pass  # Игнорируем ошибки, если окно уже закрыто

    def flush(self):
        pass


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
    def __init__(self, master=None):
        # Проверяем, не создано ли уже приложение
        if hasattr(self.__class__, '_instance'):
            print("Приложение уже создано")
            return
        self.__class__._instance = self
        
        self.root = tk.Toplevel(master=master)
        self.root.geometry("1600x1200")
        self.root.title("Image Annotation Tool")
        self._set_window_icon()
        self._setup_ui()
        self.deleter = DatasetDeleter(self.root)
        self.deleter_test = DatasetDeleter(self.root, test_dataset=True)
        self.root.bind("<<RefreshDatasets>>", lambda e: self.get_annotated_datasets())
        self.root.bind("<<RefreshTestedDatasets>>", lambda e: self.get_tested_datasets())
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        try:
            if self.root.master:
                self.root.master.quit()
                self.root.master.destroy()
            self.root.destroy()
        except tk.TclError:
            pass  # окно уже уничтожено

    def _set_window_icon(self):
        """Устанавливает иконку в зависимости от ОС"""
        try:
            if sys.platform == 'darwin':  # macOS
                icns_path = get_resource_path('favicons/favicon.icns')
                if os.path.exists(icns_path):
                    # Создаем временный .png для tkinter
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
        # Проверяем, не происходит ли уже настройка UI
        if hasattr(self, '_ui_setup_done'):
            return
        self._ui_setup_done = True
        
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

        # self.annotate_btn_googledrive = tk.Button(
        #     button_frame,
        #     text="Загрузить папку для разметки из Google Drive",
        #     command=self._show_gdrive_folder_selector,
        #     bg="#e1e1e1"
        # )
        # self.annotate_btn_googledrive.pack(side=tk.LEFT, padx=20, ipadx=20, ipady=10)

        self.annotate_btn_zip = tk.Button(
            button_frame,
            text="Загрузить размеченный датасет .zip",
            command= lambda: self._show_popover(is_zip=True),
            bg="#e1e1e1"
        )
        self.annotate_btn_zip.pack(side=tk.LEFT, padx=20, ipadx=20, ipady=10)

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

        self.tested_datasets = []

        # --- Правая часть (дообучение) ---
        self.right_frame = tk.Frame(self.bottom_frame, bg="white", relief=tk.SUNKEN, borderwidth=1)
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Контейнер для вертикального разделения
        self.right_container = tk.Frame(self.right_frame, bg="white")
        self.right_container.pack(fill=tk.BOTH, expand=True)

        # Верхняя часть (существующее содержимое)
        self.right_top_frame = tk.Frame(self.right_container, bg="white")
        self.right_top_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок для верхней части
        tk.Label(
            self.right_top_frame,
            text="Дообучение",
            font=("Arial", 12),
            bg="white"
        ).pack(pady=10)

        # Блок выбора модели
        self.model_frame = tk.Frame(self.right_top_frame, bg="white")
        self.model_frame.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(
            self.model_frame,
            text="Выбор модели:",
            bg="white",
            font=("Arial", 10)
        ).pack(anchor="w")

        self.available_models = self._get_available_models()
        self.model_var = tk.StringVar()

        self.model_listbox = tk.Listbox(
            self.model_frame,
            height=8,
            exportselection=False
        )
        self.model_listbox.pack(fill=tk.X, pady=5)

        # Заполняем список моделей
        for model in self.available_models:
            self.model_listbox.insert(tk.END, model)

        # Устанавливаем выбранную модель, если есть
        if self.available_models:
            self.model_listbox.selection_set(0)
            self.model_var.set(self.available_models[0])

        # Привязка выбора модели
        def on_model_select(event):
            selection = self.model_listbox.curselection()
            if selection:
                selected_model = self.model_listbox.get(selection[0])
                self.model_var.set(selected_model)

        self.model_listbox.bind("<<ListboxSelect>>", on_model_select)

        self.rename_button = ttk.Button(
            self.model_frame,
            text="Переименовать",
            command=self._rename_model
        )
        self.rename_button.pack(pady=5)

        self.delete_button = ttk.Button(
            self.model_frame,
            text="Удалить",
            command=self._delete_model
        )
        self.delete_button.pack(pady=5)

        # Если моделей нет — отключаем список и кнопки
        if not self.available_models:
            self.model_listbox.configure(state="disabled")
            self.rename_button.configure(state="disabled")
            self.delete_button.configure(state="disabled")


        # Блок кнопок скачивания
        download_frame = tk.Frame(self.model_frame, bg="white")
        download_frame.pack(fill=tk.X, pady=10)

        tk.Label(
            download_frame,
            text="Скачать модели:",
            bg="white",
            font=("Arial", 9)
        ).pack(anchor="w", pady=(0, 5))

        tk.Button(
            download_frame,
            text="YOLOv8n",
            command=lambda: self._download_model("yolov8n"),
            bg="#e1e1e1"
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            download_frame,
            text="YOLOv8s",
            command=lambda: self._download_model("yolov8s"),
            bg="#e1e1e1"
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            download_frame,
            text="YOLOv8m",
            command=lambda: self._download_model("yolov8m"),
            bg="#e1e1e1"
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            download_frame,
            text="Загрузить свою модель",
            command=self._download_user_model,
            bg="#e1e1e1"
        ).pack(side=tk.LEFT, padx=5)

        # Кнопка запуска обучения
        train_button = tk.Button(
            self.right_top_frame,
            text="Обучить на выбранных датасетах",
            command=self._open_training_popup,
            bg="#4CAF50",
            font=("Arial", 12, "bold")
        )
        train_button.pack(pady=20, ipadx=10, ipady=5)

        test_button = tk.Button(
            self.right_top_frame,
            text="Протестировать на датасете",
            command=self._open_testing_popup,
            bg="#2196F3",
            font=("Arial", 12, "bold")
        )
        test_button.pack(pady=10, ipadx=10, ipady=5)

        # Нижняя часть (новая)
        self.right_bottom_frame = tk.Frame(self.right_container, bg="white", relief=tk.RAISED, borderwidth=1)
        self.right_bottom_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # Заголовок для нижней части
        tk.Label(
            self.right_bottom_frame,
            text="Протестированные датасеты",
            font=("Arial", 12),
            bg="white"
        ).pack(pady=10)

        # Контейнер для списка протестированных датасетов
        self.tested_datasets_container = tk.Frame(self.right_bottom_frame, bg="white")
        self.tested_datasets_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Прокручиваемый список
        self.tested_canvas = tk.Canvas(self.tested_datasets_container, bg="white")
        scrollbar = ttk.Scrollbar(self.tested_datasets_container, orient="vertical", command=self.tested_canvas.yview)
        self.tested_scrollable_frame = tk.Frame(self.tested_canvas, bg="white")

        self.tested_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.tested_canvas.configure(
                scrollregion=self.tested_canvas.bbox("all")
            )
        )

        self.tested_canvas.create_window((0, 0), window=self.tested_scrollable_frame, anchor="nw")
        self.tested_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.tested_canvas.pack(side="left", fill="both", expand=True)

        # Инициализация списка протестированных датасетов
        self._setup_tested_datasets_panel()

    def _rename_model(self):
        selection = self.model_listbox.curselection()
        if not selection:
            messagebox.showwarning("Нет выбора", "Выберите модель для переименования.")
            return

        old_name = self.model_listbox.get(selection[0])
        new_name = simpledialog.askstring("Переименование", f"Новое имя для модели '{old_name}':", initialvalue=old_name)

        if new_name:
            models_dir = DATA_DIR / "models"
            old_path = os.path.join(models_dir, old_name)
            new_path = os.path.join(models_dir, new_name)
            if os.path.exists(new_path):
                messagebox.showerror("Ошибка", f"Модель с именем '{new_name}' уже существует.")
                return
            try:
                os.rename(old_path, new_path)
                self._refresh_models_list()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось переименовать модель:\n{e}")

    def _delete_model(self):
        selection = self.model_listbox.curselection()
        if not selection:
            messagebox.showwarning("Нет выбора", "Выберите модель для удаления.")
            return

        model_name = self.model_listbox.get(selection[0])
        
        # # Запрещаем удаление базовых моделей
        # if not model_name.endswith('_custom') and not '_best' in model_name:
        #     messagebox.showwarning("Внимание", "Нельзя удалять базовые модели (yolov8n.pt, yolov8s.pt и т.д.).")
        #     return

        # Запрашиваем подтверждение
        confirm = messagebox.askyesno(
            "Подтверждение удаления", 
            f"Вы уверены, что хотите удалить модель '{model_name}'?\n\nЭто действие нельзя отменить.",
            icon='warning'
        )
        
        if confirm:
            models_dir = DATA_DIR / "models"
            model_path = models_dir / model_name
            
            try:
                os.remove(model_path)
                messagebox.showinfo("Готово", f"Модель '{model_name}' успешно удалена.")
                self._refresh_models_list()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить модель:\n{e}")

    def _refresh_models_list(self):
        """Обновляет список моделей в интерфейсе"""
        self.available_models = self._get_available_models()
        self.model_listbox.delete(0, tk.END)
        for model in self.available_models:
            self.model_listbox.insert(tk.END, model)
        
        # Обновляем состояние кнопок
        if self.available_models:
            self.model_listbox.configure(state="normal")
            self.rename_button.configure(state="normal")
            self.delete_button.configure(state="normal")
            # Устанавливаем выбранную модель, если есть
            if not self.model_listbox.curselection():
                self.model_listbox.selection_set(0)
                self.model_var.set(self.available_models[0])
        else:
            self.model_listbox.configure(state="disabled")
            self.rename_button.configure(state="disabled")
            self.delete_button.configure(state="disabled")

    def _refresh_ui(self):
        """Обновляет интерфейс приложения"""
        # Проверяем, не происходит ли уже обновление
        if hasattr(self, '_refreshing'):
            return
        self._refreshing = True
        
        try:
            # Обновляем списки датасетов
            self.get_annotated_datasets()
            self.get_tested_datasets()
        finally:
            self._refreshing = False

    def _get_available_models(self):
        """Проверяет наличие скачанных моделей."""
        models_dir = DATA_DIR / "models"
        if not models_dir.exists():
            return []

        models = sorted(list([f.name for f in models_dir.glob("*.pt")]))
        # models_trained = list([f.parent.parent.name + "/" + f.name for f in Path(DATA_DIR).glob("**/best.pt")])
        return models  # + models_trained

    def _download_model(self, model_name):
        """Cкачивания модели."""
        from ml.yolo import ensure_model_downloaded
        _ = ensure_model_downloaded(model_name)
        #  model = YOLO(model_path)

        messagebox.showinfo("Модель загружена", f"Модель {model_name} успешно скачана.")
        # Обновляем список моделей
        self._refresh_models_list()

    def _download_user_model(self):
        """Cкачивания модели."""
        filepath = filedialog.askopenfilename(
            title="Загрузить модель",
            filetypes=[("PyTorch Model", "*.pt")]
        )
        if not filepath:
            return

        models_dir = DATA_DIR / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        dest_path = models_dir / Path(filepath).name

        if dest_path.exists() and dest_path.is_file():
            dest_path = models_dir / (Path(filepath).name[:-3] + '_2.pt')

        try:
            shutil.copy2(Path(filepath), dest_path)
            messagebox.showinfo("Модель загружена", f"Модель {Path(filepath).name} успешно скачана.")
            # Обновляем список моделей
            self._refresh_models_list()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при загрузке файла: {str(e)}")

    def _open_training_popup(self):
        """Открывает окно настроек обучения"""
        if not self.selected_datasets:
            messagebox.showwarning("Внимание", "Не выбраны датасеты для обучения")
            return

        popup = tk.Toplevel(self.root)
        popup.title("Настройки обучения")
        popup.geometry("400x500")

        tk.Label(popup, text="Параметры обучения:", font=("Arial", 12, "bold")).pack(pady=10)

        # Параметры
        params_frame = tk.Frame(popup)
        params_frame.pack(pady=10)

        tk.Label(params_frame, text="Batch Size:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        batch_entry = tk.Entry(params_frame)
        batch_entry.insert(0, "16")
        batch_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(params_frame, text="Epochs:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        epoch_entry = tk.Entry(params_frame)
        epoch_entry.insert(0, "100")
        epoch_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(params_frame, text="Imgs size:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        imgsz_entry = tk.Entry(params_frame)
        imgsz_entry.insert(0, "640")
        imgsz_entry.grid(row=2, column=1, padx=5, pady=5)

        tk.Label(params_frame, text="Workers:").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        workers_entry = tk.Entry(params_frame)
        workers_entry.insert(0, "0")
        workers_entry.grid(row=3, column=1, padx=5, pady=5)

        tk.Label(params_frame, text="Модель:").grid(row=4, column=0, sticky="e", padx=5, pady=5)
        model_label = tk.Label(params_frame, text=self.model_var.get())
        model_label.grid(row=4, column=1, padx=5, pady=5)

        def validate_char(entry_text):
            return "/" not in entry_text

        vcmd = (self.root.register(validate_char), '%P')
        tk.Label(params_frame, text="Ваше имя модели:").grid(row=5, column=0, sticky="e", padx=5, pady=5)
        model_name_entry = tk.Entry(params_frame, validate="key", validatecommand=vcmd)
        model_name_entry.grid(row=5, column=1, padx=5, pady=5)
        model_name_entry.configure(validate="none")
        model_name_entry.insert(0, self.model_var.get().replace('.pt', '')[:8] + "_custom")
        model_name_entry.configure(validate="key")

        # Выбор устройства
        tk.Label(params_frame, text="Устройства:", font=("Arial", 12, "bold")).grid(row=6, column=0, sticky="e", padx=5, pady=5)

        def get_available_devices():
            # Проверяем доступность GPU, если доступно - добавляем в список
            devices = ["cpu"]  # Всегда доступен CPU

            if torch is not None and torch.cuda.is_available():
                # Если доступен GPU, добавляем его в список
                devices.append(f"cuda")

            if torch is not None and torch.backends.mps.is_available():
                # Если доступен MPS, добавляем его в список
                devices.append(f"mps")

            return devices

        device_var = tk.StringVar(value="cpu")
        device_menu = ttk.Combobox(params_frame, textvariable=device_var, values=get_available_devices(),
                                   state="readonly")
        device_menu.grid(row=6, column=1, padx=5, pady=5)

        # Выбор классов
        tk.Label(popup, text="Выбор классов:", font=("Arial", 12, "bold")).pack(pady=10)

        classes_frame = tk.Frame(popup)
        classes_frame.pack()

        class_vars = {}

        output_dir = DATA_DIR / "annotated_dataset"
        annotation_manager = AnnotationFileManager(os.path.join(output_dir, 'annotations.json'))

        classes = set()
        for dataset in self.selected_datasets:
            for anns in annotation_manager[str(output_dir / dataset.name)].values():
                for ann in anns:
                    classes.add(ann['text'])
        for i, class_name in enumerate(classes):
            var = tk.BooleanVar(value=True)
            cb = tk.Checkbutton(classes_frame, text=class_name, variable=var)
            cb.grid(row=i, column=0, sticky="w", padx=10, pady=2)
            class_vars[class_name] = var

        # Кнопка запуска обучения
        tk.Button(
            popup,
            text="Начать обучение",
            bg="#4CAF50",
            font=("Arial", 12, "bold"),
            command=lambda: self._start_training(
                popup,
                batch_entry.get(),
                epoch_entry.get(),
                imgsz_entry.get(),
                workers_entry.get(),
                model_name_entry.get(),
                device_var.get(),
                class_vars,
                self.selected_datasets
            )
        ).pack(pady=20)

        # Создаем текстовый виджет для вывода
        self.train_output = tk.Text(popup, height=15, wrap=tk.WORD)
        self.train_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Прогресс бар
        self.train_progress = ttk.Progressbar(popup, orient=tk.HORIZONTAL, length=300, mode='determinate')
        self.train_progress.pack(pady=5)

        # Метка для статуса
        self.train_status = tk.Label(popup, text="Готов к обучению...")
        self.train_status.pack()

    def _create_training_window(self, parent):
        """Создает окно для отображения прогресса обучения"""
        self.train_window = tk.Toplevel(self.root)
        self.train_window.title("Процесс обучения")
        self.train_window.geometry("800x600")

        # Текстовый вывод
        self.train_output = tk.Text(self.train_window, wrap=tk.WORD)
        self.train_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Прогресс-бар
        self.train_progress = ttk.Progressbar(self.train_window, orient=tk.HORIZONTAL, length=300, mode='determinate')
        self.train_progress.pack(pady=5)

        # Статус
        self.train_status = tk.Label(self.train_window, text="Готов к обучению...")
        self.train_status.pack()

        # Кнопка отмены
        tk.Button(
            self.train_window,
            text="Отменить обучение",
            command=self._cancel_training,
            bg="#ff6666"
        ).pack(pady=10)

        # Перенаправляем вывод
        sys.stdout = TextRedirector(self.train_output)
        sys.stderr = TextRedirector(self.train_output)
        
        # Закрываем окно настроек после создания окна прогресса
        if parent and parent.winfo_exists():
            parent.destroy()

    def _create_testing_window(self, parent):
        """Создает окно для отображения прогресса обучения"""
        self.test_window = tk.Toplevel(self.root)
        self.test_window.title("Процесс тестирования")
        self.test_window.geometry("800x600")

        # Текстовый вывод
        self.test_output = tk.Text(self.test_window, wrap=tk.WORD)
        self.test_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Прогресс-бар
        self.test_progress = ttk.Progressbar(self.test_window, orient=tk.HORIZONTAL, length=300, mode='determinate')
        self.test_progress.pack(pady=5)

        # Статус
        self.test_status = tk.Label(self.test_window, text="Готов к обучению...")
        self.test_status.pack()

        # Кнопка отмены
        tk.Button(
            self.test_window,
            text="Отменить тестирование",
            command=self._cancel_testing,
            bg="#ff6666"
        ).pack(pady=10)

        # Перенаправляем вывод
        sys.stdout = TextRedirector(self.test_output)
        sys.stderr = TextRedirector(self.test_output)
        
        # Закрываем окно настроек после создания окна прогресса
        if parent and parent.winfo_exists():
            parent.destroy()

    def _cancel_training(self):
        """Безопасная отмена обучения"""
        if hasattr(self, 'training_thread') and self.training_thread.is_alive():
            if messagebox.askyesno("Отмена", "Прервать обучение?\n\nПримечание: Обучение завершится после завершения текущей эпохи.", parent=self.train_window):
                self.training_cancelled = True
                self._safe_update_train_status("Обучение прерывается... (завершится после текущей эпохи)", warning=True)

                # Ждем завершения потока с более длительным таймаутом
                self.training_thread.join(timeout=30.0)
                
                # Сбрасываем флаг отмены
                self.training_cancelled = False
                
                # Пытаемся корректно закрыть окно через 1 секунду
                self.root.after(1000, self._safe_finalize_training)
        else:
            # Если поток не запущен, сбрасываем флаг
            if hasattr(self, '_training_started'):
                self._training_started = False

    def _cancel_testing(self):
        """Безопасная отмена тестирования"""
        if hasattr(self, 'testing_thread') and self.testing_thread.is_alive():
            if messagebox.askyesno("Отмена", "Прервать тестирование?", parent=self.test_window):
                self.testing_cancelled = True
                self._safe_update_test_status("Тестирование прерывается...", warning=True)

                # Пытаемся корректно закрыть окно через 1 секунду
                self.root.after(1000, self._safe_finalize_testing)
        else:
            # Если поток не запущен, сбрасываем флаг
            if hasattr(self, '_testing_started'):
                delattr(self, '_testing_started')

    def _run_training(self, batch, epochs, imgsz, workers, model_name, device):
        """Выполняет обучение модели с безопасным обновлением UI"""
        # Проверяем, что библиотеки загружены
        if torch is None or YOLO is None:
            self._safe_update_train_status("Ошибка: ML библиотеки не загружены", error=True)
            return
            
        try:
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            self._safe_update_train_status("Загрузка модели...")
            model_variant = self.model_var.get()
            print(f"[DEBUG] Выбранная модель: {model_variant}")
            print(f"[DEBUG] Доступные модели: {[f.name for f in (DATA_DIR / 'models').glob('*.pt')]}")
            
            # Для обучения всегда используем базовую модель (не обученную)
            base_model_name = model_variant.split('_custom')[0] + '.pt'
            if '_custom' not in model_variant:
                base_model_name = model_variant  # Если уже базовая модель
                
            print(f"[DEBUG] Используем базовую модель для обучения: {base_model_name}")
            
            # Проверяем, существует ли базовая модель
            model_path = DATA_DIR / 'models' / base_model_name
            if not model_path.exists():
                self._safe_update_train_status(f"Ошибка: Базовая модель {base_model_name} не найдена", error=True)
                return
                
            try:
                model = YOLO(model_path)
                print(f"[DEBUG] Загружена базовая модель для обучения: {model_path}")
            except Exception as e:
                self._safe_update_train_status(f"Ошибка загрузки модели: {str(e)}", error=True)
                return

            # Проверяем данные перед обучением
            data_yaml_path = DATA_DIR / "data" / model_name / 'data.yaml'
            if not data_yaml_path.exists():
                self._safe_update_train_status("Ошибка: Файл data.yaml не найден", error=True)
                return
                
            # Проверяем содержимое data.yaml
            try:
                import yaml
                with open(data_yaml_path, 'r', encoding='utf-8') as f:
                    data_config = yaml.safe_load(f)
                
                # Проверяем количество классов
                if 'nc' in data_config:
                    num_classes = data_config['nc']
                    print(f"[DEBUG] Количество классов в data.yaml: {num_classes}")
                    
                    if num_classes == 0:
                        self._safe_update_train_status("Ошибка: Нет классов в датасете", error=True)
                        return
                        
                    if num_classes == 1:
                        print("[WARNING] Только один класс в датасете - это может вызвать проблемы")
                        
                # Проверяем имена классов
                if 'names' in data_config:
                    class_names = data_config['names']
                    print(f"[DEBUG] Имена классов: {class_names}")
                    
                    # Проверяем, что индексы классов корректны
                    if len(class_names) != num_classes:
                        print(f"[WARNING] Несоответствие: {len(class_names)} имен классов, но {num_classes} классов")
                        
                # Проверяем пути к данным
                if 'train' in data_config:
                    train_path = Path(data_config['train'])
                    if not train_path.exists():
                        self._safe_update_train_status("Ошибка: Путь к тренировочным данным не найден", error=True)
                        return
                        
                if 'val' in data_config:
                    val_path = Path(data_config['val'])
                    if not val_path.exists():
                        self._safe_update_train_status("Ошибка: Путь к валидационным данным не найден", error=True)
                        return
                        
                # Проверяем файлы разметки
                train_labels_path = Path(data_config.get('train', '')).parent / 'labels'
                if train_labels_path.exists():
                    label_files = list(train_labels_path.glob('*.txt'))
                    print(f"[DEBUG] Найдено файлов разметки: {len(label_files)}")
                    
                    # Проверяем первые несколько файлов на корректность индексов
                    max_class_idx = 0
                    for label_file in label_files[:5]:  # Проверяем первые 5 файлов
                        try:
                            with open(label_file, 'r') as f:
                                lines = f.readlines()
                                for line in lines:
                                    parts = line.strip().split()
                                    if len(parts) >= 5:
                                        class_idx = int(parts[0])
                                        max_class_idx = max(max_class_idx, class_idx)
                                        if class_idx >= num_classes:
                                            print(f"[WARNING] Неправильный индекс класса {class_idx} в файле {label_file}")
                        except Exception as e:
                            print(f"[WARNING] Ошибка чтения файла {label_file}: {e}")
                    
                    print(f"[DEBUG] Максимальный индекс класса в разметке: {max_class_idx}")
                    if max_class_idx >= num_classes:
                        print(f"[WARNING] Индексы классов превышают количество классов! Максимум: {max_class_idx}, классов: {num_classes}")
                        # Предлагаем исправить data.yaml
                        try:
                            # Обновляем количество классов в data.yaml
                            data_config['nc'] = max_class_idx + 1
                            with open(data_yaml_path, 'w', encoding='utf-8') as f:
                                yaml.dump(data_config, f, default_flow_style=False)
                            print(f"[DEBUG] Исправлен data.yaml: количество классов = {max_class_idx + 1}")
                        except Exception as e:
                            print(f"[ERROR] Не удалось исправить data.yaml: {e}")
                        
            except Exception as e:
                print(f"[DEBUG] Ошибка при проверке data.yaml: {e}")
                # Продолжаем обучение, но с предупреждением

            # Проверяем, что модель была успешно загружена
            if 'model' not in locals() or model is None:
                self._safe_update_train_status("Ошибка: Модель не была загружена", error=True)
                return
                
            self._safe_update_train_status("Начинаем обучение...")
            self._safe_set_progress_max(epochs)

            for epoch in range(epochs):
                if getattr(self, 'training_cancelled', False):
                    self._safe_update_train_status("Обучение прервано", warning=True)
                    break

                self._safe_update_train_status(f"Эпоха {epoch}/{epochs}")
                self._safe_set_progress(epoch + 1)

                custom_project_dir = DATA_DIR / "data" / model_name / "result"

                # Проверяем отмену перед началом обучения
                if getattr(self, 'training_cancelled', False):
                    self._safe_update_train_status("Обучение прервано", warning=True)
                    break

                results = model.train(
                    data=str(DATA_DIR / "data" / model_name / 'data.yaml'),
                    epochs=1,
                    batch=batch,
                    imgsz=imgsz,
                    device=device,
                    workers=workers,
                    name=model_name,
                    pretrained=True,
                    optimizer='AdamW',
                    verbose=True,
                    project=str(custom_project_dir),
                    exist_ok=True  # Разрешаем перезапись
                )

                # Проверяем отмену после завершения эпохи
                if getattr(self, 'training_cancelled', False):
                    self._safe_update_train_status("Обучение прервано", warning=True)
                    break

            if not getattr(self, 'training_cancelled', False):
                self._safe_update_train_status("Обучение завершено!", success=True)

        except Exception as e:
            error_msg = f"Ошибка: {str(e)}"
            print(f"[TRAINING ERROR] {error_msg}")
            print(f"[TRAINING ERROR] Exception type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            tb = traceback.format_exc()
            
            test_log_path = Path(sys.executable).parent / "test_log.txt"
            with open(test_log_path, "a") as f:
                f.write(f"[TRAINING ERROR] {error_msg}\n")
                f.write(f"[TRAINING ERROR] Exception type: {type(e).__name__}\n")
                f.write(f"[TRAINING ERROR] Traceback:\n{tb}\n")
            
            # Дополнительная диагностика для типичных ошибок
            if "index" in str(e) and "out of bounds" in str(e):
                error_msg += "\n\nВозможные причины:\n"
                error_msg += "1. Недостаточно классов в датасете\n"
                error_msg += "2. Проблема с разметкой - неправильные индексы классов\n"
                error_msg += "3. Конфликт версий библиотек\n"
                error_msg += "4. Проблема с форматом данных YAML\n\n"
                error_msg += "Попробуйте:\n"
                error_msg += "- Добавить больше изображений с разметкой\n"
                error_msg += "- Проверить, что все классы имеют аннотации\n"
                error_msg += "- Убедиться, что индексы классов начинаются с 0\n"
                error_msg += "- Обновить ultralytics: pip install --upgrade ultralytics\n"
                error_msg += "- Проверить файл data.yaml на корректность"
            
            self._safe_update_train_status(error_msg, error=True)
        finally:
            # Корректное освобождение ресурсов
            if 'model' in locals() and model is not None:
                try:
                    model.model.cpu()  # Переводим модель на CPU перед удалением
                    del model

                    best_pt_path = custom_project_dir / model_name / "weights" / "best.pt"
                    destination_path = DATA_DIR / "models" / f"{model_name}_best.pt"
                    if best_pt_path.exists():
                        shutil.copy2(best_pt_path, destination_path)
                        print(f"[DEBUG] Обученная модель скопирована: {destination_path}")
                except:
                    pass

            # Очистка памяти
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            # Принудительный сборщик мусора
            import gc
            gc.collect()

            # Восстановление стандартных потоков
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

            # Сбрасываем флаги обучения
            if hasattr(self, '_training_started'):
                self._training_started = False
            self.training_cancelled = False

            self._safe_finalize_training()

    def _run_testing(self, path_to_yaml, path_to_result, path_to_test_images, batch, imgsz, conf, iou, device):
        """Выполняет обучение модели с безопасным обновлением UI"""
        # Проверяем, что библиотеки загружены
        if torch is None or YOLO is None:
            self._safe_update_test_status("Ошибка: ML библиотеки не загружены", error=True)
            return
            
        try:
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            self._safe_update_test_status("Загрузка модели...")
            model_variant = self.model_var.get()
            model = YOLO(DATA_DIR / 'models' / model_variant)

            self._safe_update_test_status("Начинаем тестирование...")

            if getattr(self, 'testing_cancelled', False):
                self._safe_update_test_status("Тестирование прервано", warning=True)
                return

            # Создаем отдельные папки для val и predict
            val_result_path = str(Path(path_to_result) / "val")
            predict_result_path = str(Path(path_to_result) / "predict")
            
            # Создаем папки если их нет
            os.makedirs(val_result_path, exist_ok=True)
            os.makedirs(predict_result_path, exist_ok=True)
            
            print(f"DEBUG: val_result_path = {val_result_path}")
            print(f"DEBUG: predict_result_path = {predict_result_path}")
            print(f"DEBUG: path_to_test_images = {path_to_test_images}")

            results = model.val(
                data=path_to_yaml,  # путь к data.yaml
                split='test',  # использование тестового набора (должен быть указан в data.yaml)
                batch=batch,  # размер батча
                imgsz=imgsz,  # разрешение изображений
                conf=conf,  # порог уверенности для детекции
                iou=iou,  # порог IoU для NMS
                device=device,  # GPU (если доступен)
                project=val_result_path
            )

            # Перезагружаем модель
            model = YOLO(DATA_DIR / 'models' / model_variant)
            print(f"DEBUG: Запуск predict с параметрами:")
            print(f"  source={path_to_test_images}")
            print(f"  project={predict_result_path}")
            print(f"  conf=0.5")
            
            model.predict(
                source=path_to_test_images,
                save=True,
                conf=0.5,
                project=predict_result_path,
                name=".",
                exist_ok=True
            )
            
            print(f"DEBUG: predict завершен")
            print(f"DEBUG: Проверяем содержимое {predict_result_path}:")
            if os.path.exists(predict_result_path):
                for item in os.listdir(predict_result_path):
                    print(f"  - {item}")
            else:
                print(f"  Папка {predict_result_path} не существует!")

            if not getattr(self, 'testing_cancelled', False):
                self._safe_update_test_status("Тестирование завершено!", success=True)

        except Exception as e:
            self._safe_update_test_status(f"Ошибка: {str(e)}", error=True)
        finally:
            # Корректное освобождение ресурсов
            if model is not None:
                try:
                    model.model.cpu()  # Переводим модель на CPU перед удалением
                    del model
                except:
                    print("cannot delete model")
                    pass

            # Очистка памяти
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            # Принудительный сборщик мусора
            import gc
            gc.collect()

            # Восстановление стандартных потоков
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

            self._safe_finalize_testing()

    def _safe_update_train_status(self, message, success=False, error=False, warning=False):
        """Безопасное обновление статуса"""

        def update():
            if hasattr(self, 'train_status') and self.train_status.winfo_exists():
                self.train_status.config(text=message)
                if success:
                    self.train_status.config(fg="green")
                elif error:
                    self.train_status.config(fg="red")
                elif warning:
                    self.train_status.config(fg="orange")
                else:
                    self.train_status.config(fg="black")

        try:
            self.root.after(0, update)
        except:
            pass

    def _safe_update_test_status(self, message, success=False, error=False, warning=False):
        """Безопасное обновление статуса"""

        def update():
            if hasattr(self, 'test_status') and self.test_status.winfo_exists():
                self.test_status.config(text=message)
                if success:
                    self.test_status.config(fg="green")
                elif error:
                    self.test_status.config(fg="red")
                elif warning:
                    self.test_status.config(fg="orange")
                else:
                    self.test_status.config(fg="black")

        try:
            self.root.after(0, update)
        except:
            pass

    def _safe_set_progress(self, value):
        """Безопасное обновление прогресс-бара"""

        def update():
            if hasattr(self, 'train_progress') and self.train_progress.winfo_exists():
                self.train_progress["value"] = value

        try:
            self.root.after(0, update)
        except:
            pass

    def _safe_set_progress_max(self, max_value):
        """Безопасная установка максимума прогресс-бара"""

        def update():
            if hasattr(self, 'train_progress') and self.train_progress.winfo_exists():
                self.train_progress["maximum"] = max_value

        try:
            self.root.after(0, update)
        except:
            pass

    def _start_training(self, popup, batch, epochs, imgsz, workers, model_name, device, class_vars, datasets):
        """Запускает обучение в отдельном потоке"""
        # Проверяем, не запущено ли уже обучение
        if hasattr(self, '_training_started'):
            messagebox.showwarning("Внимание", "Обучение уже запущено")
            return
        self._training_started = True
        
        from ml.yolo import prepare_yolo_dataset
        self.training_cancelled = False
        try:
            batch = int(batch)
            epochs = int(epochs)
            imgsz = int(imgsz)
            workers = int(workers)
        except Exception as e:
            self._show_error(f"Неверный формат: {e}")
            self._training_started = False
            return

        if not self.model_var:
            self._show_error("Не выбрана модель")
            self._training_started = False
            return

        # Создаем окно для отображения прогресса
        self._create_training_window(popup)

        # Подготовка данных в основном потоке
        selected_classes = [name for name, var in class_vars.items() if var.get()]
        if not selected_classes:
            messagebox.showwarning("Внимание", "Выберите хотя бы один класс для обучения")
            self._training_started = False
            return
        selected_datasets = [dataset.name for dataset in datasets]

        JSON_PATH = DATA_DIR / "annotated_dataset/annotations.json"
        IMAGES_DIR = DATA_DIR / "annotated_dataset"

        self._update_train_status("Подготовка датасета...")
        prepare_yolo_dataset(
            json_path=JSON_PATH,
            images_source_dir=IMAGES_DIR,
            dir_names=selected_datasets,
            output_base_dir=str(DATA_DIR / "data" / model_name),
            class_names=selected_classes,
            train_ratio=0.8,
            seed=42,
            default_img_ext=".jpg",
            copy_files=True
        )

        # Запускаем обучение в отдельном потоке
        self.training_thread = threading.Thread(
            target=self._run_training,
            args=(batch, epochs, imgsz, workers, model_name, device),
            daemon=True
        )
        self.training_thread.start()

    def _open_testing_popup(self):
        # Проверка выбранных датасетов
        if not self.selected_datasets:
            messagebox.showwarning("Внимание", "Не выбраны датасеты для тестирования")
            return

        popup = tk.Toplevel(self.root)
        popup.title("Тестирование модели")
        popup.geometry("400x500")

        # Параметры
        params_frame = tk.Frame(popup)
        params_frame.pack(pady=10)

        tk.Label(params_frame, text="Batch Size:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        batch_entry = tk.Entry(params_frame)
        batch_entry.insert(0, "16")
        batch_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(params_frame, text="Imgs size:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        imgsz_entry = tk.Entry(params_frame)
        imgsz_entry.insert(0, "640")
        imgsz_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(params_frame, text="Conf:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        conf_entry = tk.Entry(params_frame)
        conf_entry.insert(0, "0.5")
        conf_entry.grid(row=2, column=1, padx=5, pady=5)

        tk.Label(params_frame, text="Iou:").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        iou_entry = tk.Entry(params_frame)
        iou_entry.insert(0, "0.5")
        iou_entry.grid(row=3, column=1, padx=5, pady=5)

        # Выбор устройства
        tk.Label(params_frame, text="Устройства:", font=("Arial", 12, "bold")).grid(row=6, column=0, sticky="e", padx=5,
                                                                                    pady=5)

        def get_available_devices():
            # Проверяем доступность GPU, если доступно - добавляем в список
            devices = ["cpu"]  # Всегда доступен CPU

            if torch is not None and torch.cuda.is_available():
                # Если доступен GPU, добавляем его в список
                devices.append(f"cuda")

            if torch is not None and torch.backends.mps.is_available():
                # Если доступен MPS, добавляем его в список
                devices.append(f"mps")

            return devices

        device_var = tk.StringVar(value="cpu")
        device_menu = ttk.Combobox(params_frame, textvariable=device_var, values=get_available_devices(),
                                   state="readonly")
        device_menu.grid(row=6, column=1, padx=5, pady=5)

        # Выбор классов
        tk.Label(popup, text="Выбор классов:", font=("Arial", 12, "bold")).pack(pady=10)

        classes_frame = tk.Frame(popup)
        classes_frame.pack()

        class_vars = {}

        output_dir = DATA_DIR / "annotated_dataset"
        annotation_manager = AnnotationFileManager(os.path.join(output_dir, 'annotations.json'))

        classes = set()
        for dataset in self.selected_datasets:
            if annotation_manager[str(output_dir / dataset.name)]:
                for anns in annotation_manager[str(output_dir / dataset.name)].values():
                    for ann in anns:
                        classes.add(ann['text'])
        for i, class_name in enumerate(classes):
            var = tk.BooleanVar(value=True)
            cb = tk.Checkbutton(classes_frame, text=class_name, variable=var)
            cb.grid(row=i, column=0, sticky="w", padx=10, pady=2)
            class_vars[class_name] = var

        if not classes:
            tk.Label(params_frame, text="Класс:").grid(row=7, column=0, sticky="e", padx=5, pady=5)
            class_entry = tk.Entry(params_frame)
            class_entry.insert(0, "ваш_класс")
            class_entry.grid(row=7, column=1, padx=5, pady=5)

        # Кнопка запуска тестирования
        tk.Button(
            popup,
            text="Начать тестирование",
            bg="#2196F3",
            font=("Arial", 12, "bold"),
            command=lambda: self._start_testing(
                popup,
                class_vars if classes else class_entry.get(),
                self.selected_datasets,
                batch_entry.get(), imgsz_entry.get(), conf_entry.get(), iou_entry.get(), device_var.get()
            )
        ).pack(pady=20)

    def _start_testing(self, popup, class_vars, datasets, batch, imgsz, conf, iou, device):
        # Проверяем, не запущено ли уже тестирование
        if hasattr(self, '_testing_started'):
            messagebox.showwarning("Внимание", "Тестирование уже запущено")
            return
        self._testing_started = True
        
        # Создаем окно для отображения прогресса
        from ml.yolo import prepare_yolo_dataset
        self.testing_cancelled = False
        try:
            batch = int(batch)
            conf = float(conf)
            imgsz = int(imgsz)
            iou = float(iou)
        except Exception as e:
            self._show_error(f"Неверный формат: {e}")
            self._testing_started = False
            return
        self._create_testing_window(popup)

        # Получить выбранные классы
        if isinstance(class_vars, str):
            selected_classes = [class_vars]
        else:
            selected_classes = [name for name, var in class_vars.items() if var.get()]
        if not selected_classes:
            messagebox.showwarning("Внимание", "Выберите хотя бы один класс для тестирования")
            return

        selected_datasets = [dataset.name for dataset in datasets]

        JSON_PATH = DATA_DIR / "annotated_dataset/annotations.json"
        IMAGES_DIR = DATA_DIR / "annotated_dataset"

        self._safe_update_test_status("Подготовка датасетов...")
        output_base_dir = DATA_DIR / "data" / "test" / selected_datasets[0]
        prepare_yolo_dataset(
            json_path=JSON_PATH,
            images_source_dir=IMAGES_DIR,
            dir_names=selected_datasets,
            output_base_dir=str(output_base_dir),
            class_names=selected_classes,
            seed=42,
            default_img_ext=".jpg",
            copy_files=True,
            test=True
        )

        # Запускаем тестирование в отдельном потоке
        self.testing_thread = threading.Thread(
            target=self._run_testing,
            args=(
                str(output_base_dir / "data.yaml"),
                str(output_base_dir / "result"),
                str(output_base_dir / "test" / "images"),
                batch, imgsz, conf, iou, device
            ),
            daemon=True
        )
        self.testing_thread.start()
        # self._add_tested_dataset_panel(selected_datasets, selected_classes)

    def _setup_tested_datasets_panel(self):
        """Настройка панели протестированных датасетов"""
        # Проверяем, не происходит ли уже настройка панели
        # if hasattr(self, '_tested_panel_setup_done'):
        #     return
        # self._tested_panel_setup_done = True
        
        # Очищаем предыдущие элементы
        for widget in self.tested_scrollable_frame.winfo_children():
            widget.destroy()

        # Добавляем заголовок
        tk.Label(
            self.tested_scrollable_frame,
            text="История тестирования",
            font=("Arial", 10, "bold"),
            bg="white"
        ).pack(anchor="w", pady=5)

        # Получаем список датасетов
        test_dir = DATA_DIR / "data" / "test"
        if not test_dir.exists():
            return
        output_dir = DATA_DIR / "annotated_dataset"
        sub_folders = [f for f in test_dir.iterdir() if f.is_dir()]
        json_manager = JsonManager(os.path.join(output_dir, 'hash_to_name.json'))

        # Параметры сетки
        ITEMS_PER_ROW = 3
        ITEM_WIDTH = 350
        PREVIEW_SIZE = 150

        # Контейнер для сетки
        grid_container = tk.Frame(self.tested_scrollable_frame, bg="white")
        grid_container.pack(fill=tk.BOTH, expand=True)

        # Настройка столбцов
        for col in range(ITEMS_PER_ROW):
            grid_container.columnconfigure(col, weight=1)

        for i, sub_folder in enumerate(sub_folders):
            print("DEBUG", sub_folder.name)
            real_name = Path(json_manager[sub_folder.name]).name
            # Ищем результаты предсказаний в новой структуре папок
            predict_folder = Path(sub_folder) / "predict"
            if not predict_folder.exists():
                # Fallback к старой структуре
                images_folder = Path(sub_folder) / "result" / "predict"
            else:
                images_folder = predict_folder

            # Фрейм для одного датасета
            item_frame = tk.Frame(
                grid_container,
                width=ITEM_WIDTH,
                height=ITEM_WIDTH + 60,
                bg="white",
                bd=1,
                relief=tk.RAISED,
                highlightbackground="#e0e0e0",
                highlightthickness=1
            )
            item_frame.grid(
                row=i // ITEMS_PER_ROW,
                column=i % ITEMS_PER_ROW,
                padx=10,
                pady=10,
                sticky="nsew"
            )
            item_frame.grid_propagate(False)

            # Контейнер для изображения
            img_container = tk.Frame(item_frame, bg="white", height=PREVIEW_SIZE + 10)
            img_container.pack(fill=tk.X, pady=(25, 5))
            img_container.pack_propagate(False)

            # Загрузка превью изображения
            image_files = list(
                sorted(
                    list(images_folder.glob("*.jpg")) +
                    list(images_folder.glob("*.jpeg")) +
                    list(images_folder.glob("*.png")) +
                    list(images_folder.glob("*.gif"))
                )
            )

            if image_files:
                try:
                    from PIL import Image, ImageTk
                    img = Image.open(image_files[0])
                    img.thumbnail((PREVIEW_SIZE, PREVIEW_SIZE))
                    photo = ImageTk.PhotoImage(img)

                    img_label = tk.Label(img_container, image=photo, bg="white", cursor="hand")
                    img_label.image = photo
                    img_label.pack()
                    img_label.bind("<Button-1>", lambda _, s=images_folder: self._open_dataset(s))
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
                cursor="hand"
            )
            name_label.pack(fill=tk.X, padx=5, pady=(0, 5))

            stat_frame = tk.Frame(item_frame, bg="white")
            stat_frame.pack(fill=tk.X, pady=(0, 5))

            # Кнопка скачивания
            edit_btn = tk.Button(
                stat_frame,
                text="↓️",
                fg="blue",
                bg="white",
                bd=0,
                font=("Arial", 12, "bold"),
                command=lambda s=images_folder, test=True: self._download_dataset(s, test)
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
                command=lambda s=images_folder: self._remove_tested_dataset(s)
            )
            del_btn.pack(side=tk.RIGHT, padx=5)

    def _open_dataset(self, folder_path):
        output_dir = DATA_DIR / "annotated_dataset"
        annotated_path = output_dir / folder_path.parent.parent.name

        if annotated_path.exists():
            popover = AnnotationPopover(
                self.root,
                self,
                readonly=True,
                annotated_path=annotated_path
            )
        else:
            popover = AnnotationPopover(
                self.root,
                self,
                readonly=True
            )

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

    def _remove_tested_dataset(self, folder_path):
        self.deleter_test.delete_datasets([folder_path])
        self._refresh_tested_datasets_only()

    def _safe_finalize_training(self):
        """Безопасное завершение обучения"""
        # Проверяем, не происходит ли уже завершение
        if hasattr(self, '_finalizing_training'):
            return
        self._finalizing_training = True

        def finalize():
            try:
                if hasattr(self, 'train_window') and self.train_window.winfo_exists():
                    if not getattr(self, 'training_cancelled', False):
                        messagebox.showinfo("Готово", "Обучение модели завершено!", parent=self.train_window)
                    self.train_window.destroy()
                    # Обновляем списки датасетов и моделей
                    print(f"[DEBUG] Обновляем интерфейс после завершения обучения")
                    self._refresh_annotated_datasets_only()
                    self._refresh_models_list()
                    self._refresh_tested_datasets_only()
                    
                    # Показываем уведомление о новой модели
                    if not getattr(self, 'training_cancelled', False):
                        # Ищем новую обученную модель
                        models_dir = DATA_DIR / "models"
                        new_models = [f for f in models_dir.glob(f"*_best.pt") if f.stat().st_mtime > time.time() - 60]  # Модели созданные за последнюю минуту
                        if new_models:
                            latest_model = max(new_models, key=lambda x: x.stat().st_mtime)
                            messagebox.showinfo("Новая модель", f"Обученная модель '{latest_model.name}' добавлена в список!")
            finally:
                self._finalizing_training = False
                # Сбрасываем флаг запуска обучения
                if hasattr(self, '_training_started'):
                    delattr(self, '_training_started')

        try:
            self.root.after(0, finalize)
        except:
            self._finalizing_training = False

    def _safe_finalize_testing(self):
        """Безопасное завершение тестирования"""
        # Проверяем, не происходит ли уже завершение
        if hasattr(self, '_finalizing_testing'):
            return
        self._finalizing_testing = True

        def finalize():
            try:
                if hasattr(self, 'test_window') and self.test_window.winfo_exists():
                    if not getattr(self, 'testing_cancelled', False):
                        messagebox.showinfo("Готово", "Тестирование модели завершено!", parent=self.test_window)
                    self.test_window.destroy()
                    # Обновляем списки датасетов
                    self._refresh_annotated_datasets_only()
                    self._refresh_tested_datasets_only()
            finally:
                self._finalizing_testing = False
                # Сбрасываем флаг запуска тестирования
                if hasattr(self, '_testing_started'):
                    delattr(self, '_testing_started')

        try:
            self.root.after(0, finalize)
        except:
            self._finalizing_testing = False

    def _update_train_status(self, message, success=False, error=False):
        """Обновляет статус обучения в UI"""

        def update():
            self.train_status.config(text=message)
            if success:
                self.train_status.config(fg="green")
            elif error:
                self.train_status.config(fg="red")
            else:
                self.train_status.config(fg="black")

        # Выполняем обновление в основном потоке
        self.root.after(0, update)

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
            image_files = list(sorted(
                list(sub_folder.glob("*.jpg")) +
                list(sub_folder.glob("*.jpeg")) +
                list(sub_folder.glob("*.png")) +
                list(sub_folder.glob("*.gif"))
            ))

            if image_files:
                try:
                    from PIL import Image, ImageTk
                    print(f"[INFO] Loading image: {image_files[0]}")
                    img = Image.open(image_files[0])
                    img.thumbnail((PREVIEW_SIZE, PREVIEW_SIZE))
                    photo = ImageTk.PhotoImage(img)

                    img_label = tk.Label(img_container, image=photo, bg="white", cursor="hand")
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
                cursor="hand"
            )
            name_label.pack(fill=tk.X, padx=5, pady=(0, 5))
            name_label.bind("<Button-1>", lambda _, s=sub_folder: self._modify_dataset(s))

            # Статистика и кнопки управления
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

            # Кнопка скачивания (стрелка вниз)
            download_btn = tk.Button(
                stat_frame,
                text="↓",
                fg="green",
                bg="white",
                bd=0,
                font=("Arial", 12, "bold"),
                command=lambda s=sub_folder: self._download_dataset(s)
            )
            download_btn.pack(side=tk.RIGHT, padx=2)

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
            edit_btn.pack(side=tk.RIGHT, padx=2)

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
            del_btn.pack(side=tk.RIGHT, padx=2)

            self.annotated_datasets.append(item_frame)

    def _refresh_annotated_datasets_only(self):
        """Обновляет только панель аннотированных датасетов без пересоздания всего UI"""
        # Просто вызываем оригинальный метод, так как он уже безопасен
        self.get_annotated_datasets()

    def _download_dataset(self, dataset_folder, test=False):
        """Метод для вызова из интерфейса"""
        output_dir = DATA_DIR / "annotated_dataset"
        hash_to_name_manager = JsonManager(os.path.join(output_dir, 'hash_to_name.json'))
        annotations_manager = JsonManager(os.path.join(output_dir, 'annotations.json'))
        blazons_manager = JsonManager(os.path.join(output_dir, 'blazons.json'))
        if not test:
            real_name = Path(hash_to_name_manager[dataset_folder.name]).name
            # Получаем аннотации для всего датасета
            dataset_path = str(output_dir / dataset_folder.name)
            annotations = annotations_manager[dataset_path] or {}
            print(f"Загруженные аннотации: {annotations}")
            blazons = blazons_manager[dataset_folder.name]
        else:
            real_name = Path(hash_to_name_manager[dataset_folder.parent.parent.name]).name
            annotations = None
            blazons = None

        # Спрашиваем пользователя о скачивании
        if test:
            format_choice = messagebox.askyesno(
                "Скачивание",
                f"Скачать протестированный датасет '{real_name}'?",
                parent=self.root
            )
        else:
            format_choice = messagebox.askyesnocancel(
                "Выбор формата",
                "Выберите формат скачивания:\n\n"
                "Yes - скачать аннотированные изображения (разметка будет на картинках)\n"
                "No - скачать оригинальные изображения + JSON файлы\n"
                "Cancel — отменить операцию",
                parent=self.root
            )

        # Показываем индикатор загрузки
        if format_choice is not None:
            self._show_loading_indicator()

        def download_complete_callback(success):
            """Коллбек для закрытия окна загрузки"""
            self.root.after(0, self.loading_popup.destroy)
            if success:
                messagebox.showinfo("Готово", f"Датасет '{real_name}' успешно скачан в папку Downloads!",
                                    parent=self.root)

        print("format_choice: ", format_choice)
        if format_choice is None:
            return
        elif format_choice == True:
            # Скачиваем изображения
            if test:
                # Для протестированных датасетов скачиваем изображения
                threading.Thread(
                    target=lambda: self._download_test_images(
                        dataset_folder,
                        real_name,
                        download_complete_callback
                    ),
                    daemon=True
                ).start()
            else:
                # Для аннотированных датасетов добавляем аннотации
                threading.Thread(
                    target=lambda: self._download_annotated_images(
                        dataset_folder,
                        real_name,
                        annotations,
                        download_complete_callback
                    ),
                    daemon=True
                ).start()
        elif format_choice == False:
            # Скачиваем оригинальные изображения + JSON (только для аннотированных датасетов)
            if not test:
                extra_data = [
                    (annotations, 'annotations.json'),
                    (blazons, 'blazons.json')
                ]
                threading.Thread(
                    target=lambda: download_dataset_with_notification(
                        self.root,
                        dataset_folder,
                        real_name,
                        extra_data,
                        download_complete_callback
                    ),
                    daemon=True
                ).start()
            

    def _download_annotated_images(self, dataset_folder, real_name, annotations, callback):
        """Скачивает датасет с аннотированными изображениями"""
        try:
            print("Начинаем скачивание аннотированных изображений")
            print(f"Путь к датасету: {dataset_folder}")
            print(f"Аннотации: {annotations}")

            # Создаем временную директорию
            temp_dir = Path(tempfile.mkdtemp())
            output_dir = temp_dir / real_name
            output_dir.mkdir(parents=True)

            # Копируем и аннотируем каждое изображение
            for image_path in dataset_folder.glob('*'):
                if image_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                    print(f"\nОбработка изображения: {image_path}")
                    # Открываем изображение
                    from PIL import Image, ImageDraw, ImageFont
                    img = Image.open(image_path)
                    img = img.convert('RGB')

                    print(f"{image_path.name} — mode: {img.mode}")
                    draw = ImageDraw.Draw(img)
                    
                    # Получаем аннотации для текущего изображения по имени файла
                    image_name = image_path.name
                    image_annotations = annotations.get(image_name, []) if annotations is not None else []
                    print(f"Аннотации для изображения {image_name}: {image_annotations}")
                    
                    # Рисуем аннотации на изображении
                    for ann in image_annotations:
                        print(f"Обработка аннотации: {ann}")
                        coords = ann['coords']
                        label = ann['text']
                        ratio = ann.get('ratio', 1.0)
                        # Преобразуем координаты обратно в оригинальный размер
                        x1 = coords[0] / ratio
                        y1 = coords[1] / ratio
                        x2 = coords[2] / ratio
                        y2 = coords[3] / ratio
                        print(f"Координаты (оригинал): {x1}, {y1}, {x2}, {y2}, ratio: {ratio}")
                        # Рисуем прямоугольник
                        draw.rectangle([x1, y1, x2, y2], outline='red', width=2)
                        # Рисуем текст
                        x_center = (x1 + x2) / 2
                        y_center = (y1 + y2) / 2
                        try:
                            font_path = get_resource_path('favicons/arial.ttf')
                            font = ImageFont.truetype(font_path, 14)
                        except OSError:
                            font = ImageFont.load_default()
                        text_bbox = draw.textbbox((x_center, y_center), label, font=font, anchor="mm")
                        draw.rectangle(
                            [text_bbox[0]-2, text_bbox[1]-2, text_bbox[2]+2, text_bbox[3]+2],
                            fill='white'
                        )
                        draw.text(
                            (x_center, y_center),
                            label,
                            fill='red',
                            font=font,
                            anchor="mm"
                        )
                    # Сохраняем аннотированное изображение
                    output_path = output_dir / image_path.name
                    img.save(output_path)
                    print(f"Изображение сохранено: {output_path}")

            # Создаем архив
            downloads_dir = Path.home() / "Downloads"
            archive_path = downloads_dir / f"{real_name}_annotated.zip"
            print(f"\nСоздание архива: {archive_path}")
            
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in output_dir.rglob('*'):
                    if file.is_file():
                        zipf.write(file, file.relative_to(output_dir))
                        print(f"Добавлен в архив: {file}")

            # Удаляем временную директорию
            shutil.rmtree(temp_dir)
            print("\nВременная директория удалена")
            
            callback(True)
        except Exception as e:
            print(f"Ошибка при скачивании аннотированных изображений: {str(e)}")
            import traceback
            traceback.print_exc()
            callback(False)

    def _download_test_images(self, dataset_folder, real_name, callback):
        """Скачивает протестированный датасет с изображениями"""
        try:
            print("Начинаем скачивание протестированных изображений")
            print(f"Путь к датасету: {dataset_folder}")

            # Создаем временную директорию
            temp_dir = Path(tempfile.mkdtemp())
            output_dir = temp_dir / real_name
            output_dir.mkdir(parents=True)

            # Копируем изображения
            for image_path in dataset_folder.glob('*'):
                if image_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                    print(f"\nКопирование изображения: {image_path}")
                    # Просто копируем изображение без изменений
                    output_path = output_dir / image_path.name
                    shutil.copy2(image_path, output_path)
                    print(f"Изображение скопировано: {output_path}")

            # Создаем архив
            downloads_dir = Path.home() / "Downloads"
            archive_path = downloads_dir / f"{real_name}_test.zip"
            print(f"\nСоздание архива: {archive_path}")
            
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in output_dir.rglob('*'):
                    if file.is_file():
                        zipf.write(file, file.relative_to(output_dir))
                        print(f"Добавлен в архив: {file}")

            # Удаляем временную директорию
            shutil.rmtree(temp_dir)
            print("\nВременная директория удалена")
            
            callback(True)
        except Exception as e:
            print(f"Ошибка при скачивании протестированных изображений: {str(e)}")
            import traceback
            traceback.print_exc()
            callback(False)

    def _show_loading_indicator(self):
        """Показывает индикатор загрузки"""
        self.loading_popup = tk.Toplevel(self.root)
        self.loading_popup.title("Подождите...")
        self.loading_popup.geometry("300x100")

        tk.Label(
            self.loading_popup,
            text="Идет создание архива...",
            font=('Arial', 11)
        ).pack(pady=10)

        progress = ttk.Progressbar(
            self.loading_popup,
            mode='indeterminate',
            length=200
        )
        progress.pack()
        progress.start()

        # Центрируем окно
        self._center_window(self.loading_popup)

    def _center_window(self, window):
        """Центрирует окно на экране"""
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f'+{x}+{y}')

    def get_tested_datasets(self):
        """Загружает список протестированных датасетов"""
        test_dir = DATA_DIR / "data" / "test"
        
        print(f"[DEBUG] Проверяем протестированные датасеты в: {test_dir}")
        print(f"[DEBUG] Директория существует: {test_dir.exists()}")

        # Очищаем предыдущие датасеты
        for dataset in self.tested_datasets:
            dataset.destroy()
        self.tested_datasets = []

        # Очищаем предыдущие элементы
        for widget in self.tested_scrollable_frame.winfo_children():
            widget.destroy()

        if not test_dir.exists():
            print(f"[DEBUG] Директория {test_dir} не существует")
            return

        print(f"[DEBUG] Найдены протестированные датасеты: {list(test_dir.iterdir())}")
        
        # Загружаем актуальные данные
        self._setup_tested_datasets_panel()

    def _refresh_tested_datasets_only(self):
        """Обновляет только панель протестированных датасетов без пересоздания всего UI"""
        print(f"[DEBUG] Обновляем протестированные датасеты")
        # Просто вызываем оригинальный метод, так как он уже безопасен
        self.get_tested_datasets()

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
        print(f"[DEBUG] _delete_single_dataset called. deleter id: {id(self.deleter)}, is_running: {getattr(self.deleter, 'is_running', None)}")
        self.deleter.delete_datasets([dataset_folder])
        # self._refresh_ui()  # УБРАТЬ эту строку!

    def _delete_selected_datasets(self):
        if not self.selected_datasets:
            messagebox.showwarning("Внимание", "Не выбраны датасеты для удаления")
            return
        self.deleter.delete_datasets(list(self.selected_datasets))
        self._refresh_ui()

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
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))
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

    def _show_popover(self, is_zip=False):
        """Показывает Popover с интерфейсом разметки"""
        popover = AnnotationPopover(self.root, self)

        # Центрируем Popover относительно главного окна
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 600
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 400
        popover.geometry(f"+{x}+{y}")

        # Пытаемся загрузить папку с картинками
        try:
            popover.load_folder(is_zip=is_zip)
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
                from PIL import Image
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
