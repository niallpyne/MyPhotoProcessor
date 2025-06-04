Project Title: My Photo Processor

Description:

A desktop application for macOS designed to streamline the process of importing, organizing, and enhancing batches of scanned photos. This tool helps users correct EXIF metadata (like dates and geo-locations which are often incorrect for scanned images) and perform image processing tasks such as auto-cropping borders and adjusting image quality before final archiving or sharing.

The application features a tabbed interface for a clear workflow:

Config: Set up base directories for photo staging and output.
Import & Metadata: Import photo batches (events), manage event-specific metadata (date, location, keywords) via a JSON file, and apply these corrections to photo EXIF data. Includes a feature to fetch geo-coordinates by opening Google Maps.
Process Photos: View and process individual photos within an event. Features include:
Automatic border cropping optimized for photos scanned against a consistent colored background (e.g., pale blue), with configurable HSV ranges and inward offset.
Manual draw cropping.
Percentage-based cropping.
Image rotation (-90°, +90°, 180°, fine-tuning).
Enhancements like contrast adjustment (CLAHE), noise reduction (Bilateral Filter), and sharpening (Unsharp Mask) using OpenCV.
Ability to preview changes before saving.
EXIF data viewer for original and processed images, with indicators for applied metadata.
Reporting: (Basic framework for future comparison of original vs. processed images).
Built with Python and Tkinter (using ttk for themed widgets) for the GUI, and leveraging Pillow and OpenCV for image manipulation and EXIF data handling with piexif. The project is structured with a focus on readable and maintainable code.

