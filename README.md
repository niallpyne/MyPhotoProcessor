# My Photo Processor

## 1. Project Description

My Photo Processor is a desktop application developed in Python using Tkinter (with ttk themed widgets), Pillow, OpenCV, and piexif. It is designed to streamline the workflow for users who scan old photographs and need to:

* Organize batches of photos (referred to as "events").
* Correct or add essential EXIF metadata (like capture date, location, and keywords) which is often missing or incorrect for scanned images.
* Perform image processing tasks such as automatic and manual border cropping, rotation, and basic image enhancements.
* Manage photos through a defined workflow from initial import to a final, processed state.

The application aims to provide a user-friendly GUI for these common tasks, leveraging powerful image processing libraries under the hood. It is intended to be cross-platform (tested primarily on macOS, with considerations for Linux and Windows).

## 2. Features

The application is organized into a tabbed interface:

### 2.1. Config Tab
* **Photo Storage Root Path:** Allows the user to define a primary, absolute root directory on their system where all photo data (imported, processed, final) will be stored. This keeps photo data separate from the application code.
* **Event Folder Names:** Allows configuration of the names for subfolders within the Photo Storage Root for:
    * Imported Phone Events (where photos are initially placed by the user)
    * Processed Events
    * Final Photos
* **View Default Parameters:** Displays current default values for various OpenCV processing parameters and auto-crop settings (e.g., CLAHE limits, HSV ranges for blue background detection, inward offset). These are primarily view-only in this tab and are managed in `AppConfig/AppConfig.json`.
* **Save Configuration:** Saves the path settings to `AppConfig/AppConfig.json`.

### 2.2. Event & Metadata Tab (Formerly "Import & Metadata")
* **No Direct Import:** The application no longer performs a file copy/import step. Users are expected to place their scanned photo event folders directly into the `[Photo Storage Root Path]/ImportedPhoneEvents/` directory.
* **Event Selection:**
    * Browse and select an event folder from the `ImportedPhoneEvents` directory.
    * Displays the number of photos in the selected event.
* **Metadata Management (for the selected event):**
    * **Event Name:** Displayed, based on the folder name.
    * **Assign Location:**
        * Input fields for City and Country.
        * Button to open Google Maps in a web browser, pre-filled with City/Country (if provided) or Latitude/Longitude (if provided), to help the user find precise GPS coordinates.
        * Input fields for Latitude and Longitude (e.g., decimal degrees).
    * **Correct Photo Date:**
        * Input fields for Year, Month, and Day for the event. Time is not required and defaults to 00:00:00.
    * **Add Keywords:**
        * Text entry for comma-separated keywords for the event.
* **Actions:**
    * **Save Event Metadata JSON:** Saves the entered metadata (location, date, keywords) into an `EventMetadata.json` file within the selected event folder in `ImportedPhoneEvents`.
    * **Apply Metadata to Photos:** Reads the `EventMetadata.json` for the selected event and writes the specified date, location, and keywords as EXIF tags to all image files within that event folder using `piexif`.

### 2.3. Process Photos Tab
* **Event Selection:** Dropdown to select an event from the `ImportedPhoneEvents` directory.
* **Photo Navigation:** "Previous" and "Next" buttons to navigate through photos in the selected event. Displays "Photo X of Y".
* **Image Previews:**
    * **Original Image:** Displayed on a canvas. Supports right-click to enlarge.
    * **Processed Preview:** Displays the result of the latest processing operation. Supports click to enlarge.
* **EXIF Data:**
    * "EXIF" button below the original image display to show its EXIF data in a new window.
    * "EXIF" button below the processed image display to show the EXIF data of the *saved processed file* (if it exists) in a new window.
    * Visual indicators (✓/✗) next to each EXIF button:
        * Original: '✓' if `EventMetadata.json` for the event exists and contains user-defined entries (keywords, location). '✗' otherwise.
        * Processed: '✓' if a processed preview exists for the current session *and* the original metadata was defined. '✗' otherwise (resets to '✗' when a new original photo is loaded).
