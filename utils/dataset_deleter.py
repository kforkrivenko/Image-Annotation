import shutil
import threading
import queue
from pathlib import Path
from tkinter import messagebox
import tkinter as tk
from tkinter import ttk
from utils.json_manager import JsonManager
from utils.paths import DATA_DIR


class DatasetDeleter:
    def __init__(self, master, test_dataset=False):
        self.master = master
        self.queue = queue.Queue()
        self.is_running = False
        self.progress_window = None
        self.current_task_id = 0
        self.test_dataset = test_dataset

    def delete_datasets(self, datasets):
        if not datasets:
            return

        if self.is_running:
            messagebox.showwarning("Внимание", "Удаление уже выполняется", parent=self.master)
            return

        output_dir = DATA_DIR / "annotated_dataset"
        hash_to_name_path = output_dir / 'hash_to_name.json'

        if not self.test_dataset:
            hash_to_name_manager = JsonManager(hash_to_name_path)
            dataset_names = ' '.join(
                list(map(lambda dataset: Path(hash_to_name_manager[Path(dataset).name]).name, datasets)))
        else:
            hash_to_name_manager = JsonManager(hash_to_name_path)
            dataset_names = ' '.join(
                list(map(lambda dataset: Path(hash_to_name_manager[Path(dataset).parent.parent.name]).name, datasets)))

        if not self.test_dataset:
            txt_conf = f"Удалить датасеты: {dataset_names}?" if len(datasets) > 1 else f"Удалить датасет: {dataset_names}?"
        else:
            txt_conf = f"Удалить результат тестирование датасетов: {dataset_names}?" if len(
                datasets) > 1 else f"Удалить результаты тестирования датасетов: {dataset_names}?"
        confirm = messagebox.askyesno(
            "Подтверждение",
            txt_conf,
            parent=self.master
        )
        if not confirm:
            return

        self.current_task_id += 1
        self.is_running = True

        self.datasets_to_delete = datasets
        self._show_progress(len(datasets))

        self.master.after(100, self._start_deletion)

    def _start_deletion(self):
        threading.Thread(
            target=self._delete_in_background,
            args=(self.datasets_to_delete, self.current_task_id),
            daemon=True
        ).start()

        self._monitor_progress()

    def _delete_in_background(self, datasets, task_id):
        output_dir = DATA_DIR / "annotated_dataset"
        annotations_path = output_dir / 'annotations.json'
        hash_to_name_path = output_dir / 'hash_to_name.json'
        annotations_manager = JsonManager(annotations_path)
        hash_to_name_manager = JsonManager(hash_to_name_path)

        try:
            for i, dataset in enumerate(datasets, 1):
                if task_id != self.current_task_id:
                    break

                try:
                    if dataset.exists():
                        if not self.test_dataset:
                            shutil.rmtree(dataset, ignore_errors=True)
                        else:
                            shutil.rmtree(dataset.parent.parent, ignore_errors=True)

                    dataset_path = str(output_dir / dataset.name)

                    if not self.test_dataset:
                        annotations_manager.delete_key(dataset_path)
                        hash_to_name_manager.delete_key(dataset.name)

                    self.queue.put(("progress", i, len(datasets)))

                except Exception as e:
                    self.queue.put(("error", f"{dataset.name}: {str(e)}"))
                    continue
            if not self.test_dataset:
                annotations_manager.save()
                hash_to_name_manager.save()

            self.queue.put(("complete", task_id))
        except Exception as e:
            self.queue.put(("error", f"Critical error: {str(e)}"))

    def _show_progress(self, total):
        if self.progress_window:
            self.progress_window.destroy()

        self.progress_window = tk.Toplevel(self.master)
        self.progress_window.title("Удаление датасетов")
        self.progress_window.protocol("WM_DELETE_WINDOW", self._confirm_cancel)
        self.progress_window.resizable(False, False)

        # Центрируем окно
        self.progress_window.update_idletasks()
        width = 350
        height = 120
        x = (self.master.winfo_screenwidth() // 2) - (width // 2)
        y = (self.master.winfo_screenheight() // 2) - (height // 2)
        self.progress_window.geometry(f"{width}x{height}+{x}+{y}")

        self.progress_label = tk.Label(
            self.progress_window,
            text="Подготовка к удалению..."
        )
        self.progress_label.pack(pady=5)

        self.progress_bar = ttk.Progressbar(
            self.progress_window,
            orient="horizontal",
            length=300,
            mode="determinate",
            maximum=total
        )
        self.progress_bar.pack(pady=5)

        self.cancel_btn = tk.Button(
            self.progress_window,
            text="Отмена",
            command=self._confirm_cancel
        )
        self.cancel_btn.pack(pady=5)
        self.progress_window.update_idletasks()

    def _monitor_progress(self):
        try:
            msg_type, *data = self.queue.get_nowait()

            if msg_type == "progress":
                current, total = data
                self.progress_bar["value"] = current
                self.progress_label.config(text=f"Удаление {current} из {total}")
                self.progress_window.update_idletasks()

            elif msg_type == "error":
                error_msg = data[0]
                print(f"Ошибка удаления: {error_msg}")

            elif msg_type == "complete":
                task_id = data[0]
                if task_id == self.current_task_id:
                    self._cleanup()
                    return

        except queue.Empty:
            pass

        if self.is_running:
            self.master.after(100, self._monitor_progress)

    def _cleanup(self):
        self.is_running = False
        if self.progress_window:
            self.progress_window.destroy()
            self.progress_window = None

        # Обновляем список датасетов
        self.master.event_generate("<<RefreshDatasets>>")
        self.master.event_generate("<<RefreshTestedDatasets>>")
        messagebox.showinfo("Готово", "Удаление завершено", parent=self.master)

    def _confirm_cancel(self):
        if messagebox.askokcancel(
                "Отмена удаления",
                "Вы уверены, что хотите прервать удаление?",
                parent=self.progress_window
        ):
            self.current_task_id += 1  # Инвалидируем текущую задачу
            self.is_running = False
            if self.progress_window:
                self.progress_window.destroy()
                self.progress_window = None