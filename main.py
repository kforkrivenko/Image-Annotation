import sys

from pathlib import Path
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
import os

# Создание необходимых директорий
def prepare_env():
    (DATA_DIR / "logs").mkdir(exist_ok=True)
    (DATA_DIR / "annotated_dataset").mkdir(exist_ok=True)

# 👇 Всё GUI и тяжёлое — сюда
def run_app():
    import tkinter as tk
    from tkinter import Label
    import threading
    from ui.app import ImageAnnotationApp

    def show_splash():
        splash = tk.Tk()
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
                    f.write("[INFO] Heavy components initialized.")
                splash.after(0, lambda: (callback(), splash.destroy()))
            except Exception as e:
                print(f"[ERROR] Heavy init failed: {e}")
                with open(test_log_path, "a") as f:
                    f.write(f"[ERROR] Heavy init failed: {e}\n")
                splash.after(0, splash.destroy)

        threading.Thread(target=task, daemon=True).start()

    splash = show_splash()

    def on_loaded():
        with open(test_log_path, "a") as f:
            f.write("[INFO] on_loaded executed\n")
        app = ImageAnnotationApp()

        if '--test' in sys.argv:
            app.root.after(3000, app.root.destroy)

        app.run()

    initialize_heavy_components(callback=on_loaded)
    splash.mainloop()


if __name__ == "__main__":
    prepare_env()
    run_app()
