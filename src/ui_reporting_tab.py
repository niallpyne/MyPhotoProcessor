# ui_reporting_tab.py
import tkinter as tk
from tkinter import ttk, messagebox
import os
from PIL import Image, ImageTk

class ReportingTab(ttk.Frame):
    def __init__(self, parent_notebook, app_config):
        super().__init__(parent_notebook)
        self.app_config = app_config
        # Use get_path for resolved absolute paths
        # self.imported_events_root_abs = self.app_config.get_path('imported_events_path')
        
        default_events_path = self.app_config.DEFAULT_IMPORTED_EVENTS_PATH 
        self.imported_events_root_abs = self.app_config.get_setting(
            self.app_config.CONFIG_SECTION_PATHS,         # This is 'Paths'
            self.app_config.CONFIG_KEY_IMPORTED_EVENTS,   # This is 'ImportedEventsDirectory'
            fallback=default_events_path)        
        
        #self.final_photos_root_abs = self.app_config.get_path('final_photos_path')
        default_final_path = self.app_config.DEFAULT_FINAL_PHOTOS_PATH 
        self.final_photos_root_abs = self.app_config.get_setting(
            self.app_config.CONFIG_SECTION_PATHS,       # This is 'Paths'
            self.app_config.CONFIG_KEY_FINAL_PHOTOS,    # This is 'FinalPhotosDirectory'
            fallback=default_final_path)

        # --- UI Elements ---
        # Event Selection
        event_selection_frame = ttk.Frame(self)
        event_selection_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(event_selection_frame, text="Select Event:").pack(side=tk.LEFT, padx=5)
        self.event_var = tk.StringVar()
        self.event_dropdown = ttk.Combobox(event_selection_frame, textvariable=self.event_var, state="readonly", width=30)
        self.event_dropdown.pack(side=tk.LEFT, padx=5)
        self.event_dropdown.bind("<<ComboboxSelected>>", self.on_event_selected)
        ttk.Button(event_selection_frame, text="Refresh Event List", command=self.populate_event_dropdown).pack(side=tk.LEFT, padx=5)

        # Photo Selection (within the chosen event)
        photo_selection_frame = ttk.Frame(self)
        photo_selection_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(photo_selection_frame, text="Select Photo:").pack(side=tk.LEFT, padx=5)
        self.photo_var = tk.StringVar()
        self.photo_dropdown = ttk.Combobox(photo_selection_frame, textvariable=self.photo_var, state="readonly", width=40)
        self.photo_dropdown.pack(side=tk.LEFT, padx=5)
        self.photo_dropdown.bind("<<ComboboxSelected>>", self.on_photo_selected)

        # Image Display Panes
        comparison_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        comparison_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.original_panel = ttk.LabelFrame(comparison_pane, text="Original")
        self.original_image_label = ttk.Label(self.original_panel, text="Original Image", relief="groove", anchor="center")
        self.original_image_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        comparison_pane.add(self.original_panel, weight=1)

        self.processed_panel = ttk.LabelFrame(comparison_pane, text="Processed / Final")
        self.processed_image_label = ttk.Label(self.processed_panel, text="Processed / Final Image", relief="groove", anchor="center")
        self.processed_image_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        comparison_pane.add(self.processed_panel, weight=1)
        
        self.original_image_tk = None # To keep a reference to the PhotoImage object
        self.processed_image_tk = None # To keep a reference

        self.populate_event_dropdown() # Initial population


    def populate_event_dropdown(self):
        # self.imported_events_root_abs = self.app_config.get_path('imported_events_path') # Refresh path
        default_events_path = self.app_config.DEFAULT_IMPORTED_EVENTS_PATH 
        self.imported_events_root_abs = self.app_config.get_setting(
            self.app_config.CONFIG_SECTION_PATHS,         # This is 'Paths'
            self.app_config.CONFIG_KEY_IMPORTED_EVENTS,   # This is 'ImportedEventsDirectory'
            fallback=default_events_path)
        
        if not self.imported_events_root_abs or not os.path.isdir(self.imported_events_root_abs):
            self.event_dropdown['values'] = []
            self.event_var.set("")
            self.clear_image_displays() # Clear displays if root is invalid
            return
        try:
            events = [d for d in os.listdir(self.imported_events_root_abs)
                      if os.path.isdir(os.path.join(self.imported_events_root_abs, d))]
            self.event_dropdown['values'] = sorted(events)
            if events: 
                # Try to keep current selection if it's still valid, else default to first
                current_event = self.event_var.get()
                if current_event not in events:
                    self.event_var.set(events[0])
                # else, current selection is still valid, on_event_selected will handle it if it was already set
            else: 
                self.event_var.set("")
            self.on_event_selected(None) # Trigger photo list update for the (newly) selected event
        except Exception as e:
            messagebox.showerror("Error", f"Could not list events: {e}", parent=self)
            self.clear_image_displays()


    def on_event_selected(self, event_unused):
        event_name = self.event_var.get()
        self.photo_dropdown['values'] = [] # Clear previous photo list
        self.photo_var.set("") # Clear photo selection
        self.clear_image_displays() # Clear image previews

        if not event_name: return
        
        current_event_path_abs = os.path.join(self.imported_events_root_abs, event_name)
        photo_extensions = ('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.heic', '.webp')
        try:
            photos = sorted([
                f for f in os.listdir(current_event_path_abs) 
                if os.path.isfile(os.path.join(current_event_path_abs, f)) and f.lower().endswith(photo_extensions)
            ])
            self.photo_dropdown['values'] = photos
            if photos:
                self.photo_var.set(photos[0]) # Select first photo by default
                self.on_photo_selected(None) # Load the first photo
        except Exception as e:
            messagebox.showerror("Error", f"Could not list photos for event '{event_name}': {e}", parent=self)


    def on_photo_selected(self, event_unused):
        self.clear_image_displays() # Clear previous images first
        event_name = self.event_var.get()
        photo_name = self.photo_var.get()

        if not event_name or not photo_name:
            return

        original_photo_path = os.path.join(self.imported_events_root_abs, event_name, photo_name)
        processed_photo_path_interim = os.path.join(self.imported_events_root_abs, event_name, "Processed", photo_name)
        final_photo_path = os.path.join(self.app_config.get_path('final_photos_path'), event_name, photo_name)


        self._display_image_on_label(original_photo_path, self.original_image_label, "original_image_tk")

        if os.path.exists(final_photo_path):
            self._display_image_on_label(final_photo_path, self.processed_image_label, "processed_image_tk")
        elif os.path.exists(processed_photo_path_interim):
            self._display_image_on_label(processed_photo_path_interim, self.processed_image_label, "processed_image_tk")
        else:
            self.processed_image_label.config(image='', text="Not processed or finalized.")
            self.processed_image_tk = None


    def _display_image_on_label(self, image_path, label_widget, tk_image_attr_name):
        if not os.path.exists(image_path):
            label_widget.config(image='', text=f"Image not found:\n{os.path.basename(image_path)}")
            setattr(self, tk_image_attr_name, None)
            return
        try:
            label_widget.update_idletasks() 
            max_width = label_widget.winfo_width() - 10 
            max_height = label_widget.winfo_height() - 10

            if max_width <=1 or max_height <=1: 
                max_width, max_height = 300, 300 

            img = Image.open(image_path)
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            tk_image = ImageTk.PhotoImage(img)
            setattr(self, tk_image_attr_name, tk_image) 
            label_widget.config(image=tk_image, text="")
        except Exception as e:
            label_widget.config(image='', text=f"Error loading image:\n{os.path.basename(image_path)}\n{e}")
            setattr(self, tk_image_attr_name, None)

    def clear_image_displays(self):
        self.original_image_label.config(image='', text="Original Image")
        self.original_image_tk = None
        self.processed_image_label.config(image='', text="Processed / Final Image")
        self.processed_image_tk = None
