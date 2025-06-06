# MyPhotoProcessor/src/app_config.py
import configparser
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE_PATH = os.path.join(PROJECT_ROOT, 'config.ini')

DEFAULT_PHOTO_STORAGE_PATH = os.path.join(os.path.expanduser("~"), "PhotoStorage")
DEFAULT_IMPORTED_EVENTS_PATH = os.path.join(os.path.expanduser("~"), "MyPhotoProcessorEvents")
DEFAULT_FINAL_PHOTOS_PATH = os.path.join(os.path.expanduser("~"), "MyPhotoProcessorFinalOutput") # New default

# --- Configuration Keys ---
CONFIG_SECTION_PATHS = 'Paths'
CONFIG_KEY_PHOTO_STORAGE = 'PhotoStorageDirectory'
CONFIG_KEY_IMPORTED_EVENTS = 'ImportedEventsDirectory'
CONFIG_KEY_FINAL_PHOTOS = 'FinalPhotosDirectory' # New key

def _load_config_parser():
    # ... (as before) ...
    parser = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE_PATH):
        parser.read(CONFIG_FILE_PATH)
    return parser

def _save_config_parser(parser):
    # ... (as before) ...
    try:
        with open(CONFIG_FILE_PATH, 'w') as configfile:
            parser.write(configfile)
    except IOError as e:
        print(f"Error saving configuration file to {CONFIG_FILE_PATH}: {e}")


def initialize_config():
    parser = _load_config_parser()
    updated = False

    if not parser.has_section(CONFIG_SECTION_PATHS):
        parser.add_section(CONFIG_SECTION_PATHS)
        updated = True

    if not parser.has_option(CONFIG_SECTION_PATHS, CONFIG_KEY_PHOTO_STORAGE):
        parser.set(CONFIG_SECTION_PATHS, CONFIG_KEY_PHOTO_STORAGE, DEFAULT_PHOTO_STORAGE_PATH)
        updated = True
    
    if not parser.has_option(CONFIG_SECTION_PATHS, CONFIG_KEY_IMPORTED_EVENTS):
        parser.set(CONFIG_SECTION_PATHS, CONFIG_KEY_IMPORTED_EVENTS, DEFAULT_IMPORTED_EVENTS_PATH)
        updated = True

    # --- ADD HANDLING FOR FINAL PHOTOS PATH ---
    if not parser.has_option(CONFIG_SECTION_PATHS, CONFIG_KEY_FINAL_PHOTOS):
        parser.set(CONFIG_SECTION_PATHS, CONFIG_KEY_FINAL_PHOTOS, DEFAULT_FINAL_PHOTOS_PATH)
        updated = True
    # --- END ---

    if updated:
        _save_config_parser(parser)
    return parser

def get_photo_storage_path():
    # ... (as before) ...
    parser = initialize_config()
    return parser.get(CONFIG_SECTION_PATHS, CONFIG_KEY_PHOTO_STORAGE, fallback=DEFAULT_PHOTO_STORAGE_PATH)


def save_photo_storage_path(path):
    # ... (as before) ...
    parser = _load_config_parser()
    if not parser.has_section(CONFIG_SECTION_PATHS):
        parser.add_section(CONFIG_SECTION_PATHS)
    parser.set(CONFIG_SECTION_PATHS, CONFIG_KEY_PHOTO_STORAGE, path)
    _save_config_parser(parser)
    print(f"Photo storage path saved: {path}")


def get_setting(section, key, fallback=None): # Ensure this function exists
    parser = initialize_config()
    return parser.get(section, key, fallback=fallback)

if __name__ == '__main__':
    initialize_config()
    print(f"Photo Storage Path: {get_photo_storage_path()}")
    imported_events_path = get_setting(CONFIG_SECTION_PATHS, CONFIG_KEY_IMPORTED_EVENTS, "DefaultEventsPathNotSet")
    print(f"Imported Events Path: {imported_events_path}")
    final_photos_path = get_setting(CONFIG_SECTION_PATHS, CONFIG_KEY_FINAL_PHOTOS, "DefaultFinalPhotosPathNotSet") # Test new setting
    print(f"Final Photos Path: {final_photos_path}")