* **Processing Controls:**
    * **Auto-Orient:** Checkbox to enable/disable automatic image orientation based on EXIF data (performed by Pillow).
    * **Cropping Mode:**
        * **Auto-Crop (Blue BG):** Radio button to select automatic border cropping optimized for photos scanned against a known pale blue background.
            * UI fields to input/adjust HSV (Hue, Saturation, Value) lower and upper ranges for background detection (pre-filled from config).
            * UI field for "Inward Offset (px)" for the auto-crop.
            * "Find Optimal HSV" button: Iterates through predefined alternative HSV ranges to find one that yields an effective crop and updates the UI HSV fields if a better one is found.
        * **Percentage:** Radio button for percentage-based cropping from each side (Top, Right, Bottom, Left). UI fields for percentage input.
        * **Manual Draw:** Radio button to enable manual crop by drawing a rectangle on the "Original Image" canvas.
    * **Rotation:**
        * Slider for fine-tuning rotation (-45° to +45°).
        * Entry field to display/set rotation value.
        * Buttons for quick rotations: "-90°", "+90°", "180°".
        * "Reset" button to set rotation to 0°.
    * **OpenCV Enhancements:** Checkboxes to enable/disable:
        * CLAHE (Contrast Limited Adaptive Histogram Equalization)
        * Bilateral Filter (for smoothing while preserving edges)
        * Unsharp Mask (for sharpening)
* **Actions:**
    * **Preview Changes:** Applies all selected orientation, cropping, rotation, and enhancement settings to the current original photo and displays the result in the "Processed Preview" area.
    * **Save Processed Photo:** Saves the currently displayed processed preview (or re-processes if no preview exists) to the `[Photo Storage Root Path]/ProcessedEvents/[EventName]/` directory. Preserves EXIF data (carrying over user-applied metadata from the original).
    * **Process All in Event:** Applies the current UI settings (except manual draw crop, which results in no crop for batch) to all photos in the selected event and saves them to the `ProcessedEvents` directory.
    * **Move Processed to Final:** Copies all images from the current event's subfolder in `ProcessedEvents` to a corresponding subfolder in `FinalPhotos`. Warns if the destination event folder already exists and is not empty.

### 2.4. Reporting Tab
* **Event and Photo Selection:** Dropdowns to select an event (from `ImportedPhoneEvents`) and a specific photo within that event.
* **Side-by-Side Comparison:**
    * Displays the original photo.
    * Displays the corresponding processed photo (from `ProcessedEvents`) or final photo (from `FinalPhotos`), whichever is found first.
    * Allows for visual comparison of before and after processing.

## 3. File Structure


MyPhotoProcessor/
├── AppConfig/
│   └── AppConfig.json       # Stores user configurations (paths, default parameters)
├── src/
│   ├── init.py          # Makes 'src' a Python package
│   ├── main.py              # Main application entry point
│   ├── app_config.py        # Class for managing AppConfig.json
│   ├── file_utils.py        # Utility functions for file/directory operations
│   ├── image_processor.py   # Class for all image manipulation logic (OpenCV, Pillow)
│   ├── metadata_manager.py  # Class for reading/writing EXIF metadata (piexif)
│   ├── ui_config_tab.py     # UI and logic for the Config tab
│   ├── ui_import_tab.py     # UI and logic for the Event & Metadata tab
│   ├── ui_process_tab.py    # UI and logic for the Process Photos tab
│   └── ui_reporting_tab.py  # UI and logic for the Reporting tab
├── requirements.txt         # List of Python dependencies
└── README.md                # This file


**User Photo Data Structure (Example, configured by user):**

[User Defined Photo Storage Root Path, e.g., /Users/niall/PhotoStorage]/
├── ImportedPhoneEvents/
│   ├── EventName1/
│   │   ├── photo1.jpg
│   │   ├── photo2.png
│   │   └── EventMetadata.json
│   └── EventName2/
│       └── ...
├── ProcessedEvents/
│   ├── EventName1/
│   │   ├── photo1.jpg
│   │   └── photo2.png
│   └── EventName2/
│       └── ...
└── FinalPhotos/
├── EventName1/
│   ├── photo1.jpg
│   └── photo2.png
└── EventName2/
└── ...


## 4. Setup and Installation

