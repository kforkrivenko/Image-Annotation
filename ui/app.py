import json
import os
import shutil
import subprocess
import sys
import tempfile
import tkinter as tk
import traceback
from pathlib import Path
import platform
from tkinter import ttk
from tkinter import filedialog, messagebox
from data_processing.image_loader import ImageLoader
from data_processing.annotation_saver import AnnotationSaver
from ui.canvas import AnnotationCanvas
from ui.widgets import ControlPanel
from data_processing.history_manager import DatasetHistoryManager
from ui.dataset_history import DatasetHistoryPanel


class ImageAnnotationApp:
    def __init__(self):
        self.root = tk.Tk()
        self._set_window_icon()
        self.root.title("Image Annotation Tool")

        # Главный контейнер для разделения на 2 части
        self.main_frame = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Левая часть: Canvas + кнопки
        self.left_frame = tk.Frame(self.main_frame)
        self.main_frame.add(self.left_frame)

        # Правая часть: История датасетов
        self.right_frame = tk.Frame(self.main_frame, width=200, bg="#f0f0f0")
        self.main_frame.add(self.right_frame)

        self._setup_left_ui()  # Canvas и кнопки
        self._setup_right_ui()  # История датасетов
        self._initialize_state()

        self._bind_events()

        # Инициализация переменных
        self.status_var = tk.StringVar()

    def _set_window_icon(self):
        """Устанавливает иконку в зависимости от ОС"""
        try:
            if sys.platform == 'darwin':  # macOS
                # Для .icns на macOS используем специальный метод
                icns_path = self._get_resource_path('favicons/favicon.icns')
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
                ico_path = self._get_resource_path('favicons/favicon.ico')
                if os.path.exists(ico_path):
                    self.root.iconbitmap(ico_path)

        except Exception as e:
            print(f"Ошибка установки иконки: {str(e)}")
            # Попробуем установить стандартную иконку Tkinter как fallback
            try:
                self.root.tk.call('wm', 'iconphoto', self.root._w,
                                  tk.PhotoImage(file=self._get_resource_path('favicons/favicon.png')))
            except:
                pass

    def _get_resource_path(self, relative_path):
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

    def _setup_left_ui(self):
        # Canvas для изображений
        self.canvas = AnnotationCanvas(self.left_frame)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Панель управления (кнопки)
        self.control_panel = ControlPanel(self.left_frame)
        self.control_panel.pack(pady=10)

    def _setup_right_ui(self):
        # Заголовок
        tk.Label(
            self.right_frame,
            text="Annotated Datasets",
            font=("Arial", 12, "bold"),
            bg="#f0f0f0"
        ).pack(pady=10)

        # Treeview для списка датасетов
        self.dataset_tree = ttk.Treeview(
            self.right_frame,
            columns=("Images"),
            show="headings",
            height=15
        )
        self.dataset_tree.heading("#0", text="Dataset Name")
        self.dataset_tree.heading("Images", text="Images Count")
        self.dataset_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Кнопка "Open Dataset"
        tk.Button(
            self.right_frame,
            text="Open Selected",
            command=self._open_selected_dataset,
            bg="#e1e1e1"
        ).pack(pady=5)

        # Обновляем список
        self._update_dataset_list()
        # Добавляем обработчик выбора в Treeview
        self.dataset_tree.bind("<<TreeviewSelect>>", self._on_dataset_selected)

    def _on_dataset_selected(self, event):
        """Обрабатывает выбор датасета в списке"""
        selected = self.dataset_tree.selection()
        if selected:
            self.selected_dataset = self.dataset_tree.item(selected[0])["text"]
            print(f"Выбран датасет: {self.selected_dataset}")  # Для отладки

    def _update_dataset_list(self):
        """Загружает список размеченных датасетов из annotations.json"""
        try:
            if Path("annotated_dataset/annotations.json").exists():
                with open("annotated_dataset/annotations.json", "r") as f:
                    data = json.load(f)
                    for folder_name in data.keys():
                        img_count = len(data[folder_name])
                        self.dataset_tree.insert(
                            "", "end",
                            text=folder_name,
                            values=(img_count,)
                        )
        except Exception as e:
            print(f"Error loading dataset list: {e}")

    def _open_selected_dataset(self):
        """Загружает выбранный датасет для продолжения работы"""
        selected = self.dataset_tree.selection()
        if not selected:
            return

        # 1. Получаем имя выбранного датасета
        dataset_name = self.dataset_tree.item(selected[0])["text"]

        # 2. Закрываем текущий датасет (если открыт)
        self._close_image()

        try:
            # 3. Загружаем информацию о датасете из истории
            history_file = Path("annotated_dataset/annotations.json")
            if not history_file.exists():
                raise FileNotFoundError("History file not found")

            with open(history_file, "r") as f:
                history_data = json.load(f)
                print(history_data, dataset_name)
                dataset_info = history_data.get(dataset_name)

                if not dataset_info:
                    raise ValueError("Dataset not found in history")

                # 4. Получаем ПУТЬ К ОРИГИНАЛЬНОЙ ПАПКЕ (не к аннотациям!)
                original_folder = dataset_info.get("original_path")
                if not original_folder or not Path(original_folder).exists():
                    raise FileNotFoundError("Original dataset folder not found")

                # 5. Инициализируем загрузчик с оригинальной папкой
                self.image_loader = ImageLoader(original_folder)
                self.annotation_saver = AnnotationSaver(original_folder)

                # 6. Загружаем первое изображение
                self._load_image()
                self._update_ui()

                messagebox.showinfo("Success", f"Dataset '{dataset_name}' loaded successfully")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load dataset: {str(e)}")
            print(f"Debug: {traceback.format_exc()}")  # Для отладки

    def _load_existing_dataset(self, dataset_path: Path):
        """Загружает ранее размеченный датасет"""
        try:
            # Проверяем существование аннотаций
            print(dataset_path)
            annotations_file = dataset_path / "annotations.json"
            if not annotations_file.exists():
                raise FileNotFoundError("Annotations file not found")

            # Инициализируем загрузчик
            self.image_loader = ImageLoader(str(dataset_path))
            self.annotation_saver = AnnotationSaver(str(dataset_path))

            # Загружаем первое изображение
            self._load_image()
            self._update_ui()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load dataset: {str(e)}")

    def _open_folder_in_explorer(self, path):
        """Открывает папку в системном проводнике"""
        try:
            path = str(path)  # Преобразуем Path в строку

            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", path])
            else:  # Linux и другие
                subprocess.run(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Error", f"Cannot open folder: {str(e)}")

    def _initialize_state(self):
        self.image_loader = None
        self.annotation_saver = None
        self.current_image = None
        self.current_image_path = None

    def _bind_events(self):
        self.control_panel.load_btn.config(command=self._load_folder)
        self.control_panel.prev_btn.config(command=self._prev_image)
        self.control_panel.next_btn.config(command=self._next_image)
        self.control_panel.close_btn.config(command=self._close_image)

    def _load_folder(self):
        """Открывает диалог выбора папки и загружает изображения"""
        folder_path = filedialog.askdirectory(title="Select Folder with Images")
        if not folder_path:  # Если пользователь отменил выбор
            return

        try:
            self.image_loader = ImageLoader(folder_path)
            self.annotation_saver = AnnotationSaver(folder_path)

            if not self.image_loader.image_files:
                messagebox.showerror("Error", "No images found in selected folder!")
                return

            self._load_image()
            self._update_ui()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load folder: {str(e)}")

    def _load_image(self):
        self.current_image = self.image_loader.get_image("next")
        self.current_image_path = self.image_loader.get_current_image_path()

        if self.current_image is None:
            messagebox.showinfo("Complete", "All images annotated!")
            return

        self.canvas.display_image(self.current_image, self.current_image_path)
        self._load_existing_annotations()

    def _load_existing_annotations(self):
        annotations = self.annotation_saver.get_annotations(self.current_image_path)
        for ann in annotations:
            self.canvas.add_annotation(ann)

    def _prev_image(self):
        self._save_current_annotations()
        self.current_image = self.image_loader.get_image("prev")
        self.current_image_path = self.image_loader.get_current_image_path()
        self.canvas.clear()  # Очищаем canvas перед загрузкой нового изображения
        self._update_image_display()

    def _next_image(self):
        self._save_current_annotations()
        self.current_image = self.image_loader.get_image("next")
        self.current_image_path = self.image_loader.get_current_image_path()
        self.canvas.clear()  # Очищаем canvas перед загрузкой нового изображения
        self._update_image_display()

    def _close_image(self):
        self.image_loader.current_index = -1
        self._save_current_annotations()
        self.canvas.clear()
        self._update_ui()
        self.control_panel.status_var.set("")

    def _save_current_annotations(self):
        try:
            if self.current_image_path and hasattr(self, 'annotation_saver'):
                annotations = self.canvas.get_annotations()
                full_image_path = os.path.join(
                    self.image_loader.folder_path,
                    self.current_image_path
                )
                if os.path.exists(full_image_path):
                    self.annotation_saver.save_annotations(full_image_path, annotations)
                else:
                    print(f"Warning: Image file not found: {full_image_path}")
        except Exception as e:
            print(f"Error saving annotations: {str(e)}")

    def _update_image_display(self):
        if self.current_image is not None and self.current_image_path is not None:
            self.canvas.clear()
            self.canvas.display_image(self.current_image, self.current_image_path)
            self._load_existing_annotations()
        self._update_ui()

    def _update_ui(self):
        if self.image_loader:
            self.control_panel.update_state(
                current_index=self.image_loader.current_index,
                total_images=len(self.image_loader.image_files),
                has_image=self.current_image is not None
            )

    def run(self):
        self.root.mainloop()
