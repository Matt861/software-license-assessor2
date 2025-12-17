from configuration import Configuration as Config
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path


class DirectoryPickerApp:
    def __init__(self, title: str = "Select Directories"):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.resizable(False, False)

        frame = tk.Frame(self.root, padx=12, pady=12)
        frame.pack(fill="both", expand=True)

        # --- Row 0: Source dir ---
        tk.Label(frame, text="Source:").grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.source_var = tk.StringVar(value=getattr(Config, "source_dir", ""))
        tk.Entry(frame, textvariable=self.source_var, width=55, state="readonly") \
            .grid(row=0, column=1, sticky="we")

        tk.Button(frame, text="Browse...", command=self.browse_source) \
            .grid(row=0, column=2, padx=(8, 0))

        # --- Row 1: Destination dir + Overwrite Destination ---
        tk.Label(frame, text="Destination:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(8, 0))

        self.dest_var = tk.StringVar(value=getattr(Config, "dest_dir", ""))
        tk.Entry(frame, textvariable=self.dest_var, width=55, state="readonly") \
            .grid(row=1, column=1, sticky="we", pady=(8, 0))

        tk.Button(frame, text="Browse...", command=self.browse_dest) \
            .grid(row=1, column=2, padx=(8, 0), pady=(8, 0))

        self.overwrite_dest_var = tk.BooleanVar(value=bool(getattr(Config, "overwrite_dest", False)))
        tk.Checkbutton(frame, text="Overwrite Destination", variable=self.overwrite_dest_var) \
            .grid(row=1, column=3, padx=(10, 0), sticky="w", pady=(8, 0))

        # --- Row 2: Diff Data (JSON file) ---
        tk.Label(frame, text="Diff Data:").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(8, 0))

        self.diff_var = tk.StringVar(value=getattr(Config, "diff_file_data", ""))
        tk.Entry(frame, textvariable=self.diff_var, width=55, state="readonly") \
            .grid(row=2, column=1, sticky="we", pady=(8, 0))

        tk.Button(frame, text="Browse...", command=self.browse_diff) \
            .grid(row=2, column=2, padx=(8, 0), pady=(8, 0))

        # --- Row 3: Project Name ---
        tk.Label(frame, text="Project Name:").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=(10, 0))

        self.project_name_var = tk.StringVar(value=getattr(Config, "source_project_name", ""))
        tk.Entry(frame, textvariable=self.project_name_var, width=55) \
            .grid(row=3, column=1, sticky="we", pady=(10, 0), columnspan=3)

        # --- Row 4: Assessment Name ---
        tk.Label(frame, text="Assessment Name:").grid(row=4, column=0, sticky="w", padx=(0, 8), pady=(8, 0))

        self.assessment_name_var = tk.StringVar(value=getattr(Config, "assessment_name", ""))
        tk.Entry(frame, textvariable=self.assessment_name_var, width=55) \
            .grid(row=4, column=1, sticky="we", pady=(8, 0), columnspan=3)

        # --- Row 5: Submit / Cancel ---
        tk.Button(frame, text="Submit", width=12, command=self.submit) \
            .grid(row=5, column=2, sticky="e", pady=(12, 0), padx=(0, 8))

        tk.Button(frame, text="Cancel", width=12, command=self.cancel) \
            .grid(row=5, column=3, sticky="e", pady=(12, 0))

        # Let the path entry expand
        frame.grid_columnconfigure(1, weight=1)

        self.root.bind("<Return>", lambda _e: self.submit())
        self.root.bind("<Escape>", lambda _e: self.cancel())

    def _pick_dir(self, current_value: str, title: str) -> str:
        current = (current_value or "").strip()
        if current and Path(current).exists():
            initial_dir = current
        else:
            initial_dir = str(Path.home())

        chosen = filedialog.askdirectory(title=title, initialdir=initial_dir)
        return chosen or ""

    def _pick_file(self, current_value: str, title: str, filetypes) -> str:
        current = (current_value or "").strip()
        initial_dir = str(Path(current).parent) if current else str(Path.home())
        if not Path(initial_dir).exists():
            initial_dir = str(Path.home())

        chosen = filedialog.askopenfilename(
            title=title,
            initialdir=initial_dir,
            filetypes=filetypes
        )
        return chosen or ""

    def browse_source(self):
        chosen = self._pick_dir(self.source_var.get(), "Choose source folder")
        if chosen:
            self.source_var.set(chosen)

    def browse_dest(self):
        chosen = self._pick_dir(self.dest_var.get(), "Choose destination folder")
        if chosen:
            self.dest_var.set(chosen)

    def browse_diff(self):
        chosen = self._pick_file(
            current_value=self.diff_var.get(),
            title="Choose diff data JSON file",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if chosen:
            self.diff_var.set(chosen)

    def submit(self):
        src = self.source_var.get().strip()
        dst = self.dest_var.get().strip()
        diff_file = self.diff_var.get().strip()
        project_name = self.project_name_var.get().strip()
        assessment_name = self.assessment_name_var.get().strip()

        if not src:
            messagebox.showwarning("Missing selection", "Please choose a source directory.")
            return
        if not dst:
            messagebox.showwarning("Missing selection", "Please choose a destination directory.")
            return
        if diff_file and not diff_file.lower().endswith(".json"):
            messagebox.showwarning("Invalid file", "Diff Data must be a .json file.")
            return
        if not project_name:
            messagebox.showwarning("Missing value", "Please enter a Project Name.")
            return
        if not assessment_name:
            messagebox.showwarning("Missing value", "Please enter an Assessment Name.")
            return

        # Set properties on your config object
        Config.source_dir = src
        Config.dest_dir = dst
        Config.diff_file_data = diff_file  # may be "" if not chosen
        Config.source_project_name = project_name
        Config.assessment_name = assessment_name

        # Set overwrite flags
        Config.overwrite_dest = bool(self.overwrite_dest_var.get())

        self.root.quit()
        self.root.destroy()

    def cancel(self):
        self.root.quit()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    DirectoryPickerApp().run()

    print("Config.SOURCE_DIR        =", getattr(Config, "source_dir", ""))
    print("Config.DEST_DIR          =", getattr(Config, "dest_dir", ""))
    print("Config.DIFF_FILE_DATA    =", getattr(Config, "diff_file_data", ""))
    print("Config.PROJECT_NAME      =", getattr(Config, "source_project_name", ""))
    print("Config.ASSESSMENT_NAME   =", getattr(Config, "assessment_name", ""))
    print("Config.OVERWRITE_DEST    =", getattr(Config, "overwrite_dest", None))
