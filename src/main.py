# MyPhotoProcessor/src/main.py
import tkinter as tk
from tkinter import ttk, messagebox
from . import app_config  # Relative import
from .ui_config_tab import ConfigTab # Assuming you named the file ui_config_tab.py
#  Import your other tabs and main frame components here
from .ui_import_tab import ImportTab 
from .ui_process_tab import ProcessTab
from .ui_reporting_tab import ReportingTab 


import tkinter as tk
from tkinter import ttk, messagebox # Added messagebox here
from . import app_config
from .ui_config_tab import ConfigTab


class MainApplication(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("My Photo Processorrrr")
        self.geometry("800x600")

        # --- Initialize Configuration First ---
        # This ensures config.ini is created/loaded before any UI tries to access it
        app_config.initialize_config()
        print(f"MainApplication: Initial photo storage path from config: {app_config.get_photo_storage_path()}")

        # --- Main UI Structure (e.g., using a Notebook for tabs) ---
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill="both", padx=5, pady=5)

        # Config Tab
        self.config_tab = ConfigTab(self.notebook)
        self.notebook.add(self.config_tab, text="Configuration")

        # Add other tabs if you have them:
        self.import_tab = ImportTab(self.notebook, app_config) # pass app_config here
        self.notebook.add(self.import_tab, text="Import Photos")

        # self.process_tab = ProcessTab(self.notebook) # Example
        self.process_tab = ProcessTab(self.notebook, app_config) # Pass app_config here
        self.notebook.add(self.process_tab, text="Process Photos")
        
        # Reporting Tab (example, if you have it)
        # self.reporting_tab = ReportingTab(self.notebook)
        self.reporting_tab = ReportingTab(self.notebook, app_config) # Pass app_config here
        self.notebook.add(self.reporting_tab, text="Reporting")
        
        
        # You might want to select a default tab
        self.notebook.select(self.config_tab) 

        # --- Status Bar (Optional) ---
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_var.set("Welcome to My Photo Processor!")
        
        # Handle window close gracefully (optional, but good practice)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        # You might want to save any unsaved changes or confirm exit
        if messagebox.askokcancel("Quit", "Do you want to quit My Photo Processor?"):
            # Perform any cleanup here
            print("Exiting application.")
            self.destroy()

if __name__ == '__main__':
    app = MainApplication()
    app.mainloop()
