# ui_import_tab.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
import json
from datetime import datetime
import webbrowser # For opening Google Maps
import urllib.parse # Added for URL quoting

from metadata_manager import MetadataManager 
from file_utils import create_dot_nomedia, ensure_directory_exists

class ImportTab(ttk.Frame):
    def __init__(self, parent_notebook, app_config):
        super().__init__(parent_notebook)
        self.app_config = app_config
        self.metadata_manager = MetadataManager()
        self.current_selected_staging_event_path = None
        self.current_imported_event_path = None
        self.current_event_name = tk.StringVar()

        # --- UI Elements ---
        # Section 1: Select Event from Staging
        select_event_frame = ttk.LabelFrame(self, text="1. Select Event from Phone Staging Area")
        select_event_frame.pack(padx=10, pady=10, fill="x")

        self.select_event_button = ttk.Button(select_event_frame, text="Browse for Event Folder...", command=self.select_event_from_staging)
        self.select_event_button.pack(pady=5, padx=5, fill=tk.X)
        self.selected_staging_event_label = ttk.Label(select_event_frame, text="No event selected.")
        self.selected_staging_event_label.pack(pady=5)

        # Section 2: Import Event to Workspace
        import_to_workspace_frame = ttk.LabelFrame(self, text="2. Import to Workspace")
        import_to_workspace_frame.pack(padx=10, pady=10, fill="x")

        self.import_button = ttk.Button(import_to_workspace_frame, text="Import Selected Event", command=self.import_event_to_workspace, state=tk.DISABLED)
        self.import_button.pack(pady=5, padx=5, fill=tk.X)
        self.import_status_label = ttk.Label(import_to_workspace_frame, text="")
        self.import_status_label.pack(pady=5)

        # Section 3: Event Metadata (Restructured)
        metadata_main_frame = ttk.LabelFrame(self, text="3. Event Metadata (for currently imported event)")
        metadata_main_frame.pack(padx=10, pady=10, fill="x", expand=True)

        # Event Name (stays at the top of metadata section)
        event_name_frame = ttk.Frame(metadata_main_frame)
        event_name_frame.pack(fill=tk.X, padx=5, pady=(5,10))
        ttk.Label(event_name_frame, text="Event Name:").pack(side=tk.LEFT)
        self.event_name_label = ttk.Label(event_name_frame, textvariable=self.current_event_name)
        self.event_name_label.pack(side=tk.LEFT, padx=5)


        # --- Assign Location ---
        location_frame = ttk.LabelFrame(metadata_main_frame, text="Assign Location")
        location_frame.pack(fill=tk.X, padx=5, pady=5)
        
        loc_g_row = 0
        ttk.Label(location_frame, text="City:").grid(row=loc_g_row, column=0, sticky="w", padx=5, pady=2)
        self.event_city_var = tk.StringVar()
        self.event_city_entry = ttk.Entry(location_frame, textvariable=self.event_city_var, width=30)
        self.event_city_entry.grid(row=loc_g_row, column=1, sticky="ew", padx=5, pady=2)
        loc_g_row += 1

        ttk.Label(location_frame, text="Country:").grid(row=loc_g_row, column=0, sticky="w", padx=5, pady=2)
        self.event_country_var = tk.StringVar()
        self.event_country_entry = ttk.Entry(location_frame, textvariable=self.event_country_var, width=30)
        self.event_country_entry.grid(row=loc_g_row, column=1, sticky="ew", padx=5, pady=2)
        loc_g_row += 1
        
        self.open_map_button = ttk.Button(location_frame, text="Open Map (based on City/Country)", command=self.open_google_maps)
        self.open_map_button.grid(row=loc_g_row, column=0, columnspan=2, pady=5, sticky="ew")
        loc_g_row += 1

        ttk.Label(location_frame, text="Latitude (e.g., 52.1300):").grid(row=loc_g_row, column=0, sticky="w", padx=5, pady=2)
        self.event_latitude_var = tk.StringVar()
        self.event_latitude_entry = ttk.Entry(location_frame, textvariable=self.event_latitude_var, width=30)
        self.event_latitude_entry.grid(row=loc_g_row, column=1, sticky="ew", padx=5, pady=2)
        loc_g_row += 1

        ttk.Label(location_frame, text="Longitude (e.g., -8.3000):").grid(row=loc_g_row, column=0, sticky="w", padx=5, pady=2)
        self.event_longitude_var = tk.StringVar()
        self.event_longitude_entry = ttk.Entry(location_frame, textvariable=self.event_longitude_var, width=30)
        self.event_longitude_entry.grid(row=loc_g_row, column=1, sticky="ew", padx=5, pady=2)
        location_frame.grid_columnconfigure(1, weight=1)


        # --- Correct Photo Dates ---
        date_frame = ttk.LabelFrame(metadata_main_frame, text="Event Date (to be applied to all photos in this event)  (YYYY-MM-DD)")
        date_frame.pack(fill=tk.X, padx=5, pady=5)
        
        date_input_frame = ttk.Frame(date_frame)
        date_input_frame.pack(pady=2)

        ttk.Label(date_input_frame, text="Year:").pack(side=tk.LEFT, padx=(0,2))
        self.event_year_var = tk.StringVar()
        self.event_year_entry = ttk.Entry(date_input_frame, textvariable=self.event_year_var, width=6)
        self.event_year_entry.pack(side=tk.LEFT, padx=(0,5))

        ttk.Label(date_input_frame, text="Month:").pack(side=tk.LEFT, padx=(0,2))
        self.event_month_var = tk.StringVar()
        self.event_month_entry = ttk.Entry(date_input_frame, textvariable=self.event_month_var, width=4)
        self.event_month_entry.pack(side=tk.LEFT, padx=(0,5))

        ttk.Label(date_input_frame, text="Day:").pack(side=tk.LEFT, padx=(0,2))
        self.event_day_var = tk.StringVar()
        self.event_day_entry = ttk.Entry(date_input_frame, textvariable=self.event_day_var, width=4)
        self.event_day_entry.pack(side=tk.LEFT)
        

        # --- Add Keywords ---
        keywords_frame = ttk.LabelFrame(metadata_main_frame, text="Add Keywords")
        keywords_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(keywords_frame, text="Keywords (comma-separated):").pack(side=tk.LEFT, padx=5, pady=2)
        self.event_keywords_var = tk.StringVar()
        self.event_keywords_entry = ttk.Entry(keywords_frame, textvariable=self.event_keywords_var) 
        self.event_keywords_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=2)
        

        # --- Save and Apply Buttons ---
        action_button_frame = ttk.Frame(metadata_main_frame)
        action_button_frame.pack(fill=tk.X, padx=5, pady=10)

        self.save_metadata_button = ttk.Button(action_button_frame, text="Save Event Metadata JSON", command=self.save_event_metadata, state=tk.DISABLED)
        self.save_metadata_button.pack(side=tk.LEFT, padx=5)

        self.apply_metadata_button = ttk.Button(action_button_frame, text="Apply Metadata to Photos", command=self.apply_metadata_to_photos, state=tk.DISABLED)
        self.apply_metadata_button.pack(side=tk.LEFT, padx=5)


    def open_google_maps(self):
        city = self.event_city_var.get()
        country = self.event_country_var.get()
        lat = self.event_latitude_var.get()
        lon = self.event_longitude_var.get()
        
        query_location = ""
        if city:
            query_location += city
        if country:
            if query_location: query_location += ", "
            query_location += country

        # Use a more reliable base Google Maps URL. 
        # The "googleusercontent.com" domain is not standard for direct map access.
        # Using maps.google.com with a query parameter 'q' is more robust.
        base_url = "https://maps.google.com/"
        params = {}

        if lat and lon: 
            try:
                float(lat) 
                float(lon) 
                # For specific coordinates, use the @lat,lon,zoom syntax or ll=lat,lon&z=zoom
                # A simple query with lat,lon should also work to center the map.
                params['q'] = f"{lat},{lon}"
                params['ll'] = f"{lat},{lon}" # Center map
                params['z'] = "10" # Zoom level
            except ValueError:
                if query_location: 
                    params['q'] = query_location
        elif query_location: 
             params['q'] = query_location
        else: # If nothing is provided, just open generic maps
            params['q'] = "Ireland" # Default to a broader location if no input

        # Construct the URL with parameters
        if params:
            url = base_url + "?" + urllib.parse.urlencode(params)
        else:
            url = base_url # Fallback to generic maps if no params could be formed

        webbrowser.open(url, new=2)
        messagebox.showinfo("Open Map", 
                            "Google Maps opened in your browser.\n"
                            "1. Find your precise location.\n"
                            "2. Right-click on the map and select 'What's here?' or click the coordinates usually displayed at the bottom or in a pop-up.\n"
                            "3. Copy the latitude and longitude.\n"
                            "4. Paste them into the Latitude and Longitude fields here.",
                            parent=self)


    def select_event_from_staging(self):
        staging_root = self.app_config.get_path('phone_staging_path')
        if not staging_root or not os.path.isdir(staging_root):
            messagebox.showerror("Error", "Phone Staging Directory not set or invalid (Config tab).", parent=self)
            return
        selected_path = filedialog.askdirectory(initialdir=staging_root, title="Select Event Folder from Staging Area", parent=self)
        if selected_path:
            self.current_selected_staging_event_path = selected_path
            event_name = os.path.basename(selected_path)
            self.selected_staging_event_label.config(text=f"Selected: {event_name} ({self.count_photos(selected_path)} photos)")
            self.import_button.config(state=tk.NORMAL)
            self.current_event_name.set(event_name) 
            self.save_metadata_button.config(state=tk.DISABLED)
            self.apply_metadata_button.config(state=tk.DISABLED)
            self.clear_metadata_fields() 

    def count_photos(self, directory_path):
        count = 0
        if not directory_path: return 0
        for item in os.listdir(directory_path):
            if item.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.heic', '.webp')): count += 1
        return count

    def import_event_to_workspace(self):
        if not self.current_selected_staging_event_path:
            messagebox.showerror("Error", "No event folder selected from staging.", parent=self)
            return
        event_name = os.path.basename(self.current_selected_staging_event_path)
        imported_events_root = self.app_config.get_path('imported_events_path')
        self.current_imported_event_path = os.path.join(imported_events_root, event_name)
        if os.path.exists(self.current_imported_event_path):
            if not messagebox.askyesno("Confirm", f"Event '{event_name}' already exists in workspace. Overwrite?", parent=self):
                self.import_status_label.config(text=f"Import of '{event_name}' cancelled.")
                return
            shutil.rmtree(self.current_imported_event_path)
        try:
            shutil.copytree(self.current_selected_staging_event_path, self.current_imported_event_path)
            create_dot_nomedia(self.current_imported_event_path)
            num_photos = self.count_photos(self.current_imported_event_path)
            self.import_status_label.config(text=f"Event '{event_name}' ({num_photos} photos) imported to workspace.")
            self.current_event_name.set(event_name) 
            self.load_or_init_metadata_for_current_event() 
            self.save_metadata_button.config(state=tk.NORMAL)
            if os.path.exists(os.path.join(self.current_imported_event_path, "EventMetadata.json")):
                 self.apply_metadata_button.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import event: {e}", parent=self)
            self.import_status_label.config(text=f"Import failed for '{event_name}'.")
            self.current_imported_event_path = None 

    def clear_metadata_fields(self):
        self.event_year_var.set("")
        self.event_month_var.set("")
        self.event_day_var.set("")
        self.event_city_var.set("")
        self.event_country_var.set("")
        self.event_latitude_var.set("")
        self.event_longitude_var.set("")
        self.event_keywords_var.set("")

    def load_or_init_metadata_for_current_event(self):
        self.clear_metadata_fields() 
        if not self.current_imported_event_path: return

        metadata_file_path = os.path.join(self.current_imported_event_path, "EventMetadata.json")
        if os.path.exists(metadata_file_path):
            try:
                with open(metadata_file_path, 'r') as f: data = json.load(f)
                
                event_date_str = data.get('event_date', '')
                if event_date_str:
                    try:
                        dt_obj = datetime.strptime(event_date_str.split(" ")[0], "%Y-%m-%d") 
                        self.event_year_var.set(str(dt_obj.year))
                        self.event_month_var.set(str(dt_obj.month).zfill(2))
                        self.event_day_var.set(str(dt_obj.day).zfill(2))
                    except ValueError:
                        print(f"Could not parse date from EventMetadata.json: {event_date_str}")
                        self.init_default_date_fields() 
                else:
                     self.init_default_date_fields()

                self.event_city_var.set(data.get('event_city', ''))
                self.event_country_var.set(data.get('event_country', ''))
                self.event_latitude_var.set(data.get('event_latitude', ''))
                self.event_longitude_var.set(data.get('event_longitude', ''))
                self.event_keywords_var.set(", ".join(data.get('event_keywords', [])))
                print(f"Loaded metadata for {self.current_event_name.get()}")
            except json.JSONDecodeError:
                 messagebox.showerror("Error", f"Could not decode EventMetadata.json for {self.current_event_name.get()}", parent=self)
                 self.init_default_metadata_fields() 
        else:
            self.init_default_metadata_fields() 

    def init_default_date_fields(self):
        now = datetime.now()
        self.event_year_var.set(str(now.year))
        self.event_month_var.set(str(now.month).zfill(2))
        self.event_day_var.set(str(now.day).zfill(2))

    def init_default_metadata_fields(self):
        self.init_default_date_fields()
        self.event_city_var.set("")
        self.event_country_var.set("")
        self.event_latitude_var.set("")
        self.event_longitude_var.set("")
        self.event_keywords_var.set("")

    def save_event_metadata(self):
        if not self.current_imported_event_path:
            messagebox.showerror("Error", "No event imported to workspace.", parent=self)
            return

        year_str = self.event_year_var.get()
        month_str = self.event_month_var.get()
        day_str = self.event_day_var.get()

        try:
            event_dt = datetime(int(year_str), int(month_str), int(day_str), 0, 0, 0)
            event_date_to_save = event_dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            messagebox.showerror("Invalid Date", "Please enter a valid Year, Month, and Day.", parent=self)
            return

        lat_str = self.event_latitude_var.get()
        lon_str = self.event_longitude_var.get()
        try: 
            if lat_str: float(lat_str)
            if lon_str: float(lon_str)
        except ValueError:
            messagebox.showerror("Invalid Coordinates", "Latitude and Longitude must be valid numbers if provided.", parent=self)
            return

        metadata = {
            "event_name": self.current_event_name.get(),
            "event_date": event_date_to_save, 
            "event_city": self.event_city_var.get(),
            "event_country": self.event_country_var.get(),
            "event_latitude": lat_str,
            "event_longitude": lon_str,
            "event_keywords": [kw.strip() for kw in self.event_keywords_var.get().split(',') if kw.strip()]
        }
        metadata_file_path = os.path.join(self.current_imported_event_path, "EventMetadata.json")
        try:
            with open(metadata_file_path, 'w') as f: json.dump(metadata, f, indent=4)
            messagebox.showinfo("Metadata", f"Metadata saved to {metadata_file_path}", parent=self)
            self.apply_metadata_button.config(state=tk.NORMAL)
        except IOError as e: messagebox.showerror("Error", f"Could not save metadata: {e}", parent=self)

    def apply_metadata_to_photos(self):
        if not self.current_imported_event_path:
            messagebox.showerror("Error", "No event imported to workspace.", parent=self)
            return
        metadata_file_path = os.path.join(self.current_imported_event_path, "EventMetadata.json")
        if not os.path.exists(metadata_file_path):
            messagebox.showerror("Error", "EventMetadata.json not found. Please save metadata first.", parent=self)
            return
        
        try:
            with open(metadata_file_path, 'r') as f: event_metadata_dict = json.load(f)
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Could not read EventMetadata.json.", parent=self)
            return

        success_count, fail_count = 0, 0
        photo_files = [f for f in os.listdir(self.current_imported_event_path)
                       if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.heic', '.webp'))]
        if not photo_files:
            messagebox.showinfo("Info", "No photos in event folder to apply metadata to.", parent=self)
            return

        for photo_name in photo_files:
            photo_path = os.path.join(self.current_imported_event_path, photo_name)
            try:
                self.metadata_manager.apply_event_metadata_to_photo(photo_path, event_metadata_dict)
                success_count += 1
            except Exception as e:
                print(f"Failed to apply metadata to {photo_name}: {e}")
                fail_count += 1
        messagebox.showinfo("Metadata Application", 
                            f"Metadata applied to {success_count} photos.\n"
                            f"Failed for {fail_count} photos. Check console for details.", 
                            parent=self)
