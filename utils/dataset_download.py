import json
import os
import sys
import zipfile
import tempfile
from pathlib import Path
from tkinter import messagebox
import shutil
import subprocess
import platform
import tkinter as tk


def create_custom_zip(source_folder, zip_name=None, extra_json_data=None, output_dir=None):
    """
    Создает ZIP-архив с возможностью:
    - Указать имя архива
    - Добавить дополнительные файлы
    - Выбрать директорию для сохранения

    :param source_folder: Папка для архивирования
    :param zip_name: Имя ZIP-файла (без расширения)
    :param extra_json_data: Список дополнительных json-ов для включения
    :param output_dir: Директория для сохранения (None = временная папка)
    :return: Path к созданному ZIP-архиву
    """

    # Создаем временный файл для JSON, если есть дополнительные данные
    temp_json_paths = []

    if extra_json_data is not None:
        for extra_data, name in extra_json_data:
            if extra_data is not None:
                try:
                    # Создаем временный файл
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
                        json.dump(extra_data, tmp, indent=2, ensure_ascii=False)
                        temp_json_paths.append(
                            (Path(tmp.name), name)
                        )
                except Exception as e:
                    print(f"Ошибка создания временного JSON: {e}")

    # Определяем имя архива
    base_name = Path(source_folder).name if zip_name is None else zip_name
    zip_filename = f"{base_name}.zip"

    # Определяем директорию для сохранения
    if output_dir is None:
        output_dir = Path(tempfile.gettempdir())
    else:
        output_dir = Path(output_dir)

    zip_path = output_dir / zip_filename

    # Создаем архив
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Добавляем основную папку
        for root, _, files in os.walk(source_folder):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(source_folder)
                zipf.write(file_path, arcname)

        # Добавляем дополнительные файлы
        for file, name in temp_json_paths:
            file_path = Path(file)
            if file_path.exists():
                zipf.write(file_path, name)
            else:
                print(f"Предупреждение: Файл {file} не найден и не будет добавлен")

    return zip_path


def get_downloads_folder():
    """Возвращает путь к папке Downloads пользователя"""
    if os.name == 'nt':  # Windows
        import ctypes
        from ctypes import windll, wintypes
        CSIDL_PERSONAL = 5
        SHGFP_TYPE_CURRENT = 0

        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
        downloads = Path(buf.value) / 'Downloads'
    else:  # macOS и Linux
        downloads = Path.home() / 'Downloads'

    # Создаем папку, если не существует
    downloads.mkdir(exist_ok=True)
    return downloads


def show_downloads_notification(app, file_path):
    """Показывает уведомление о сохранении файла с кнопкой открытия папки"""
    downloads = Path(file_path).parent

    # Создаем кастомное окно сообщения
    popup = tk.Toplevel(app)
    popup.title("Скачивание завершено")
    popup.geometry("400x200")

    # Основной текст
    msg = tk.Label(
        popup,
        text=f"Архив успешно сохранен в папке Downloads:\n\n{file_path.name}",
        font=('Arial', 11),
        wraplength=380,
        justify='left'
    )
    msg.pack(pady=20)

    # Кнопка открытия папки
    open_btn = tk.Button(
        popup,
        text="Открыть папку Downloads",
        command=lambda: open_folder(downloads),
        bg="#4CAF50",
        fg="white",
        padx=20,
        pady=5
    )
    open_btn.pack(pady=10)

    # Кнопка закрытия
    close_btn = tk.Button(
        popup,
        text="Закрыть",
        command=popup.destroy,
        bg="#f44336",
        fg="white",
        padx=20,
        pady=5
    )
    close_btn.pack(pady=5)


def create_zip_from_folder(source_folder, zip_name=None):
    """Создает временный ZIP-архив из папки"""
    if zip_name is None:
        zip_name = Path(source_folder).name + '.zip'

    temp_dir = tempfile.gettempdir()
    zip_path = Path(temp_dir) / zip_name

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_folder):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(source_folder)
                zipf.write(file_path, arcname)

    return zip_path


def open_folder(path):
    """Открывает папку в проводнике ОС"""
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])
    except Exception as e:
        print(f"Ошибка открытия папки: {e}")


def download_dataset_with_notification(app, source_folder, zip_name=None, extra_data=None, callback=None):
    """Безопасная версия для собранного приложения с коллбеком"""
    try:
        # Получаем путь к Downloads
        downloads_folder = get_downloads_folder()

        # Создаем архив во временной папке
        zip_path = create_custom_zip(source_folder, zip_name=zip_name, extra_json_data=extra_data)

        # Определяем конечный путь в Downloads с проверкой на существование
        base_name = Path(source_folder).name if zip_name is None else zip_name
        dest_filename = f"{base_name}.zip"
        dest_path = downloads_folder / dest_filename

        # Обработка случая, когда файл уже существует
        counter = 1
        while dest_path.exists() and dest_path.is_file():
            dest_path = downloads_folder / f"{base_name} ({counter}).zip"
            counter += 1

        # Копируем в Downloads
        shutil.copy2(zip_path, dest_path)

        # Очистка временного файла
        zip_path.unlink()

        # Вызываем коллбек при успехе
        if callback:
            callback(True)

        return True

    except Exception as e:
        app.after(0, lambda: messagebox.showerror(
            "Ошибка",
            f"Не удалось скачать датасет:\n{str(e)}",
            parent=app
        ))
        if callback:
            callback(False)
        return False