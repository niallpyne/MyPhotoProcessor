import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys

# Determine Project Root for correct path handling
# If main.py is in src/, then __file__ is .../MyPhotoProcessor/src/main.py
# os.path.abspath(__file__) gives the absolute path to main.py
# os.path.dirname(...) gives the directory of main.py (i.e., .../src/)
# One more os.path.dirname(...) gives the project root (i.e., .../MyPhotoProcessor/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add project root to sys.path to allow for absolute imports from 'src' if needed,
# though direct imports should work if all .py files are in src/
# and main.py is the entry point executed from within src/ or with src/ in PYTHONPATH.
# For robustness if running scripts from different locations or for helper scripts:
# sys.path.insert(0, PROJECT_ROOT) 
# sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from app_config import AppConfig 
from ui_config_tab import ConfigTab
from ui_import_tab import ImportTab
from ui_process_tab import ProcessTab
from ui_reporting_tab import ReportingTab
from file_utils import create_dot_nomedia

class PhotoProcessorApp(tk.Tk):
    def __init__(self, project_root):
        super().__init__()
        self.project_root = project_root
        self.title("My Photo Processor (with OpenCV)")
        self.geometry("850x650") # Adjusted size

        # Load or initialize application configuration, passing the project_root
        self.app_config = AppConfig(project_root=self.project_root)
        self.initialize_base_directories() # Uses app_config which now knows project_root

        # Styling
        style = ttk.Style(self)
        available_themes = style.theme_names()
        if 'aqua' in available_themes: # 'aqua' is a common macOS theme
            try:
                style.theme_use('aqua')
            except tk.TclError: # Fallback if aqua theme fails
                style.theme_use('clam') # 'clam' is a good cross-platform alternative
        else:
            style.theme_use('clam')


        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        # Pass app_config (which implicitly knows project_root) to tabs
        self.config_tab = ConfigTab(self.notebook, self.app_config)
        self.import_tab = ImportTab(self.notebook, self.app_config)
        self.process_tab = ProcessTab(self.notebook, self.app_config)
        self.reporting_tab = ReportingTab(self.notebook, self.app_config)

        self.notebook.add(self.config_tab, text="Config")
        self.notebook.add(self.import_tab, text="Import & Metadata")
        self.notebook.add(self.process_tab, text="Process Photos")
        self.notebook.add(self.reporting_tab, text="Reporting")

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def initialize_base_directories(self):
        """Creates base directories using paths from AppConfig."""
        imported_events_dir = self.app_config.get_path('imported_events_path')
        final_photos_dir = self.app_config.get_path('final_photos_path')

        os.makedirs(imported_events_dir, exist_ok=True)
        create_dot_nomedia(imported_events_dir)

        os.makedirs(final_photos_dir, exist_ok=True)
        create_dot_nomedia(final_photos_dir)

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.app_config.save_config() # Ensure config is saved on exit
            self.destroy()

if __name__ == "__main__":
    # PROJECT_ROOT is defined at the module level
    app = PhotoProcessorApp(project_root=PROJECT_ROOT)
    app.mainloop()