1.  **Prerequisites:**
    * Python 3.9 or newer recommended.
    * `pip` (Python package installer).

2.  **Clone the Repository (if applicable):**
    ```bash
    git clone [repository_url]
    cd MyPhotoProcessor
    ```

3.  **Create a Virtual Environment (Recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On macOS/Linux
    # venv\Scripts\activate   # On Windows
    ```

4.  **Install Dependencies:**
    Create a `requirements.txt` file in the project root with the following content:
    ```
    Pillow
    piexif
    opencv-python
    numpy
    ```
    Then run:
    ```bash
    pip install -r requirements.txt
    ```

## 5. How to Run

Navigate to the directory and run:
```bash
Activate the virtual environment venv
python src/main.py

Alternatively, if the project root is in your PYTHONPATH:

python src/main.py

Upon first run, the application will create an AppConfig/AppConfig.json file with default paths and settings. You should visit the Config tab to set your "Photo Storage Root Path" and verify other folder names.

6. Key Libraries Used
Tkinter (with ttk themed widgets): For the graphical user interface.

Pillow (PIL Fork): For image file I/O, basic image manipulations, and EXIF orientation.

OpenCV (cv2): For advanced image processing tasks (cropping, enhancements, color space conversions).

NumPy: For numerical operations, primarily used by OpenCV.

piexif: For reading and writing EXIF metadata to JPEG and TIFF files.

Standard Python Libraries: os, json, shutil, datetime, webbrowser, urllib.parse.

7. Configuration (AppConfig/AppConfig.json)
The application stores its configuration in AppConfig/AppConfig.json within the project directory. Key configurable items include:

photo_storage_root_path: The main absolute path where your photo event folders will be stored. Users should set this to their desired location. (Default: ~/PhotoStorage)

imported_phone_events_folder_name: (Default: "ImportedPhoneEvents")

processed_events_folder_name: (Default: "ProcessedEvents")

final_photos_folder_name: (Default: "FinalPhotos")

Default OpenCV and auto-crop parameters (e.g., HSV values for blue background detection).

8. Typical Workflow
Copy scanned photo folders (events) from your phone/scanner to the directory specified as [Photo Storage Root Path]/ImportedPhoneEvents/.

Open the "My Photo Processor" application.

Go to the Config tab and set your "Photo Storage Root Path" and review/adjust folder names. Save configuration. A restart might be prompted for path changes to take full effect initially.

Go to the Event & Metadata tab.

Click "Browse Imported Phone Events..." to select an event folder.

Enter/correct the event date, location details (using map lookup if needed), and keywords.

Click "Save Event Metadata JSON".

Click "Apply Metadata to Photos" to write this information into the EXIF data of the images in that event folder.

Go to the Process Photos tab.

Select the event from the dropdown.

Navigate through photos using "Previous"/"Next".

Use the cropping tools (Auto-Crop, Percentage, Manual Draw), rotation, and enhancement checkboxes.

Click "Preview Changes" to see the effect.

Adjust "Auto-Crop (Blue BG)" HSV parameters or use "Find Optimal HSV" if needed.

Click "Save Processed Photo" to save the modified image to the ProcessedEvents/[EventName]/ folder. The corrected EXIF data is preserved.

Alternatively, use "Process All in Event" to apply current settings to all photos in the event.

Once all photos in an event are processed and saved, click "Move Processed to Final" to copy them from ProcessedEvents to FinalPhotos.

Use the Reporting tab to compare original and processed/final images.

9. Known Issues / Limitations
Styling of ttk.Button background colors for EXIF status indicators was changed to text labels (✓/✗) due to cross-platform inconsistencies with ttk themes (especially on macOS).

The "Find Optimal HSV" feature iterates through a predefined set of alternatives; for very specific or unusual blue backgrounds, manual HSV tuning might still be required.

Batch processing with "Manual Draw" crop selected will result in no cropping for the batch items.

10. Future Enhancements (Potential)
More sophisticated auto-cropping algorithms or learning capabilities.

Advanced color correction tools.

Direct integration with exiftool for more comprehensive metadata editing.

User-configurable presets for processing settings.

Ability to manage/edit metadata for individual photos,