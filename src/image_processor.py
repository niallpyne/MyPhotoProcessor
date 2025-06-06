# MyPhotoProcessor/src/image_processor.py
import os
from . import app_config # Relative import
# You might import other libraries like Pillow (PIL) or OpenCV here
# when you add more detailed image manipulation logic.
# from .metadata_manager import MetadataManager # If you intend to use it here

class ImageProcessor:
    def __init__(self):
        """
        Initializes the ImageProcessor.
        """
        # You can add any setup for the processor here if needed.
        # For example, loading machine learning models, setting default parameters, etc.
        print("DEBUG: ImageProcessor instance created.") # For debugging
        pass

    def process_all_photos_in_configured_folder(self):
        """
        Processes all photos found in the application's configured photo storage directory.
        Returns a tuple: (bool_success, int_files_processed)
        """
        photo_dir = app_config.get_photo_storage_path()

        if not photo_dir or not os.path.isdir(photo_dir):
            print(f"ERROR (ImageProcessor): The configured photo directory '{photo_dir}' is invalid or does not exist.")
            return False, 0 # Indicate failure and 0 files processed

        print(f"INFO (ImageProcessor): Starting photo processing in directory: {photo_dir}")
        image_files_processed = 0
        
        try:
            for item_name in os.listdir(photo_dir):
                item_path = os.path.join(photo_dir, item_name)
                if os.path.isfile(item_path) and item_name.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp')):
                    print(f"  INFO (ImageProcessor): Processing file: {item_path}")
                    
                    # ------------------------------------------------------------------
                    # --- Placeholder for your actual per-image processing logic ---
                    # This is where you would:
                    #   - Open the image (e.g., with Pillow: from PIL import Image; img = Image.open(item_path))
                    #   - Read/write metadata (e.g., using an instance of MetadataManager)
                    #     # metadata_mgr = MetadataManager() # Or pass it in/create once
                    #     # metadata_mgr.apply_event_metadata_to_photo(item_path, your_event_data)
                    #   - Resize, crop, apply filters, etc.
                    #   - Save the processed image (possibly to a different output directory)
                    # For now, we're just counting it.
                    # ------------------------------------------------------------------
                    
                    image_files_processed += 1
            
            print(f"INFO (ImageProcessor): Finished processing. {image_files_processed} image file(s) were found and iterated in {photo_dir}.")
            return True, image_files_processed # Indicate success and count
            
        except FileNotFoundError:
            print(f"ERROR (ImageProcessor): The directory {photo_dir} was not found during processing (it may have been deleted or renamed).")
            return False, image_files_processed
        except PermissionError:
            print(f"ERROR (ImageProcessor): Permission denied when trying to access {photo_dir}.")
            return False, image_files_processed
        except Exception as e:
            print(f"ERROR (ImageProcessor): An unexpected error occurred during processing in {photo_dir}: {e}")
            return False, image_files_processed


# Example usage for standalone testing of this module (optional)
if __name__ == '__main__':
    print("--- Testing image_processor.py standalone ---")
    
    # This setup ensures app_config can find config.ini relative to this file's expected position
    # It might need adjustment if your config.ini isn't two levels up from 'src'
    # For robust testing, it's better to have a dedicated test script or use the main app.
    print("Attempting to initialize configuration for test...")
    try:
        app_config.initialize_config()
        current_photo_path = app_config.get_photo_storage_path()
        print(f"Test: Configured photo storage path: {current_photo_path}")
        if not os.path.isdir(current_photo_path):
            print(f"WARNING (Test): Configured photo path '{current_photo_path}' does not exist. Processing test may not find images.")
    except Exception as e:
        print(f"ERROR (Test): Could not initialize app_config: {e}")
        print("Ensure config.ini is accessible or test via the main application.")
    
    print("\nCreating ImageProcessor instance...")
    processor = ImageProcessor()
    
    print("Calling process_all_photos_in_configured_folder()...")
    success, count = processor.process_all_photos_in_configured_folder()
    
    if success:
        print(f"\nStandalone Test Result: Processing reported success. {count} files iterated.")
    else:
        print(f"\nStandalone Test Result: Processing reported failure. {count} files iterated (before failure).")
    print("--- End of image_processor.py standalone test ---")


