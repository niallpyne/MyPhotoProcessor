# metadata_manager.py
import piexif
import piexif.helper # For UserComment encoding
import json # Not strictly used here, but often useful with metadata
from datetime import datetime
import os

# Helper function for GPS rational format (simplified)
def _to_deg_min_sec(value_str):
    try:
        value = float(value_str)
    except (ValueError, TypeError): # Handle None or empty string
        return None

    abs_value = abs(value)
    deg = int(abs_value)
    min_float = (abs_value - deg) * 60
    min_val = int(min_float)
    sec_float = (min_float - min_val) * 60
    # piexif expects rationals: (numerator, denominator)
    # Increased precision for seconds
    return [(deg, 1), (min_val, 1), (int(sec_float * 1000), 1000)]

class MetadataManager:
    def __init__(self):
        pass 

    def get_photo_datetime_original(self, photo_path):
        """Attempts to get the DateTimeOriginal from EXIF."""
        try:
            exif_dict = piexif.load(photo_path)
            date_str_bytes = exif_dict.get("Exif", {}).get(piexif.ExifIFD.DateTimeOriginal)
            if date_str_bytes:
                return date_str_bytes.decode('utf-8')
        except Exception as e:
            print(f"Error reading DateTimeOriginal from {photo_path}: {e}")
        return None

    def apply_event_metadata_to_photo(self, photo_path, event_metadata_dict):
        """
        Applies metadata from the event's JSON to the photo's EXIF.
        event_metadata_dict should contain 'event_date' (YYYY-MM-DD HH:MM:SS), 
        'event_city', 'event_country', 'event_latitude', 'event_longitude', 'event_keywords'.
        """
        try:
            exif_dict = piexif.load(photo_path)
        except piexif.InvalidImageDataError: 
            print(f"Warning: No EXIF data found in {photo_path}. Creating new EXIF structure.")
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
        except Exception as e:
            print(f"Error loading EXIF from {photo_path}: {e}. Skipping.")
            return


        # Date/Time - event_date_dict now provides "YYYY-MM-DD HH:MM:SS"
        event_date_str_full = event_metadata_dict.get('event_date') 
        if event_date_str_full:
            try:
                # EXIF DateTimeOriginal format is "YYYY:MM:DD HH:MM:SS"
                dt_obj = datetime.strptime(event_date_str_full, "%Y-%m-%d %H:%M:%S")
                exif_date_str = dt_obj.strftime("%Y:%m:%d %H:%M:%S") # Convert to EXIF format

                exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = exif_date_str.encode('utf-8')
                exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = exif_date_str.encode('utf-8')
                exif_dict["0th"][piexif.ImageIFD.DateTime] = exif_date_str.encode('utf-8')

            except ValueError as ve:
                print(f"Date format error for '{event_date_str_full}': {ve}")


        # Keywords (UserComment or XPKeywords)
        keywords_list = event_metadata_dict.get('event_keywords', [])
        if keywords_list:
            # Using piexif.helper for UserComment with UNICODE for broader character support
            try:
                exif_dict["Exif"][piexif.ExifIFD.UserComment] = piexif.helper.dump_comment(", ".join(keywords_list), encoding="unicode")
            except Exception as e_comment:
                print(f"Error encoding UserComment: {e_comment}")
                # Fallback to ASCII if unicode fails for some reason
                try:
                    exif_dict["Exif"][piexif.ExifIFD.UserComment] = piexif.helper.dump_comment(", ".join(keywords_list), encoding="ascii")
                except Exception as e_ascii_comment:
                    print(f"Fallback ASCII UserComment encoding also failed: {e_ascii_comment}")


        # Location Description (City, Country can be combined here or put in separate tags if available)
        city_str = event_metadata_dict.get('event_city', '')
        country_str = event_metadata_dict.get('event_country', '')
        location_description = []
        if city_str: location_description.append(city_str)
        if country_str: location_description.append(country_str)
        
        if location_description:
            exif_dict["0th"][piexif.ImageIFD.ImageDescription] = ", ".join(location_description).encode('utf-8')

        # --- GPS Data ---
        latitude_str = event_metadata_dict.get('event_latitude')
        longitude_str = event_metadata_dict.get('event_longitude')

        if latitude_str and longitude_str: # Only proceed if both are present
            gps_ifd = exif_dict.get("GPS", {}) 
            try:
                lat_val = float(latitude_str) # Ensure they are valid floats
                lon_val = float(longitude_str)

                gps_ifd[piexif.GPSIFD.GPSVersionID] = (2, 3, 0, 0) # Version 2.3.0.0
                
                lat_dms = _to_deg_min_sec(latitude_str)
                if lat_dms:
                    gps_ifd[piexif.GPSIFD.GPSLatitudeRef] = ('N' if lat_val >= 0 else 'S').encode('ascii')
                    gps_ifd[piexif.GPSIFD.GPSLatitude] = lat_dms
                
                lon_dms = _to_deg_min_sec(longitude_str)
                if lon_dms:
                    gps_ifd[piexif.GPSIFD.GPSLongitudeRef] = ('E' if lon_val >= 0 else 'W').encode('ascii')
                    gps_ifd[piexif.GPSIFD.GPSLongitude] = lon_dms
                
                # Add GPSDateStamp and GPSTimeStamp using the event_date
                if event_date_str_full: # Use the full date-time string from metadata
                    dt_obj_for_gps = datetime.strptime(event_date_str_full, "%Y-%m-%d %H:%M:%S")
                    gps_ifd[piexif.GPSIFD.GPSDateStamp] = dt_obj_for_gps.strftime("%Y:%m:%d").encode('ascii')
                    gps_ifd[piexif.GPSIFD.GPSTimeStamp] = [
                        (dt_obj_for_gps.hour, 1), (dt_obj_for_gps.minute, 1), (dt_obj_for_gps.second, 1)
                    ]
                
                if gps_ifd: # Only assign if we actually added GPS data
                    exif_dict["GPS"] = gps_ifd 
                    print(f"Prepared GPS data for {os.path.basename(photo_path)}")

            except ValueError:
                print(f"Invalid latitude/longitude format for {os.path.basename(photo_path)}. GPS data skipped.")
            except Exception as e_gps:
                print(f"Error processing GPS data for {os.path.basename(photo_path)}: {e_gps}")


        # Clean up problematic tags
        if piexif.ExifIFD.MakerNote in exif_dict.get("Exif", {}):
            del exif_dict["Exif"][piexif.ExifIFD.MakerNote]
        
        # Ensure thumbnail is not None if it's not actual thumbnail data
        if "thumbnail" in exif_dict and exif_dict["thumbnail"] is None:
             del exif_dict["thumbnail"]

        try:
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, photo_path)
            print(f"Applied EXIF metadata to {os.path.basename(photo_path)}")
        except Exception as e:
            print(f"Error writing EXIF to {os.path.basename(photo_path)}: {e}")
            # Fallback: Try saving without thumbnail if it's problematic
            try:
                if "thumbnail" in exif_dict: del exif_dict["thumbnail"]
                exif_bytes = piexif.dump(exif_dict)
                piexif.insert(exif_bytes, photo_path)
                print(f"Applied EXIF metadata (no thumbnail) to {os.path.basename(photo_path)}")
            except Exception as e2:
                print(f"Still failed to write EXIF (no thumbnail) to {os.path.basename(photo_path)}: {e2}")
