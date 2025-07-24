import tkinter as tk
import subprocess
import threading
import time
import os
import sys

def launch_main():
    # Определяем путь к основному приложению внутри Contents/Resources
    if getattr(sys, 'frozen', False):
        splash_app_dir = os.path.dirname(os.path.dirname(os.path.dirname(sys.executable)))
        main_app_path = os.path.join(splash_app_dir, "Contents", "Resources", "ImageAnnotationMain.app")
    else:
        main_app_path = os.path.abspath("../ImageAnnotationMain.app")

    subprocess.Popen(["open", main_app_path])
    time.sleep(2)
    root.quit()

root = tk.Tk()
root.overrideredirect(True)
root.geometry("400x200+500+300")
tk.Label(root, text="Загрузка...", font=("Arial", 18)).pack(expand=True)

threading.Thread(target=launch_main, daemon=True).start()
root.mainloop()
