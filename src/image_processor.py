from PIL import Image, ImageOps, ImageFilter
import cv2
import numpy as np
import os
import piexif # Ensure piexif is imported for EXIF manipulation

# Helper function to order points for perspective transform
def _order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)] # Top-left
    rect[2] = pts[np.argmax(s)] # Bottom-right
    
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)] # Top-right
    rect[3] = pts[np.argmax(diff)] # Bottom-left
    return rect

class ImageProcessor:
    def __init__(self, app_config=None):
        self.app_config = app_config

    def _pil_to_cv(self, pil_image):
        if pil_image.mode == 'RGBA': pil_image = pil_image.convert('RGB')
        elif pil_image.mode == 'P': pil_image = pil_image.convert('RGB')
        elif pil_image.mode == 'L': pil_image = pil_image.convert('RGB') 
        return np.array(pil_image)[:, :, ::-1] 

    def _cv_to_pil(self, cv_image_bgr):
        return Image.fromarray(cv_image_bgr[:, :, ::-1]) 

    def auto_orient_pil(self, pil_image):
        try: 
            oriented_image = ImageOps.exif_transpose(pil_image)
            # exif_transpose may or may not keep exif in .info, let's ensure it does
            # if "exif" not in oriented_image.info and "exif" in pil_image.info:
            #    oriented_image.info["exif"] = pil_image.info["exif"]
            return oriented_image
        except Exception as e:
            print(f"Pillow could not auto-orient image: {e}")
            return pil_image

    def crop_image_cv_percent(self, cv_image, top_pct, right_pct, bottom_pct, left_pct):
        height, width = cv_image.shape[:2]
        left = int(width * (left_pct / 100.0))
        top = int(height * (top_pct / 100.0))
        end_y = min(height, int(height * (1 - (bottom_pct / 100.0))))
        end_x = min(width, int(width * (1 - (right_pct / 100.0))))
        left = min(left, end_x -1) if end_x > 0 else 0 
        top = min(top, end_y -1) if end_y > 0 else 0   
        if top >= end_y or left >= end_x: 
            print("Warning: Invalid percentage crop dimensions, returning original image.")
            return cv_image.copy() 
        return cv_image[top:end_y, left:end_x].copy() 

    def crop_image_manual_cv(self, cv_image, crop_box_scaled):
        x1, y1, x2, y2 = map(int, crop_box_scaled) 
        h_orig, w_orig = cv_image.shape[:2]
        x1 = max(0, min(x1, w_orig -1))
        y1 = max(0, min(y1, h_orig -1))
        x2 = max(0, min(x2, w_orig))
        y2 = max(0, min(y2, h_orig))
        if x1 >= x2 or y1 >= y2: 
            print("Warning: Invalid manual crop coordinates, returning original.")
            return cv_image.copy()
        return cv_image[y1:y2, x1:x2].copy()

    def auto_crop_on_color_background(self, cv_image_bgr, hsv_lower_list, hsv_upper_list, inward_offset_pixels=5):
        print(f"Attempting auto-crop on color background. HSV Lower: {hsv_lower_list}, Upper: {hsv_upper_list}")
        original_h, original_w = cv_image_bgr.shape[:2]
        img_area = float(original_h * original_w)
        if img_area == 0:
            print("Auto-Crop (Color BG): Input image has zero area.")
            return cv_image_bgr.copy()

        hsv = cv2.cvtColor(cv_image_bgr, cv2.COLOR_BGR2HSV)
        lower_bound = np.array(hsv_lower_list, dtype=np.uint8)
        upper_bound = np.array(hsv_upper_list, dtype=np.uint8)
        background_mask = cv2.inRange(hsv, lower_bound, upper_bound)
        photo_mask = cv2.bitwise_not(background_mask)

        kernel_open = np.ones((5,5),np.uint8) 
        kernel_close = np.ones((11,11),np.uint8) 
        cleaned_mask = cv2.morphologyEx(photo_mask, cv2.MORPH_OPEN, kernel_open, iterations=2)
        cleaned_mask = cv2.morphologyEx(cleaned_mask, cv2.MORPH_CLOSE, kernel_close, iterations=3)

        contours, _ = cv2.findContours(cleaned_mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            print("Auto-Crop (Color BG): No contours found after masking. Check HSV ranges and background.")
            return cv_image_bgr.copy()

        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        found_photo_contour_approx = None
        for c in contours:
            area = cv2.contourArea(c)
            if not (img_area * 0.05 < area < img_area * 0.99): continue
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4:
                (x_br, y_br, w_br, h_br) = cv2.boundingRect(approx)
                aspect_ratio = w_br / float(h_br) if h_br > 0 else 0
                if 0.3 < aspect_ratio < 3.0: 
                    found_photo_contour_approx = approx
                    print(f"Auto-Crop (Color BG): Found candidate. Area: {area:.0f}, Aspect: {aspect_ratio:.2f}")
                    break
        if found_photo_contour_approx is None:
            print("Auto-Crop (Color BG): No suitable quadrilateral contour found. Returning original.")
            return cv_image_bgr.copy()

        points = found_photo_contour_approx.reshape(4, 2).astype("float32")
        ordered_rect_points = _order_points(points)
        (tl, tr, br, bl) = ordered_rect_points
        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))
        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))
        if maxWidth <= 0 or maxHeight <= 0:
            print("Auto-Crop (Color BG): Calculated zero/negative warped dim. Returning original.")
            return cv_image_bgr.copy()
        dst_rect = np.array([[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]], dtype="float32")
        M = cv2.getPerspectiveTransform(ordered_rect_points, dst_rect)
        warped = cv2.warpPerspective(cv_image_bgr, M, (maxWidth, maxHeight)) 
        if warped.size == 0:
            print("Auto-Crop (Color BG): Warped image empty. Returning original.")
            return cv_image_bgr.copy()
        print(f"Auto-Crop (Color BG): Perspective transform applied. Warped size: ({maxWidth}, {maxHeight})")
        h_warped, w_warped = warped.shape[:2]
        x1 = inward_offset_pixels; y1 = inward_offset_pixels
        x2 = w_warped - inward_offset_pixels; y2 = h_warped - inward_offset_pixels
        x1 = max(0, x1); y1 = max(0, y1)
        x2 = min(w_warped, x2); y2 = min(h_warped, y2) 
        if x1 >= x2 or y1 >= y2:
            print("Auto-Crop (Color BG): Inward offset invalid. Returning warped (no offset).")
            return warped 
        final_cropped_image = warped[y1:y2, x1:x2].copy()
        if final_cropped_image.size == 0:
            print("Auto-Crop (Color BG): Final cropped empty. Returning original.")
            return cv_image_bgr.copy()
        print(f"Auto-Crop (Color BG): Successfully cropped.")
        return final_cropped_image

    def rotate_image_cv(self, cv_image, angle_degrees):
        height, width = cv_image.shape[:2]
        if height == 0 or width == 0: return cv_image 
        center = (width // 2, height // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, -angle_degrees, 1.0) 
        abs_cos = abs(rotation_matrix[0, 0]); abs_sin = abs(rotation_matrix[0, 1])
        new_width = int(height * abs_sin + width * abs_cos)
        new_height = int(height * abs_cos + width * abs_sin)
        rotation_matrix[0, 2] += (new_width / 2) - center[0]
        rotation_matrix[1, 2] += (new_height / 2) - center[1]
        return cv2.warpAffine(cv_image, rotation_matrix, (new_width, new_height))

    def adjust_clahe_cv(self, cv_image_bgr, clip_limit=2.0, tile_grid_size=(8, 8)):
        if cv_image_bgr.size == 0: return cv_image_bgr
        lab = cv2.cvtColor(cv_image_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    def reduce_noise_bilateral_cv(self, cv_image, d=9, sigma_color=75, sigma_space=75):
        if cv_image.size == 0: return cv_image
        return cv2.bilateralFilter(cv_image, d, sigma_color, sigma_space)

    def sharpen_unsharp_mask_cv(self, cv_image, sigma=1.0, strength=1.5):
        if cv_image.size == 0: return cv_image
        blurred = cv2.GaussianBlur(cv_image, (0, 0), sigma) 
        sharpened = cv2.addWeighted(cv_image, 1.0 + strength, blurred, -strength, 0)
        return sharpened

    def process_image(self, pil_input_image, settings_dict, base_image_for_processing=None):
        if pil_input_image is None and base_image_for_processing is None:
            print("Error: No input or base image provided to process_image.")
            return None

        original_exif = None
        cv_image_to_process = None

        if base_image_for_processing:
            print("Processing based on provided base image.")
            pil_current_base = base_image_for_processing.copy()
            if "exif" in pil_current_base.info: # If base image has EXIF, try to preserve it
                original_exif = pil_current_base.info["exif"]
            cv_image_to_process = self._pil_to_cv(pil_current_base)
        else:
            pil_oriented_image = self.auto_orient_pil(pil_input_image) if settings_dict.get("auto_orient", True) else pil_input_image.copy()
            if "exif" in pil_oriented_image.info: # Get EXIF after orientation
                original_exif = pil_oriented_image.info["exif"]
            
            cv_image_initial = self._pil_to_cv(pil_oriented_image)
            if cv_image_initial.size == 0:
                print("Error: Initial OpenCV image is empty. Returning oriented PIL image.")
                return pil_oriented_image

            crop_mode = settings_dict.get("crop_mode", "none") 
            cv_image_after_crop = cv_image_initial.copy() 

            if crop_mode == "percent":
                crop_settings_pct = settings_dict.get("crop_percent")
                if crop_settings_pct:
                    cv_image_after_crop = self.crop_image_cv_percent(
                        cv_image_initial.copy(), 
                        crop_settings_pct.get("top", self.app_config.get_setting('default_crop_top',0) if self.app_config else 0),
                        crop_settings_pct.get("right", self.app_config.get_setting('default_crop_right',0) if self.app_config else 0),
                        crop_settings_pct.get("bottom", self.app_config.get_setting('default_crop_bottom',0) if self.app_config else 0),
                        crop_settings_pct.get("left", self.app_config.get_setting('default_crop_left',0) if self.app_config else 0)
                    )
            elif crop_mode == "manual_scaled_coords": 
                manual_crop_box = settings_dict.get("manual_crop_box_scaled") 
                if manual_crop_box:
                    cv_image_after_crop = self.crop_image_manual_cv(cv_image_initial.copy(), manual_crop_box)
            elif crop_mode == "auto_color_bg":
                hsv_lower = settings_dict.get('hsv_lower_ui', self.app_config.get_setting('pale_blue_hsv_lower', [90, 40, 100]))
                hsv_upper = settings_dict.get('hsv_upper_ui', self.app_config.get_setting('pale_blue_hsv_upper', [130, 255, 255]))
                inward_offset = settings_dict.get("auto_crop_inward_offset", self.app_config.get_setting('auto_crop_inward_offset', 5))
                cv_image_after_crop = self.auto_crop_on_color_background(
                    cv_image_initial.copy(), hsv_lower, hsv_upper, inward_offset_pixels=inward_offset
                )
            
            cv_image_to_process = cv_image_after_crop.copy()
            if cv_image_to_process.size == 0:
                print("Warning: Image empty after UI-selected crop. Reverting to pre-crop for further ops.")
                cv_image_to_process = cv_image_initial.copy()
        
        current_processed_state_cv = cv_image_to_process

        rotation_angle = settings_dict.get("rotation")
        if rotation_angle is not None and rotation_angle != 0: 
            current_processed_state_cv = self.rotate_image_cv(current_processed_state_cv, rotation_angle)
        
        if settings_dict.get("use_bilateral", True): 
            d = int(settings_dict.get("bilateral_d", self.app_config.get_setting('bilateral_d',9) if self.app_config else 9))
            sc = int(settings_dict.get("bilateral_sigma_color", self.app_config.get_setting('bilateral_sigma_color',75) if self.app_config else 75))
            ss = int(settings_dict.get("bilateral_sigma_space", self.app_config.get_setting('bilateral_sigma_space',75) if self.app_config else 75))
            current_processed_state_cv = self.reduce_noise_bilateral_cv(current_processed_state_cv, d, sc, ss)
        
        if settings_dict.get("use_clahe", True): 
            clip = float(settings_dict.get("clahe_clip_limit", self.app_config.get_setting('clahe_clip_limit',2.0) if self.app_config else 2.0))
            grid_size_val = int(settings_dict.get("clahe_tile_grid_size", self.app_config.get_setting('clahe_tile_grid_size',8) if self.app_config else 8))
            grid_size = (grid_size_val, grid_size_val)
            current_processed_state_cv = self.adjust_clahe_cv(current_processed_state_cv, clip_limit=clip, tile_grid_size=grid_size)
        
        if settings_dict.get("use_sharpen", True): 
            sigma = float(settings_dict.get("unsharp_sigma", self.app_config.get_setting('unsharp_sigma',1.0) if self.app_config else 1.0))
            strength = float(settings_dict.get("unsharp_strength", self.app_config.get_setting('unsharp_strength',1.5) if self.app_config else 1.5))
            current_processed_state_cv = self.sharpen_unsharp_mask_cv(current_processed_state_cv, sigma=sigma, strength=strength)
        
        if current_processed_state_cv.size == 0:
            print("Error: Final processed OpenCV image is empty. Returning original PIL image if available.")
            if base_image_for_processing: return base_image_for_processing
            return pil_input_image.copy() if pil_input_image else None

        pil_processed_image = self._cv_to_pil(current_processed_state_cv)
        
        # Re-attach original EXIF data if it exists
        if original_exif:
            pil_processed_image.info["exif"] = original_exif
            print("Original EXIF data re-attached to processed PIL image.")
        elif "exif" in pil_processed_image.info: # Clear any potentially stale EXIF if original was missing
            del pil_processed_image.info["exif"]


        return pil_processed_image

    def save_image_pil(self, pil_image, path, quality=90):
        if pil_image is None:
            print(f"Error: Attempted to save a None image to {path}")
            return
        try:
            save_image = pil_image
            if pil_image.mode not in ['RGB', 'L']:
                print(f"Converting image from mode {pil_image.mode} to RGB for saving.")
                save_image = pil_image.convert('RGB')
            
            exif_data_to_save = save_image.info.get('exif')
            if exif_data_to_save:
                save_image.save(path, quality=quality, icc_profile=save_image.info.get('icc_profile'), exif=exif_data_to_save)
                print(f"Image saved to {path} with EXIF data.")
            else:
                save_image.save(path, quality=quality, icc_profile=save_image.info.get('icc_profile'))
                print(f"Image saved to {path} (no EXIF data found to save).")

        except Exception as e:
            print(f"Error saving image to {path}: {e}")
            # ... (existing fallback save logic) ...
            try: 
                print("Fallback: Attempting to save without ICC profile or EXIF.")
                save_image.save(path, quality=quality)
                print(f"Image saved to {path} (fallback save).")
            except Exception as e2:
                 print(f"Still failed to save image to {path}: {e2}")
                 try:
                     png_path = os.path.splitext(path)[0] + ".png"
                     print(f"Ultimate Fallback: Attempting to save as PNG to {png_path}")
                     save_image.save(png_path) # PNG save handles EXIF differently or might strip it
                     print(f"Image saved as PNG to {png_path}")
                 except Exception as e3:
                     print(f"Failed to save as PNG: {e3}")
