import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Dict


class DatasetHistoryPanel(tk.Frame):
    def __init__(self, parent, on_dataset_select: Callable[[str], None]):
        super().__init__(parent)
        self.on_dataset_select = on_dataset_select
        self._setup_ui()

    def _setup_ui(self):
        self.tree = ttk.Treeview(self, columns=("Path", "Images"), show="headings")
        self.tree.heading("Path", text="Dataset Name")
        self.tree.heading("Images", text="Images Count")
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def update_datasets(self, datasets: List[Dict]):
        """Обновляет список датасетов в Treeview."""
        self.tree.delete(*self.tree.get_children())
        for dataset in datasets:
            self.tree.insert(
                "", "end",
                values=(dataset["name"], dataset["images_count"])
            )

    def _on_select(self, event):
        selected = self.tree.selection()
        if selected:
            dataset_name = self.tree.item(selected[0])["values"][0]
            self.on_dataset_select(dataset_name)
