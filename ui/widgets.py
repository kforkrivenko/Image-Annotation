import tkinter as tk


class ControlPanel(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._create_widgets()
        self._setup_layout()

    def _create_widgets(self):
        self.load_btn = tk.Button(self, text="Load Folder")
        self.prev_btn = tk.Button(self, text="Previous", state=tk.DISABLED)
        self.next_btn = tk.Button(self, text="Next", state=tk.DISABLED)
        self.close_btn = tk.Button(self, text="Close", state=tk.DISABLED)
        self.status_var = tk.StringVar()
        self.status_label = tk.Label(self, textvariable=self.status_var)

    def _setup_layout(self):
        self.load_btn.pack(side=tk.LEFT, padx=5)
        self.prev_btn.pack(side=tk.LEFT, padx=5)
        self.next_btn.pack(side=tk.LEFT, padx=5)
        self.close_btn.pack(side=tk.LEFT, padx=5)
        self.status_label.pack(side=tk.LEFT, padx=10)

    def update_state(self, current_index, total_images, has_image):
        self.status_var.set(f"{current_index + 1}/{total_images}")

        self.prev_btn.config(state=tk.NORMAL if current_index > 0 else tk.DISABLED)
        self.next_btn.config(
            state=tk.NORMAL if (current_index < total_images - 1) and current_index != -1 else tk.DISABLED
        )
        self.close_btn.config(state=tk.NORMAL if has_image else tk.DISABLED)
