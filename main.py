import sys
from pathlib import Path
import os

# --- Кроссплатформенный lock-файл для защиты от двойного запуска (особенно в PyInstaller .app) ---
import tempfile

# Пытаемся импортировать psutil, если не доступен - используем простую проверку
try:
    import psutil
    def pid_exists(pid):
        return psutil.pid_exists(pid)
except ImportError:
    def pid_exists(pid):
        try:
            os.kill(pid, 0)  # Проверяем, существует ли процесс
            return True
        except OSError:
            return False

lockfile = os.path.join(tempfile.gettempdir(), 'nn_custom_train_tool.lock')

# Проверяем, существует ли lock-файл и работает ли процесс
if os.path.exists(lockfile):
    try:
        with open(lockfile, 'r') as f:
            pid_str = f.read().strip()
            if pid_str.isdigit():
                pid = int(pid_str)
                # Проверяем, существует ли процесс с этим PID
                if pid_exists(pid):
                    print("[LOCK] Already running, exiting.")
                    sys.exit(0)
                else:
                    # Процесс не существует, удаляем старый lock-файл
                    print("[LOCK] Stale lock file found, removing...")
                    os.remove(lockfile)
    except (ValueError, IOError):
        # Если не удается прочитать PID, удаляем файл
        print("[LOCK] Corrupted lock file found, removing...")
        try:
            os.remove(lockfile)
        except:
            pass

# Создаем новый lock-файл
with open(lockfile, 'w') as f:
    f.write(str(os.getpid()))

import atexit
def _remove_lock():
    try:
        if os.path.exists(lockfile):
            os.remove(lockfile)
    except Exception:
        pass
atexit.register(_remove_lock)

# --- остальной код ---
# Проверяем, не запущено ли уже приложение
if hasattr(sys, '_app_initialized'):
    print("Приложение уже инициализировано")
    sys.exit(0)

# Отмечаем, что приложение инициализировано
sys._app_initialized = True

test_log_path = Path(sys.executable).parent / "test_log.txt"

# 💡 Обработка --test до ВСЕГО
if '--test' in sys.argv:
    print("Test mode active")
    with open(test_log_path, "a") as f:
        f.write("[INFO] Running test mode\n")
    if '--full' not in sys.argv:
        sys.exit(0)

# Только лёгкие импорты
from utils.paths import *
import threading
from tkinter import Label
import tkinter as tk
from ui.app import ImageAnnotationApp

def prepare_env():
    (DATA_DIR / "logs").mkdir(exist_ok=True)
    (DATA_DIR / "annotated_dataset").mkdir(exist_ok=True)

def run_app():
    # Создаем root — он не отображается, но нужен как родитель для splash и app
    root = tk.Tk()
    root.withdraw()

    def show_splash(master):
        splash = tk.Toplevel(master)
        splash.overrideredirect(True)
        splash.geometry("400x200+500+300")
        label = Label(splash, text="Загрузка приложения...", font=("Arial", 16))
        label.pack(expand=True)
        return splash

    def initialize_heavy_components(callback):
        def task():
            try:
                import matplotlib
                matplotlib.use("Agg")
                import matplotlib.pyplot as plt
                import torch
                import cv2
                from ultralytics import YOLO
                from sklearn.model_selection import train_test_split
                from PIL import Image, ImageTk, ImageDraw, ImageFont
                print("[INFO] Heavy components initialized.")
                with open(test_log_path, "a") as f:
                    f.write("[INFO] Heavy components initialized.\n")

                root.after_idle(callback)
            except Exception as e:
                print(f"[ERROR] Heavy init failed: {e}")
                with open(test_log_path, "a") as f:
                    f.write(f"[ERROR] Heavy init failed: {e}\n")
                root.quit()

        threading.Thread(target=task, daemon=True).start()

    splash = show_splash(root)

    def on_loaded():
        print("[INFO] on_loaded executed")
        with open(test_log_path, "a") as f:
            f.write("[INFO] on_loaded executed\n")

        splash.destroy()

        app = ImageAnnotationApp(master=root)
        if '--test' in sys.argv:
            def close_app():
                app.root.destroy()
                root.quit()
            app.root.after(3000, close_app)

    initialize_heavy_components(callback=on_loaded)
    root.mainloop()

if __name__ == "__main__":
    prepare_env()
    run_app()
