from utils.paths import *
from ui.app import ImageAnnotationApp
from pathlib import Path
import threading
import tkinter as tk
from tkinter import Label

# Создание необходимых директорий
def prepare_env():
    (DATA_DIR / "logs").mkdir(exist_ok=True)
    (DATA_DIR / "annotated_dataset").mkdir(exist_ok=True)

# Показываем сплэш-экран
def show_splash():
    splash = tk.Tk()
    splash.overrideredirect(True)
    splash.geometry("400x200+500+300")
    label = Label(splash, text="Загрузка приложения...", font=("Arial", 16))
    label.pack(expand=True)
    return splash

# Инициализация тяжелых компонентов
def initialize_heavy_components(callback):
    def task():
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import torch
        import cv2
        from ultralytics import YOLO
        from sklearn.model_selection import train_test_split
        from PIL import Image, ImageTk, ImageDraw, ImageFont
        print("Heavy components initialized.")

        # По завершении — вызов callback в главном потоке
        splash.after(0, callback)

    threading.Thread(target=task, daemon=True).start()


if __name__ == "__main__":
    prepare_env()
    splash = show_splash()

    def on_loaded():
        splash.destroy()
        app = ImageAnnotationApp()
        app.run()

    initialize_heavy_components(callback=on_loaded)
    splash.mainloop()
