import tkinter as tk
import subprocess
import threading
import time
import os
import sys
import platform

def launch_main():
    system = platform.system()
    if getattr(sys, 'frozen', False):
        splash_app_dir = os.path.dirname(os.path.dirname(os.path.dirname(sys.executable)))
        if system == "Darwin":
            # macOS: Contents/Resources/ImageAnnotationMain.app
            main_app_path = os.path.join(splash_app_dir, "Contents", "Resources", "ImageAnnotationMain.app")
            subprocess.Popen(["open", main_app_path])
        elif system == "Windows":
            # Windows: main exe рядом с splash (ImageAnnotationMain.exe)
            main_app_path = os.path.join(splash_app_dir, "ImageAnnotationMain.exe")
            subprocess.Popen([main_app_path], shell=True)
        else:
            # Linux: основной бинарник рядом (image_annotation_main)
            main_app_path = os.path.join(splash_app_dir, "image_annotation_main")
            subprocess.Popen([main_app_path])
    else:
        # Для отладки из исходников
        if system == "Darwin":
            main_app_path = os.path.abspath("../ImageAnnotationMain.app")
            subprocess.Popen(["open", main_app_path])
        elif system == "Windows":
            main_app_path = os.path.abspath("../ImageAnnotationMain.exe")
            subprocess.Popen([main_app_path], shell=True)
        else:
            main_app_path = os.path.abspath("../image_annotation_main")
            subprocess.Popen([main_app_path])
    time.sleep(2)
    root.quit()

root = tk.Tk()
root.overrideredirect(True)
root.geometry("400x200+500+300")
tk.Label(root, text="Загрузка...", font=("Arial", 18)).pack(expand=True)

threading.Thread(target=launch_main, daemon=True).start()
root.mainloop()
