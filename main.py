from utils.paths import *
from ui.app import ImageAnnotationApp
from pathlib import Path
import threading


def initialize_heavy_components():
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

    threading.Thread(target=task, daemon=True).start()


def prepare_env():
    """Создает необходимые директории"""
    (DATA_DIR / "logs").mkdir(exist_ok=True)
    (DATA_DIR / "annotated_dataset").mkdir(exist_ok=True)



if __name__ == "__main__":
    prepare_env()
    app = ImageAnnotationApp()
    app.root.after(100, initialize_heavy_components)
    app.run()
