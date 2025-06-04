import json
import os

APP_CONFIG_DIR_NAME = "AppConfig"
APP_CONFIG_FILE_NAME = "AppConfig.json"

class AppConfig:
    def __init__(self, project_root):
        self.project_root = project_root
        self.config_dir_path = os.path.join(self.project_root, APP_CONFIG_DIR_NAME)
        self.config_file_path = os.path.join(self.config_dir_path, APP_CONFIG_FILE_NAME)
        self.settings = {}
        self._ensure_config_dir_exists()
        self.load_config()

    def _ensure_config_dir_exists(self):
        os.makedirs(self.config_dir_path, exist_ok=True)

    def load_config(self):
        if os.path.exists(self.config_file_path):
            try:
                with open(self.config_file_path, 'r') as f:
                    self.settings = json.load(f)
                print(f"Configuration loaded from {self.config_file_path}")
            except json.JSONDecodeError:
                print(f"Error decoding JSON from {self.config_file_path}. Using defaults.")
                self._set_default_settings()
        else:
            print(f"Config file not found. Creating with defaults: {self.config_file_path}")
            self._set_default_settings()
            self.save_config()

    def _set_default_settings(self):
        self.settings['phone_staging_path'] = os.path.expanduser("~/Desktop/PhonePhotoStaging")
        self.settings['imported_events_path'] = "ImportedEvents" 
        self.settings['final_photos_path'] = "FinalPhotos"     

        # OpenCV related defaults
        self.settings['clahe_clip_limit'] = 2.0
        self.settings['clahe_tile_grid_size'] = 8
        self.settings['bilateral_d'] = 9
        self.settings['bilateral_sigma_color'] = 75
        self.settings['bilateral_sigma_space'] = 75
        self.settings['unsharp_sigma'] = 1.0
        self.settings['unsharp_strength'] = 1.5
        
        # Default crop percentages
        self.settings['default_crop_top'] = 2.0
        self.settings['default_crop_right'] = 2.0
        self.settings['default_crop_bottom'] = 2.0
        self.settings['default_crop_left'] = 2.0
        
        # Settings for Blue Background Auto-Crop
        # HSV ranges for "pale blue" (OpenCV H is 0-179, S is 0-255, V is 0-255)
        # These are starting points and might need tuning based on actual background.
        self.settings['pale_blue_hsv_lower'] = [90, 40, 100]  # Lowered Sat and Val min
        self.settings['pale_blue_hsv_upper'] = [130, 255, 255]
        self.settings['auto_crop_inward_offset'] = 5 # Default inward offset in pixels for auto-crop

    def save_config(self):
        try:
            with open(self.config_file_path, 'w') as f:
                json.dump(self.settings, f, indent=4)
            print(f"Configuration saved to {self.config_file_path}")
        except IOError as e:
            print(f"Error saving configuration to {self.config_file_path}: {e}")

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def get_path(self, path_key, default_relative_name_if_missing=None):
        path_str = self.settings.get(path_key)
        if not path_str:
            if default_relative_name_if_missing: path_str = default_relative_name_if_missing
            elif path_key == 'imported_events_path': path_str = "ImportedEvents"
            elif path_key == 'final_photos_path': path_str = "FinalPhotos"
            elif path_key == 'phone_staging_path': path_str = os.path.expanduser("~/Desktop/PhonePhotoStaging")
            else: return None
            self.settings[path_key] = path_str # Store default if it was missing
        if os.path.isabs(path_str): return path_str
        return os.path.normpath(os.path.join(self.project_root, path_str))

    def update_setting(self, key, value):
        self.settings[key] = value
