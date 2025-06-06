# MyPhotoProcessor/src/ui_config_tab.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from . import app_config # Use relative import as it's in the same 'src' package

class ConfigTab(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.padding = {"padx": 10, "pady": 5}

        # --- Photo Storage Path ---
        path_group = ttk.LabelFrame(self, text="Folder Locations", padding=(10, 5))
        path_group.grid(row=0, column=0, sticky="ew", padx=self.padding["padx"], pady=self.padding["pady"])
        path_group.columnconfigure(1, weight=1) # Make entry expand

        ttk.Label(path_group, text="Photo Storage Path:").grid(
            row=0, column=0, sticky="w", padx=self.padding["padx"], pady=self.padding["pady"])

        self.photo_storage_path_var = tk.StringVar()
        self.path_entry = ttk.Entry(path_group, textvariable=self.photo_storage_path_var, width=60)
        self.path_entry.grid(row=0, column=1, sticky="ew", padx=self.padding["padx"], pady=self.padding["pady"])

        self.browse_button = ttk.Button(path_group, text="Browse...", command=self.browse_photo_storage_path)
        self.browse_button.grid(row=0, column=2, sticky="e", padx=(0, self.padding["padx"]), pady=self.padding["pady"])
        
        # --- Save Button ---
        # It's often better to have a single "Save" or "Apply" button for the whole config tab or window
        # rather than saving on every change, to give the user control.
        # This button could be part of this tab or a global button in your main frame.
        # For this example, let's put a save button specific to this setting group.
        self.save_paths_button = ttk.Button(path_group, text="Save Path Change", command=self.save_settings)
        self.save_paths_button.grid(row=1, column=0, columnspan=3, pady=self.padding["pady"]*2)


        # --- Load initial settings ---
        self.load_settings()

    def load_settings(self):
        """Loads settings from app_config into the UI elements."""
        current_path = app_config.get_photo_storage_path()
        self.photo_storage_path_var.set(current_path)
        print(f"ConfigTab: Loaded photo storage path: {current_path}")


    def browse_photo_storage_path(self):
        """Opens a dialog to choose a directory."""
        current_path = self.photo_storage_path_var.get()
        if not current_path: # If entry is empty, start from user's home directory
            current_path = os.path.expanduser("~")
            
        directory = filedialog.askdirectory(
            initialdir=current_path,
            title="Select Photo Storage Directory"
        )
        if directory:  # If a directory was selected (not cancelled)
            self.photo_storage_path_var.set(directory)
            # Optionally, you could enable the save button here if it was disabled
            # Or print a message indicating the path has changed but not yet saved.
            print(f"ConfigTab: Path selected via browse: {directory} (not saved yet)")


    def save_settings(self):
        """Saves the current UI settings back using app_config."""
        new_path = self.photo_storage_path_var.get()
        if not new_path:
            messagebox.showerror("Error", "Photo storage path cannot be empty.")
            return

        if not os.path.isdir(new_path):
            if messagebox.askyesno("Path Not Found", 
                                   f"The path '{new_path}' does not currently exist or is not a directory.\n"
                                   "Do you want to save it anyway?"):
                pass # User chose to save anyway
            else:
                return # User chose not to save

        try:
            app_config.save_photo_storage_path(new_path)
            messagebox.showinfo("Settings Saved", f"Photo storage path updated to:\n{new_path}")
            print(f"ConfigTab: Settings saved. New path: {new_path}")
        except Exception as e:
            messagebox.showerror("Error Saving Settings", f"Could not save settings: {e}")
            print(f"ConfigTab: Error saving settings: {e}")

