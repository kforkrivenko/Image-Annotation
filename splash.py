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
        # Получаем директорию с исполняемым файлом
        if system == "Darwin":
            # macOS: Contents/Resources/ImageAnnotationMain.app
            splash_app_dir = os.path.dirname(os.path.dirname(os.path.dirname(sys.executable)))
            main_app_path = os.path.join(splash_app_dir, "Contents", "Resources", "ImageAnnotationMain.app")
            subprocess.Popen(["open", main_app_path])
        elif system == "Windows":
            # Windows: main exe в папке ImageAnnotationMain
            splash_dir = os.path.dirname(sys.executable)
            main_app_path = os.path.join(splash_dir, "ImageAnnotationMain", "ImageAnnotationMain.exe")
            # Проверяем существование файла
            if os.path.exists(main_app_path):
                subprocess.Popen([main_app_path])
            else:
                # Fallback: ищем в той же папке что и splash
                main_app_path = os.path.join(splash_dir, "ImageAnnotationMain.exe")
                if os.path.exists(main_app_path):
                    subprocess.Popen([main_app_path])
                else:
                    print(f"Не найден ImageAnnotationMain.exe в {splash_dir}")
        else:
            # Linux: основной бинарник рядом
            splash_dir = os.path.dirname(sys.executable)
            main_app_path = os.path.join(splash_dir, "ImageAnnotationMain")
            if os.path.exists(main_app_path):
                subprocess.Popen([main_app_path])
            else:
                # Fallback: ищем в папке ImageAnnotationMain
                main_app_path = os.path.join(splash_dir, "ImageAnnotationMain", "ImageAnnotationMain")
                if os.path.exists(main_app_path):
                    subprocess.Popen([main_app_path])
    else:
        # Для отладки из исходников
        if system == "Darwin":
            main_app_path = os.path.abspath("../ImageAnnotationMain.app")
            subprocess.Popen(["open", main_app_path])
        elif system == "Windows":
            main_app_path = os.path.abspath("../ImageAnnotationMain.exe")
            subprocess.Popen([main_app_path])
        else:
            main_app_path = os.path.abspath("../ImageAnnotationMain")
            subprocess.Popen([main_app_path])
    time.sleep(2)
    root.quit()

root = tk.Tk()
root.overrideredirect(True)
root.geometry("400x200+500+300")
tk.Label(root, text="Загрузка...", font=("Arial", 18)).pack(expand=True)

threading.Thread(target=launch_main, daemon=True).start()
root.mainloop()
