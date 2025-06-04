import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os

class ConfigTab(ttk.Frame):
    def __init__(self, parent_notebook, app_config):
        super().__init__(parent_notebook)
        self.app_config = app_config # app_config now knows project_root
        
        path_frame = ttk.LabelFrame(self, text="Directory Settings")
        path_frame.pack(padx=10, pady=10, fill="x")

        ttk.Label(path_frame, text="Phone Staging Directory:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.staging_path_var = tk.StringVar(value=self.app_config.get_setting('phone_staging_path', ''))
        self.entry_staging = ttk.Entry(path_frame, textvariable=self.staging_path_var, width=50)
        self.entry_staging.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(path_frame, text="Browse...", command=self.browse_staging_directory).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(path_frame, text="Imported Events Directory (Rel. to Project):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.imported_path_var = tk.StringVar(value=self.app_config.get_setting('imported_events_path', 'ImportedEvents'))
        self.entry_imported = ttk.Entry(path_frame, textvariable=self.imported_path_var, width=50) 
        self.entry_imported.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(path_frame, text="Final Photos Directory (Rel. to Project):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.final_path_var = tk.StringVar(value=self.app_config.get_setting('final_photos_path', 'FinalPhotos'))
        self.entry_final = ttk.Entry(path_frame, textvariable=self.final_path_var, width=50) 
        self.entry_final.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        path_frame.grid_columnconfigure(1, weight=1)
        
        opencv_defaults_frame = ttk.LabelFrame(self, text="Default OpenCV Parameters (Editable in AppConfig/AppConfig.json)")
        opencv_defaults_frame.pack(padx=10, pady=10, fill="x", expand=True)
        row_idx = 0
        params_to_show = [
            ('clahe_clip_limit', "CLAHE Clip Limit:"), ('clahe_tile_grid_size', "CLAHE Tile Size:"),
            ('bilateral_d', "Bilateral Filter D:"), ('bilateral_sigma_color', "Bilateral Sigma Color:"),
            ('bilateral_sigma_space', "Bilateral Sigma Space:"),
            ('unsharp_sigma', "Unsharp Mask Sigma:"), ('unsharp_strength', "Unsharp Mask Strength:"),
            ('default_crop_top', "Default Crop Top %:"), ('default_crop_right', "Default Crop Right %:"),
            ('default_crop_bottom', "Default Crop Bottom %:"), ('default_crop_left', "Default Crop Left %:"),
            ('pale_blue_hsv_lower', "Pale Blue HSV Lower:"), ('pale_blue_hsv_upper', "Pale Blue HSV Upper:"),
            ('auto_crop_inward_offset', "Auto-Crop Inward Offset (px):")
        ]
        for key, text in params_to_show:
            ttk.Label(opencv_defaults_frame, text=text).grid(row=row_idx, column=0, padx=5, pady=2, sticky="w")
            val = self.app_config.get_setting(key, 'N/A')
            ttk.Label(opencv_defaults_frame, text=str(val)).grid(row=row_idx, column=1, padx=5, pady=2, sticky="w")
            row_idx += 1

        ttk.Button(self, text="Save Configuration", command=self.save_config_settings).pack(pady=20)

    def browse_staging_directory(self):
        current_staging_path_raw = self.app_config.get_setting('phone_staging_path')
        initial_dir_for_dialog = os.path.expanduser("~")
        if current_staging_path_raw:
            if os.path.isabs(current_staging_path_raw):
                if os.path.isdir(current_staging_path_raw): initial_dir_for_dialog = current_staging_path_raw
                elif os.path.isdir(os.path.dirname(current_staging_path_raw)): initial_dir_for_dialog = os.path.dirname(current_staging_path_raw)
            else:
                resolved_path = os.path.join(self.app_config.project_root, current_staging_path_raw)
                if os.path.isdir(resolved_path): initial_dir_for_dialog = resolved_path
                elif os.path.isdir(os.path.dirname(resolved_path)): initial_dir_for_dialog = os.path.dirname(resolved_path)
        directory = filedialog.askdirectory(initialdir=initial_dir_for_dialog, title="Select Phone Staging Directory")
        if directory: self.staging_path_var.set(directory)

    def save_config_settings(self):
        self.app_config.update_setting('phone_staging_path', self.staging_path_var.get())
        self.app_config.update_setting('imported_events_path', self.imported_path_var.get()) 
        self.app_config.update_setting('final_photos_path', self.final_path_var.get())     
        # To make HSV and other OpenCV params editable via UI, you'd add StringVars/IntVars
        # and then update them here, e.g.:
        # try:
        #     hsv_l = [int(x.strip()) for x in self.hsv_lower_config_var.get().split(',')]
        #     if len(hsv_l) == 3: self.app_config.update_setting('pale_blue_hsv_lower', hsv_l)
        # except ValueError:
        #     messagebox.showerror("Error", "Invalid format for HSV Lower. Use 3 comma-separated integers.")
        # ... and similarly for other editable config params ...
        self.app_config.save_config()
        messagebox.showinfo("Config", "Configuration saved!")
