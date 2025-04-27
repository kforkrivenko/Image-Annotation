from tkinter import messagebox


class FolderLoadError(Exception):
    def __init__(self, message="Произошла ошибка загрузки"):
        self.message = message
        super().__init__(self.message)

    def show_tkinter_error(self, parent=None):
        """Отображение ошибки в Tkinter"""
        messagebox.showerror("Ошибка загрузки", self.message)


class NoImagesError(FolderLoadError):
    def __init__(self):
        self.message = "В папке нет картинок!"
        super().__init__(self.message)