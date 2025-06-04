# BU
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from PIL import Image, ImageTk
import shutil 
import tkinter.simpledialog 
import piexif 
import piexif.helper 
import numpy as np 

from image_processor import ImageProcessor
from file_utils import ensure_directory_exists, create_dot_nomedia

class ProcessTab(ttk.Frame):
    def __init__(self, parent_notebook, app_config):
        super().__init__(parent_notebook)
        self.app_config = app_config
        self.image_processor = ImageProcessor(self.app_config)
        self.imported_events_root_abs = self.app_config.get_path('imported_events_path')
        self.final_photos_root_abs = self.app_config.get_path('final_photos_path')

        self.current_event_name_str = None
        self.current_event_path_abs = None
        self.current_photo_list = []
        self.current_photo_index = -1
        self.original_image_pil = None 
        self.original_image_tk_canvas_ref = None 
        self.processed_image_tk = None 
        self.current_processed_preview_pil = None 

        self.manual_crop_active = False
        self.crop_rect_start_x = None 
        self.crop_rect_start_y = None 
        self.current_crop_rect_id = None 
        self.manual_crop_coords_display = None 
        self.display_to_original_scale_x = 1.0 
        self.display_to_original_scale_y = 1.0 

        # --- Define default HSV values used for UI and alternative ranges ---
        self.hsv_default_lower_fallback = [90, 40, 100]
        self.hsv_default_upper_fallback = [130, 255, 255]

        config_hsv_lower = self.app_config.get_setting('pale_blue_hsv_lower', self.hsv_default_lower_fallback)
        config_hsv_upper = self.app_config.get_setting('pale_blue_hsv_upper', self.hsv_default_upper_fallback)
        
        if not isinstance(config_hsv_lower, list) or len(config_hsv_lower) != 3:
            config_hsv_lower = list(self.hsv_default_lower_fallback) # Use a copy
        if not isinstance(config_hsv_upper, list) or len(config_hsv_upper) != 3:
            config_hsv_upper = list(self.hsv_default_upper_fallback) # Use a copy

        self.alternative_hsv_ranges = [
            {'name': 'From Config/Defaults', 'lower': list(config_hsv_lower), 'upper': list(config_hsv_upper)}, 
            {'name': 'Wider Saturation', 'lower': [90, 20, 90], 'upper': [135, 255, 255]}, 
            {'name': 'Narrower Saturation', 'lower': [90, 60, 110], 'upper': [130, 230, 255]}, 
            {'name': 'Higher Value Min', 'lower': [90, 40, 130], 'upper': [130, 255, 255]},
            {'name': 'Lower Value Min', 'lower': [90, 40, 70], 'upper': [130, 255, 255]},
            {'name': 'Slightly Wider Hue', 'lower': [85, 40, 100], 'upper': [135, 255, 255]},
            {'name': 'Even Wider Saturation', 'lower': [90, 10, 80], 'upper': [130, 255, 255]},
            {'name': 'Brighter Overall (Higher V_min)', 'lower': [85, 30, 150], 'upper': [135, 255, 255]},
            {'name': 'Darker Overall (Lower V_max, if needed)', 'lower': [90, 40, 100], 'upper': [130, 255, 200]},
        ]

        # --- UI Layout ---
        top_controls_frame = ttk.Frame(self)
        top_controls_frame.pack(fill=tk.X, padx=5, pady=5)
        event_selection_frame = ttk.LabelFrame(top_controls_frame, text="Event")
        event_selection_frame.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        ttk.Label(event_selection_frame, text="Select Imported Event:").pack(side=tk.LEFT, padx=5)
        self.event_var = tk.StringVar()
        self.event_dropdown = ttk.Combobox(event_selection_frame, textvariable=self.event_var, state="readonly", width=30)
        self.event_dropdown.pack(side=tk.LEFT, padx=5)
        self.event_dropdown.bind("<<ComboboxSelected>>", self.on_event_selected) 
        ttk.Button(event_selection_frame, text="Refresh List", command=self.populate_event_dropdown).pack(side=tk.LEFT, padx=5)

        main_process_frame = ttk.Frame(self)
        main_process_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        controls_panel = ttk.Frame(main_process_frame, width=300) 
        controls_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0,10), pady=5)
        controls_panel.pack_propagate(False) 
        image_display_pane = ttk.PanedWindow(main_process_frame, orient=tk.HORIZONTAL)
        image_display_pane.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, pady=5)
        
        original_display_container = ttk.Frame(image_display_pane)
        original_frame = ttk.LabelFrame(original_display_container, text="Original (Click Enlarge, Drag for Manual Crop)")
        self.original_canvas = tk.Canvas(original_frame, bg="lightgrey", relief="groove", bd=2)
        self.original_canvas.pack(fill=tk.BOTH, expand=True)
        
        self.original_canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.original_canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.original_canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.original_canvas.bind("<Button-3>", self.enlarge_original_image)

        original_frame.pack(fill=tk.BOTH, expand=True)
        self.original_exif_button = ttk.Button(original_display_container, text="EXIF", command=self.show_original_exif_data, state=tk.DISABLED)
        self.original_exif_button.pack(pady=2)
        image_display_pane.add(original_display_container, weight=1)

        processed_display_container = ttk.Frame(image_display_pane)
        processed_frame = ttk.LabelFrame(processed_display_container, text="Processed Preview (Click to Enlarge)")
        self.processed_image_label = ttk.Label(processed_frame, text="Processed Preview", anchor="center", relief="groove")
        self.processed_image_label.pack(fill=tk.BOTH, expand=True)
        self.processed_image_label.bind("<Button-1>", self.enlarge_processed_image)
            
        processed_frame.pack(fill=tk.BOTH, expand=True)
        self.processed_exif_button = ttk.Button(processed_display_container, text="EXIF", command=self.show_processed_exif_data, state=tk.DISABLED)
        self.processed_exif_button.pack(pady=2)
        image_display_pane.add(processed_display_container, weight=1)

        # --- Processing Controls in `controls_panel` ---
        self.auto_orient_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls_panel, text="Auto-Orient (from EXIF)", variable=self.auto_orient_var).pack(anchor="w", pady=2)
        
        crop_mode_frame = ttk.LabelFrame(controls_panel, text="Cropping Mode")
        crop_mode_frame.pack(fill=tk.X, pady=5)
        self.crop_mode_var = tk.StringVar(value="auto_color_bg") 
        
        ttk.Radiobutton(crop_mode_frame, text="Auto-Crop (Blue BG)", variable=self.crop_mode_var, value="auto_color_bg", command=self.on_crop_mode_changed).pack(anchor="w")
        self.auto_crop_params_frame = ttk.Frame(crop_mode_frame)
        hsv_lower_frame = ttk.Frame(self.auto_crop_params_frame)
        ttk.Label(hsv_lower_frame, text="HSV Lower (H,S,V):").pack(side=tk.LEFT, padx=(20,2))
        self.hsv_lower_vars = [tk.IntVar(), tk.IntVar(), tk.IntVar()]
        for i, var in enumerate(self.hsv_lower_vars):
            var.set(config_hsv_lower[i])
            ttk.Entry(hsv_lower_frame, textvariable=var, width=4).pack(side=tk.LEFT, padx=1)
        hsv_lower_frame.pack(fill=tk.X)
        hsv_upper_frame = ttk.Frame(self.auto_crop_params_frame)
        ttk.Label(hsv_upper_frame, text="HSV Upper (H,S,V):").pack(side=tk.LEFT, padx=(20,2))
        self.hsv_upper_vars = [tk.IntVar(), tk.IntVar(), tk.IntVar()]
        for i, var in enumerate(self.hsv_upper_vars):
            var.set(config_hsv_upper[i])
            ttk.Entry(hsv_upper_frame, textvariable=var, width=4).pack(side=tk.LEFT, padx=1)
        hsv_upper_frame.pack(fill=tk.X)
        inward_offset_sub_frame = ttk.Frame(self.auto_crop_params_frame) 
        ttk.Label(inward_offset_sub_frame, text="Inward Offset (px):").pack(side=tk.LEFT, padx=(20,0))
        self.auto_crop_inward_offset_var = tk.IntVar(value=self.app_config.get_setting('auto_crop_inward_offset', 5)) 
        ttk.Entry(inward_offset_sub_frame, textvariable=self.auto_crop_inward_offset_var, width=4).pack(side=tk.LEFT)
        inward_offset_sub_frame.pack(fill=tk.X)
        
        self.find_hsv_button = ttk.Button(self.auto_crop_params_frame, text="Find Optimal HSV", command=self.find_optimal_hsv_for_autocrop)
        self.find_hsv_button.pack(pady=5, padx=20, fill=tk.X)


        # Percentage Crop Radiobutton and Frame RE-ADDED
        ttk.Radiobutton(crop_mode_frame, text="Percentage", variable=self.crop_mode_var, value="percent", command=self.on_crop_mode_changed).pack(anchor="w")
        self.crop_percent_frame = ttk.Frame(crop_mode_frame) 
        self.crop_vars = {}
        for i, side in enumerate(["Top", "Right", "Bottom", "Left"]):
            ttk.Label(self.crop_percent_frame, text=f"{side}:").grid(row=i, column=0, sticky="w", padx=(20,0)) 
            var = tk.DoubleVar(value=self.app_config.get_setting(f'default_crop_{side.lower()}', 2.0))
            ttk.Entry(self.crop_percent_frame, textvariable=var, width=5).grid(row=i, column=1)
            self.crop_vars[side.lower()] = var
        
        ttk.Radiobutton(crop_mode_frame, text="Manual Draw (on Original)", variable=self.crop_mode_var, value="manual", command=self.on_crop_mode_changed).pack(anchor="w")
        self.on_crop_mode_changed() 

        rotation_frame = ttk.LabelFrame(controls_panel, text="Rotation (CCW Deg)")
        rotation_frame.pack(fill=tk.X, pady=5)
        self.rotation_var = tk.DoubleVar(value=0.0)
        ttk.Scale(rotation_frame, from_=-45, to=45, orient=tk.HORIZONTAL, variable=self.rotation_var, length=180).pack(fill=tk.X, padx=5)
        rotation_buttons_frame = ttk.Frame(rotation_frame)
        rotation_buttons_frame.pack(fill=tk.X, pady=2)
        ttk.Button(rotation_buttons_frame, text="-90°", command=lambda: self.adjust_rotation(-90)).pack(side=tk.LEFT, padx=2)
        ttk.Entry(rotation_buttons_frame, textvariable=self.rotation_var, width=5, justify='center').pack(side=tk.LEFT, padx=2)
        ttk.Button(rotation_buttons_frame, text="+90°", command=lambda: self.adjust_rotation(90)).pack(side=tk.LEFT, padx=2)
        ttk.Button(rotation_buttons_frame, text="180°", command=lambda: self.adjust_rotation(180)).pack(side=tk.LEFT, padx=2)
        ttk.Button(rotation_buttons_frame, text="Reset", command=self.reset_rotation).pack(side=tk.LEFT, padx=2)

        enhancement_frame = ttk.LabelFrame(controls_panel, text="OpenCV Enhancements")
        enhancement_frame.pack(fill=tk.X, pady=5)
        self.use_clahe_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(enhancement_frame, text="Use CLAHE (Contrast)", variable=self.use_clahe_var).pack(anchor="w")
        self.use_bilateral_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(enhancement_frame, text="Use Bilateral Filter (Smooth)", variable=self.use_bilateral_var).pack(anchor="w")
        self.use_sharpen_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(enhancement_frame, text="Use Unsharp Mask (Sharpen)", variable=self.use_sharpen_var).pack(anchor="w")

        action_buttons_frame = ttk.Frame(self)
        action_buttons_frame.pack(fill=tk.X, pady=10)
        self.preview_button = ttk.Button(action_buttons_frame, text="Preview Changes", command=self.preview_current_photo_processing)
        self.preview_button.pack(side=tk.LEFT, padx=10)
        self.save_processed_button = ttk.Button(action_buttons_frame, text="Save Processed Photo", command=self.save_current_processed_photo)
        self.save_processed_button.pack(side=tk.LEFT, padx=10)
        self.process_all_button = ttk.Button(action_buttons_frame, text="Process All in Event", command=self.process_all_photos_in_event)
        self.process_all_button.pack(side=tk.LEFT, padx=10)
        self.finalize_event_button = ttk.Button(action_buttons_frame, text="Move Processed to Final", command=self.finalize_event)
        self.finalize_event_button.pack(side=tk.RIGHT, padx=10)

        navigation_frame = ttk.Frame(self)
        navigation_frame.pack(fill=tk.X, pady=5, before=action_buttons_frame)
        
        self.prev_button = ttk.Button(navigation_frame, text="<< Previous", command=self.prev_photo, state=tk.DISABLED)
        self.prev_button.pack(side=tk.LEFT, padx=10)
        
        self.photo_info_label = ttk.Label(navigation_frame, text="Photo X of Y")
        self.photo_info_label.pack(side=tk.LEFT, expand=True, fill=tk.X, anchor="center")
        
        self.next_button = ttk.Button(navigation_frame, text="Next >>", command=self.next_photo, state=tk.DISABLED)
        self.next_button.pack(side=tk.RIGHT, padx=10)

        self.populate_event_dropdown()

    def _method_missing_dummy(self, method_name):
        """Dummy command to use if a method is missing, to prevent startup crash."""
        def dummy_command():
            print(f"ERROR: Method ProcessTab.{method_name} is not defined!")
            messagebox.showerror("Internal Error", f"Functionality for '{method_name}' is missing.", parent=self)
        return dummy_command

    def adjust_rotation(self, angle_change):
        current_angle = self.rotation_var.get()
        new_angle = current_angle + angle_change
        while new_angle > 180: new_angle -= 360
        while new_angle <= -180: new_angle += 360 
        self.rotation_var.set(new_angle)

    def reset_rotation(self):
        self.rotation_var.set(0.0)

    def on_crop_mode_changed(self):
        mode = self.crop_mode_var.get()
        if mode == "percent":
            self.auto_crop_params_frame.pack_forget() 
            self.crop_percent_frame.pack(fill=tk.X, padx=(20,0)) 
        elif mode == "auto_color_bg":
            self.crop_percent_frame.pack_forget()
            self.auto_crop_params_frame.pack(fill=tk.X, padx=(0,0)) 
        else: # "manual" 
            self.crop_percent_frame.pack_forget()
            self.auto_crop_params_frame.pack_forget()

        if self.manual_crop_active and mode != "manual":
            self.clear_crop_rect() 
            self.manual_crop_active = False
        
    def get_current_processing_settings(self):
        settings = {
            "auto_orient": self.auto_orient_var.get(),
            "crop_mode": self.crop_mode_var.get(), 
            "rotation": self.rotation_var.get(),
            "use_clahe": self.use_clahe_var.get(),
            "use_bilateral": self.use_bilateral_var.get(),
            "use_sharpen": self.use_sharpen_var.get(),
        }
        current_crop_mode_ui = settings["crop_mode"]
        if current_crop_mode_ui == "percent": 
            settings["crop_percent"] = {side: var.get() for side, var in self.crop_vars.items()}
        elif current_crop_mode_ui == "manual" and self.manual_crop_coords_display:
            disp_x1, disp_y1, disp_x2, disp_y2 = self.manual_crop_coords_display
            scaled_x1 = disp_x1 * self.display_to_original_scale_x
            scaled_y1 = disp_y1 * self.display_to_original_scale_y
            scaled_x2 = disp_x2 * self.display_to_original_scale_x
            scaled_y2 = disp_y2 * self.display_to_original_scale_y
            settings["manual_crop_box_scaled"] = (scaled_x1, scaled_y1, scaled_x2, scaled_y2)
            settings["crop_mode"] = "manual_scaled_coords" 
        elif current_crop_mode_ui == "auto_color_bg":
            settings["auto_crop_inward_offset"] = self.auto_crop_inward_offset_var.get()
            try:
                settings["hsv_lower_ui"] = [var.get() for var in self.hsv_lower_vars]
                settings["hsv_upper_ui"] = [var.get() for var in self.hsv_upper_vars]
            except tk.TclError: 
                messagebox.showwarning("Warning", "Could not read HSV values. Using defaults from config.", parent=self)
                settings["hsv_lower_ui"] = self.app_config.get_setting('pale_blue_hsv_lower')
                settings["hsv_upper_ui"] = self.app_config.get_setting('pale_blue_hsv_upper')
        return settings
        
    def _is_crop_effective(self, original_pil, cropped_pil):
        if cropped_pil is None: return False
        if original_pil is None: return True 
        width_diff = abs(original_pil.width - cropped_pil.width)
        height_diff = abs(original_pil.height - cropped_pil.height)
        effective_change_threshold_px = 5 
        effective_change_threshold_ratio = 0.01 
        if width_diff > effective_change_threshold_px or \
           height_diff > effective_change_threshold_px or \
           width_diff > original_pil.width * effective_change_threshold_ratio or \
           height_diff > original_pil.height * effective_change_threshold_ratio:
            original_area = original_pil.width * original_pil.height
            cropped_area = cropped_pil.width * cropped_pil.height
            if cropped_area > 0.05 * original_area : 
                return True
        return False

    def find_optimal_hsv_for_autocrop(self): 
        if not self.original_image_pil:
            messagebox.showwarning("Find HSV", "No original image loaded.", parent=self)
            return

        print("Starting search for optimal HSV for auto-crop (Blue BG)...")
        self.update_idletasks() 
        oriented_pil = self.image_processor.auto_orient_pil(self.original_image_pil.copy()) if self.auto_orient_var.get() else self.original_image_pil.copy()
        cv_oriented = self.image_processor._pil_to_cv(oriented_pil)
        inward_offset = self.auto_crop_inward_offset_var.get()
        initial_hsv_lower = [var.get() for var in self.hsv_lower_vars]
        initial_hsv_upper = [var.get() for var in self.hsv_upper_vars]
        
        all_ranges_to_try = [{'name': 'Current UI', 'lower': initial_hsv_lower, 'upper': initial_hsv_upper}]
        for alt_range in self.alternative_hsv_ranges:
            is_duplicate_of_ui = (alt_range['lower'] == initial_hsv_lower and alt_range['upper'] == initial_hsv_upper)
            is_duplicate_of_first_alternative = False
            if self.alternative_hsv_ranges and alt_range['name'] != self.alternative_hsv_ranges[0]['name']:
                 is_duplicate_of_first_alternative = (
                    self.alternative_hsv_ranges[0]['lower'] == alt_range['lower'] and
                    self.alternative_hsv_ranges[0]['upper'] == alt_range['upper']
                )
            
            if not is_duplicate_of_ui and not (alt_range['name'] != 'From Config/Defaults' and is_duplicate_of_first_alternative and len(all_ranges_to_try) > 0 and all_ranges_to_try[0]['name'] == 'From Config/Defaults'): 
                 all_ranges_to_try.append(alt_range)

        found_effective_hsv = False
        best_hsv_set_found = None

        for i, hsv_set in enumerate(all_ranges_to_try):
            current_hsv_lower = hsv_set['lower']
            current_hsv_upper = hsv_set['upper']
            if not (isinstance(current_hsv_lower, list) and len(current_hsv_lower) == 3 and
                    isinstance(current_hsv_upper, list) and len(current_hsv_upper) == 3 and
                    all(isinstance(x, int) for x in current_hsv_lower) and
                    all(isinstance(x, int) for x in current_hsv_upper)):
                print(f"Skipping invalid HSV set '{hsv_set['name']}': L={current_hsv_lower}, U={current_hsv_upper}")
                continue
            print(f"Trying HSV set '{hsv_set['name']}': L={current_hsv_lower}, U={current_hsv_upper}")
            self.update_idletasks() 
            cropped_cv_attempt = self.image_processor.auto_crop_on_color_background(
                cv_oriented.copy(), current_hsv_lower, current_hsv_upper, inward_offset_pixels=inward_offset)
            cropped_pil_attempt = self.image_processor._cv_to_pil(cropped_cv_attempt) if cropped_cv_attempt.size > 0 else None
            if cropped_pil_attempt and self._is_crop_effective(oriented_pil, cropped_pil_attempt):
                print(f"Effective auto-crop found with HSV set: {hsv_set['name']}")
                for j, var in enumerate(self.hsv_lower_vars): var.set(current_hsv_lower[j])
                for j, var in enumerate(self.hsv_upper_vars): var.set(current_hsv_upper[j])
                best_hsv_set_found = hsv_set 
                found_effective_hsv = True
                break 
            else:
                print(f"HSV set '{hsv_set['name']}' was not effective or failed.")
        if found_effective_hsv:
            messagebox.showinfo("Optimal HSV Found", f"Found effective HSV settings: {best_hsv_set_found['name']}.\nUI updated. Click 'Preview Changes' to apply all settings.", parent=self)
            self.preview_current_photo_processing() 
        else:
            messagebox.showwarning("Optimal HSV Search", "Could not find optimal HSV settings from predefined alternatives. Please adjust manually or check image.", parent=self)

    def populate_event_dropdown(self):
        self.imported_events_root_abs = self.app_config.get_path('imported_events_path')
        if not self.imported_events_root_abs or not os.path.isdir(self.imported_events_root_abs):
            self.event_dropdown['values'] = []
            self.event_var.set("")
            self.clear_photo_display_and_list()
            return
        try:
            events = [d for d in os.listdir(self.imported_events_root_abs)
                      if os.path.isdir(os.path.join(self.imported_events_root_abs, d))]
            self.event_dropdown['values'] = sorted(events)
            current_selection = self.event_var.get()
            if events:
                if current_selection not in events: self.event_var.set(events[0])
            else: self.event_var.set("")
            self.on_event_selected(None) 
        except Exception as e:
            messagebox.showerror("Error", f"Could not list events: {e}", parent=self)

    def on_event_selected(self, event_unused=None): 
        event_name = self.event_var.get()
        self.current_processed_preview_pil = None 

        if not event_name:
            self.clear_photo_display_and_list()
            self.current_event_name_str = None
            self.current_event_path_abs = None
            return

        self.current_event_name_str = event_name
        self.imported_events_root_abs = self.app_config.get_path('imported_events_path') 
        self.current_event_path_abs = os.path.join(self.imported_events_root_abs, event_name)
        
        self.clear_crop_rect() 
        self.load_photo_list_for_event()

        if self.current_photo_list:
            self.current_photo_index = 0
            self.load_and_display_current_photo()
        else:
            self.clear_photo_display_and_list()
        self.update_navigation_buttons_state()

    def on_canvas_press(self, event): 
        if self.crop_mode_var.get() == "manual" and self.original_image_pil and hasattr(self, 'original_image_tk_canvas_ref') and self.original_image_tk_canvas_ref:
            self.manual_crop_active = True
            self.current_processed_preview_pil = None 

            displayed_img_width = self.original_image_tk_canvas_ref.width()
            displayed_img_height = self.original_image_tk_canvas_ref.height()
            canvas_width = self.original_canvas.winfo_width(); canvas_height = self.original_canvas.winfo_height()
            img_offset_x = (canvas_width - displayed_img_width) / 2
            img_offset_y = (canvas_height - displayed_img_height) / 2
            self.crop_rect_start_x = self.original_canvas.canvasx(event.x) - img_offset_x
            self.crop_rect_start_y = self.original_canvas.canvasy(event.y) - img_offset_y
            self.crop_rect_start_x = max(0, min(self.crop_rect_start_x, displayed_img_width))
            self.crop_rect_start_y = max(0, min(self.crop_rect_start_y, displayed_img_height))
            if self.current_crop_rect_id: self.original_canvas.delete(self.current_crop_rect_id)
            self.current_crop_rect_id = self.original_canvas.create_rectangle(
                self.crop_rect_start_x + img_offset_x, self.crop_rect_start_y + img_offset_y,
                self.crop_rect_start_x + img_offset_x, self.crop_rect_start_y + img_offset_y,
                outline="red", width=2, tags="crop_rect")
            self.manual_crop_coords_display = None

    def on_canvas_drag(self, event): 
        if self.manual_crop_active and self.crop_rect_start_x is not None and hasattr(self, 'original_image_tk_canvas_ref') and self.original_image_tk_canvas_ref:
            displayed_img_width = self.original_image_tk_canvas_ref.width()
            displayed_img_height = self.original_image_tk_canvas_ref.height()
            canvas_width = self.original_canvas.winfo_width(); canvas_height = self.original_canvas.winfo_height()
            img_offset_x = (canvas_width - displayed_img_width) / 2
            img_offset_y = (canvas_height - displayed_img_height) / 2
            cur_x_img_relative = self.original_canvas.canvasx(event.x) - img_offset_x
            cur_y_img_relative = self.original_canvas.canvasy(event.y) - img_offset_y
            cur_x_img_relative = max(0, min(cur_x_img_relative, displayed_img_width))
            cur_y_img_relative = max(0, min(cur_y_img_relative, displayed_img_height))
            self.original_canvas.coords(self.current_crop_rect_id,
                                        self.crop_rect_start_x + img_offset_x, self.crop_rect_start_y + img_offset_y,
                                        cur_x_img_relative + img_offset_x, cur_y_img_relative + img_offset_y)

    def on_canvas_release(self, event): 
        if self.manual_crop_active and self.current_crop_rect_id and hasattr(self, 'original_image_tk_canvas_ref') and self.original_image_tk_canvas_ref:
            self.manual_crop_active = False
            canvas_coords = self.original_canvas.coords(self.current_crop_rect_id)
            displayed_img_width = self.original_image_tk_canvas_ref.width()
            displayed_img_height = self.original_image_tk_canvas_ref.height()
            canvas_width = self.original_canvas.winfo_width(); canvas_height = self.original_canvas.winfo_height()
            img_offset_x = (canvas_width - displayed_img_width) / 2
            img_offset_y = (canvas_height - displayed_img_height) / 2
            img_x1 = canvas_coords[0] - img_offset_x; img_y1 = canvas_coords[1] - img_offset_y
            img_x2 = canvas_coords[2] - img_offset_x; img_y2 = canvas_coords[3] - img_offset_y
            img_x1 = max(0, min(img_x1, displayed_img_width)); img_y1 = max(0, min(img_y1, displayed_img_height))
            img_x2 = max(0, min(img_x2, displayed_img_width)); img_y2 = max(0, min(img_y2, displayed_img_height))
            self.manual_crop_coords_display = (min(img_x1,img_x2), min(img_y1,img_y2), max(img_x1,img_x2), max(img_y1,img_y2))
            print(f"Manual crop rect (coords relative to displayed thumb): {self.manual_crop_coords_display}")

    def _show_enlarged_image(self, pil_image_to_show, title="Enlarged Image"): 
        if not pil_image_to_show: return
        top = tk.Toplevel(self)
        top.title(title)
        img_w, img_h = pil_image_to_show.size
        max_screen_w = int(self.winfo_screenwidth() * 0.8); max_screen_h = int(self.winfo_screenheight() * 0.8)
        display_img = pil_image_to_show.copy()
        if img_w > max_screen_w or img_h > max_screen_h:
            display_img.thumbnail((max_screen_w, max_screen_h), Image.Resampling.LANCZOS)
        photo_img = ImageTk.PhotoImage(display_img)
        img_label = ttk.Label(top, image=photo_img)
        img_label.image = photo_img
        img_label.pack(padx=10, pady=10)
        close_button = ttk.Button(top, text="Close", command=top.destroy)
        close_button.pack(pady=5)
        top.grab_set(); top.transient(self.winfo_toplevel())
    
    def enlarge_original_image(self, event=None): 
        if self.original_image_pil:
            base_save_path = None
            title = "Original Image - Enlarged"
            if self.current_photo_list and self.current_photo_index != -1:
                photo_name = self.current_photo_list[self.current_photo_index]
                base_save_path = os.path.join(self.current_event_path_abs, photo_name)
                title = f"Original - {photo_name}"
            self._show_enlarged_image(self.original_image_pil, title, base_path_for_saving=base_save_path)

    def enlarge_processed_image(self, event=None): 
        image_to_show = self.current_processed_preview_pil 
        base_save_path = None
        title_suffix = "Processed Preview"

        if self.current_event_path_abs and self.current_photo_list and self.current_photo_index != -1:
            photo_name = self.current_photo_list[self.current_photo_index]
            # Suggest saving in "Processed" folder for consistency if it's a processed image
            base_save_path = os.path.join(self.current_event_path_abs, "Processed", photo_name)
            title_suffix = f"Processed - {photo_name}"
            
        if image_to_show:
             self._show_enlarged_image(image_to_show, title_suffix, base_path_for_saving=base_save_path)
        elif self.original_image_pil: 
            print("No processed preview to enlarge, attempting to generate one...")
            settings = self.get_current_processing_settings()
            try:
                processed_pil = self.image_processor.process_image(self.original_image_pil, settings)
                if processed_pil:
                    # Store this generated preview so EXIF button can also refer to it if needed
                    self.current_processed_preview_pil = processed_pil 
                    self._show_enlarged_image(processed_pil, title_suffix + " (Generated)", base_path_for_saving=base_save_path)
            except Exception as e: 
                messagebox.showerror("Error", f"Could not generate processed image for enlargement: {e}", parent=self)
        else:
            messagebox.showinfo("Info", "No image to enlarge.", parent=self)
    



    def load_and_display_current_photo(self):
        self.clear_crop_rect() 
        self.current_processed_preview_pil = None 

        if not self.current_photo_list or self.current_photo_index == -1:
            self.clear_photo_display_and_list()
            return
        photo_name = self.current_photo_list[self.current_photo_index]
        original_photo_path = os.path.join(self.current_event_path_abs, photo_name)
        try:
            self.original_image_pil = Image.open(original_photo_path)
            self._display_pil_image_on_canvas(self.original_image_pil, self.original_canvas, "original_image_tk_canvas_ref")
            self.original_exif_button.config(state=tk.NORMAL) 
        except Exception as e:
            self.original_image_pil = None
            self._display_pil_image_on_canvas(None, self.original_canvas, "original_image_tk_canvas_ref")
            self.original_exif_button.config(state=tk.DISABLED)
            messagebox.showerror("Error", f"Could not load original image {photo_name}: {e}", parent=self)

        processed_dir = os.path.join(self.current_event_path_abs, "Processed")
        processed_photo_path = os.path.join(processed_dir, photo_name)
        self.processed_exif_button.config(state=tk.DISABLED) 
        if os.path.exists(processed_photo_path):
            try:
                processed_pil = Image.open(processed_photo_path)
                self.current_processed_preview_pil = processed_pil 
                self._display_pil_image_on_label(processed_pil, self.processed_image_label, "processed_image_tk")
                self.processed_exif_button.config(state=tk.NORMAL) 
            except Exception as e:
                self._display_pil_image_on_label(None, self.processed_image_label, "processed_image_tk")
                print(f"Error loading processed version of {photo_name}: {e}")
        else:
            self._display_pil_image_on_label(None, self.processed_image_label, "processed_image_tk")
        self.photo_info_label.config(text=f"{photo_name} ({self.current_photo_index + 1} of {len(self.current_photo_list)})")
        self.update_navigation_buttons_state()

    def clear_photo_display_and_list(self):
        self.current_photo_list = []; self.current_photo_index = -1
        self.original_image_pil = None
        self._display_pil_image_on_canvas(None, self.original_canvas, "original_image_tk_canvas_ref")
        self._display_pil_image_on_label(None, self.processed_image_label, "processed_image_tk")
        self.current_processed_preview_pil = None
        self.photo_info_label.config(text="Photo X of Y")
        self.original_exif_button.config(state=tk.DISABLED)
        self.processed_exif_button.config(state=tk.DISABLED)
        self.clear_crop_rect()
        self.update_navigation_buttons_state()

    def update_navigation_buttons_state(self):
        has_photos = bool(self.current_photo_list)
        self.prev_button.config(state=tk.NORMAL if has_photos and self.current_photo_index > 0 else tk.DISABLED)
        self.next_button.config(state=tk.NORMAL if has_photos and self.current_photo_index < len(self.current_photo_list) - 1 else tk.DISABLED)
        action_button_state = tk.NORMAL if self.original_image_pil else tk.DISABLED
        self.preview_button.config(state=action_button_state)
        self.save_processed_button.config(state=action_button_state)
        self.original_exif_button.config(state=action_button_state)
        self.processed_exif_button.config(state=tk.NORMAL if self.current_processed_preview_pil else tk.DISABLED)
        self.process_all_button.config(state=tk.NORMAL if has_photos else tk.DISABLED)
        self.finalize_event_button.config(state=tk.NORMAL if has_photos else tk.DISABLED)

    def next_photo(self): 
        if self.current_photo_index < len(self.current_photo_list) - 1:
            self.current_photo_index += 1
            self.load_and_display_current_photo()
        self.update_navigation_buttons_state()

    def prev_photo(self): 
        if self.current_photo_index > 0:
            self.current_photo_index -= 1
            self.load_and_display_current_photo()
        self.update_navigation_buttons_state()

    def preview_current_photo_processing(self):
        if not self.original_image_pil:
            messagebox.showwarning("Preview", "No original image loaded.", parent=self)
            return
        settings = self.get_current_processing_settings()
        print(f"Previewing with settings: {settings}")
        try:
            processed_pil = self.image_processor.process_image(self.original_image_pil, settings, base_image_for_processing=None)
            self.current_processed_preview_pil = processed_pil 
            self._display_pil_image_on_label(processed_pil, self.processed_image_label, "processed_image_tk")
            self.processed_exif_button.config(state=tk.NORMAL if processed_pil else tk.DISABLED)
        except Exception as e:
            messagebox.showerror("Processing Error", f"Could not preview changes: {e}", parent=self)
            print(f"Preview error details: {e}", exc_info=True)
            self.current_processed_preview_pil = None
            self._display_pil_image_on_label(None, self.processed_image_label, "processed_image_tk")
            self.processed_exif_button.config(state=tk.DISABLED)

    def save_current_processed_photo(self):
        image_to_save = self.current_processed_preview_pil
        settings_for_reprocess = self.get_current_processing_settings()
        if not image_to_save: 
            if not self.original_image_pil:
                messagebox.showerror("Error", "No original image loaded to process and save.", parent=self)
                return
            print("No current preview to save, re-processing with current settings...")
            try:
                image_to_save = self.image_processor.process_image(self.original_image_pil, settings_for_reprocess, base_image_for_processing=None)
            except Exception as e:
                messagebox.showerror("Processing Error", f"Could not process image for saving: {e}", parent=self)
                return
        if not image_to_save: 
            messagebox.showerror("Error", "Failed to generate image for saving.", parent=self)
            return
        if not self.current_event_path_abs or self.current_photo_index == -1:
            messagebox.showerror("Error", "No photo selected or event loaded for saving.", parent=self)
            return
        photo_name = self.current_photo_list[self.current_photo_index]
        processed_dir = ensure_directory_exists(os.path.join(self.current_event_path_abs, "Processed"))
        create_dot_nomedia(processed_dir)
        processed_photo_path = os.path.join(processed_dir, photo_name)
        try:
            self.image_processor.save_image_pil(image_to_save, processed_photo_path)
            messagebox.showinfo("Saved", f"Processed photo saved to:\n{processed_photo_path}", parent=self)
            self._display_pil_image_on_label(image_to_save, self.processed_image_label, "processed_image_tk")
            self.processed_exif_button.config(state=tk.NORMAL if image_to_save else tk.DISABLED)
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save processed photo: {e}", parent=self)
            print(f"Save error details: {e}", exc_info=True)

    def process_all_photos_in_event(self):
        if not self.current_event_path_abs or not self.current_photo_list:
            messagebox.showerror("Error", "No event or photos loaded.", parent=self)
            return
        if not messagebox.askyesno("Confirm", "Process all photos in event with current settings? This may overwrite.", parent=self):
            return
        settings_for_batch = self.get_current_processing_settings() 
        if settings_for_batch.get("crop_mode") == "manual_scaled_coords":
             print("Warning: 'Manual Draw' crop selected for batch. This will result in NO CROP for batch items.")
             settings_for_batch["crop_mode"] = "none" 
        processed_dir = ensure_directory_exists(os.path.join(self.current_event_path_abs, "Processed"))
        create_dot_nomedia(processed_dir)
        success_count, fail_count = 0, 0
        for i, photo_name in enumerate(self.current_photo_list):
            self.photo_info_label.config(text=f"Processing: {photo_name} ({i+1}/{len(self.current_photo_list)})")
            self.update_idletasks()
            original_photo_path = os.path.join(self.current_event_path_abs, photo_name)
            target_processed_path = os.path.join(processed_dir, photo_name)
            try:
                with Image.open(original_photo_path) as img_pil_current_in_batch:
                    processed_pil = self.image_processor.process_image(img_pil_current_in_batch, settings_for_batch, base_image_for_processing=None)
                    if processed_pil:
                        self.image_processor.save_image_pil(processed_pil, target_processed_path)
                        success_count +=1
                    else:
                        print(f"Processing {photo_name} resulted in None.")
                        fail_count += 1
            except Exception as e:
                print(f"Error processing {photo_name}: {e}", exc_info=True)
                fail_count += 1
        messagebox.showinfo("Batch Process", f"Processed {success_count} photos.\nFailed for {fail_count} photos.", parent=self)
        self.load_and_display_current_photo() 

    def finalize_event(self):
        if not self.current_event_path_abs:
            messagebox.showerror("Error", "No event selected.", parent=self)
            return
        event_name = self.current_event_name_str
        source_processed_dir = os.path.join(self.current_event_path_abs, "Processed")
        if not os.path.isdir(source_processed_dir) or not any(f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) for f in os.listdir(source_processed_dir)):
            messagebox.showinfo("Info", "No processed photos found for this event to move to Final.", parent=self)
            return
        target_final_event_dir = ensure_directory_exists(os.path.join(self.final_photos_root_abs, event_name))
        create_dot_nomedia(target_final_event_dir)
        if os.path.exists(target_final_event_dir) and any(f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) for f in os.listdir(target_final_event_dir)):
             if not messagebox.askyesno("Confirm", f"Event '{event_name}' already exists in FinalPhotos and is not empty. Overwrite files?", parent=self):
                return
        try:
            copied_count = 0
            for item_name in os.listdir(source_processed_dir):
                s_item = os.path.join(source_processed_dir, item_name)
                d_item = os.path.join(target_final_event_dir, item_name)
                if os.path.isfile(s_item) and s_item.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')): 
                    shutil.copy2(s_item, d_item)
                    copied_count +=1
            messagebox.showinfo("Finalized", f"{copied_count} processed photos for event '{event_name}' moved to FinalPhotos.", parent=self)
        except Exception as e: messagebox.showerror("Finalize Error", f"Could not move event to FinalPhotos: {e}", parent=self)

    def _format_exif_data(self, exif_dict):
        if not exif_dict: return "No EXIF data found."
        output_lines = []
        for ifd_name, ifd_data in exif_dict.items():
            if ifd_name == "thumbnail":
                output_lines.append(f"Thumbnail: {'Present' if ifd_data else 'None'}")
                continue
            output_lines.append(f"\n--- {ifd_name} ---")
            if not isinstance(ifd_data, dict):
                output_lines.append(f"  Invalid IFD data for {ifd_name}")
                continue
            for tag_id, value in ifd_data.items():
                tag_info = piexif.TAGS.get(ifd_name, {}).get(tag_id)
                tag_name = tag_info["name"] if tag_info else f"UnknownTag_{tag_id}"
                decoded_value = value
                if isinstance(value, bytes):
                    if tag_name == "UserComment" and ifd_name == "Exif":
                        try: decoded_value = piexif.helper.load_comment(value)
                        except: decoded_value = str(value)
                    else:
                        try: decoded_value = value.decode('utf-8', errors='replace').rstrip('\x00')
                        except: decoded_value = str(value)
                elif isinstance(value, tuple) and len(value) > 10: 
                    decoded_value = f"{str(value)[:80]}..."
                else: decoded_value = str(value)
                if len(str(decoded_value)) > 150: decoded_value = str(decoded_value)[:150] + "..." 
                output_lines.append(f"  {tag_name} (0x{tag_id:04x}): {decoded_value}")
        return "\n".join(output_lines)

    def _show_exif_window(self, photo_path, title):
        if not photo_path or not os.path.exists(photo_path):
            messagebox.showwarning("EXIF Info", "Photo path invalid or file does not exist.", parent=self)
            return
        try:
            exif_dict = piexif.load(photo_path)
            exif_str = self._format_exif_data(exif_dict)
        except piexif.InvalidImageDataError: exif_str = "Not a valid image or no EXIF data."
        except Exception as e: exif_str = f"Error reading EXIF: {e}"
        exif_window = tk.Toplevel(self); exif_window.title(title); exif_window.geometry("600x450")
        exif_window.transient(self.winfo_toplevel()); exif_window.grab_set()
        text_area = tk.Text(exif_window, wrap=tk.WORD, padx=5, pady=5, font=("Menlo", 10) if os.name == 'posix' else ("Consolas", 10))
        scrollbar = ttk.Scrollbar(exif_window, command=text_area.yview)
        text_area.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y); text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_area.insert(tk.END, exif_str); text_area.configure(state='disabled')
        ttk.Button(exif_window, text="Close", command=exif_window.destroy).pack(pady=5)

    def show_original_exif_data(self):
        if not self.original_image_pil or not self.current_event_path_abs or self.current_photo_index == -1:
            messagebox.showinfo("EXIF Info", "No original photo loaded.", parent=self)
            return
        photo_name = self.current_photo_list[self.current_photo_index]
        original_photo_path = os.path.join(self.current_event_path_abs, photo_name)
        self._show_exif_window(original_photo_path, f"EXIF - Original: {photo_name}")

    def show_processed_exif_data(self):
        if not self.current_event_path_abs or self.current_photo_index == -1:
            messagebox.showinfo("EXIF Info", "No photo selected.", parent=self)
            return
        photo_name = self.current_photo_list[self.current_photo_index]
        processed_photo_path = os.path.join(self.current_event_path_abs, "Processed", photo_name)
        if not os.path.exists(processed_photo_path): 
            if self.current_processed_preview_pil:
                messagebox.showinfo("EXIF Info", "Showing EXIF from current preview. Save photo to see EXIF of the saved processed file.", parent=self)
                return 
            else:
                messagebox.showinfo("EXIF Info", "Processed photo file not found. Please process and save first.", parent=self)
                return
        self._show_exif_window(processed_photo_path, f"EXIF - Processed: {photo_name}")

    def clear_crop_rect(self):
        if self.current_crop_rect_id:
            self.original_canvas.delete(self.current_crop_rect_id)
            self.current_crop_rect_id = None
        self.manual_crop_coords_display = None

    def load_photo_list_for_event(self):
        self.current_photo_list = []
        if not self.current_event_path_abs or not os.path.isdir(self.current_event_path_abs):
            return
        photo_extensions = ('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.heic', '.webp')
        try:
            self.current_photo_list = sorted([
                f for f in os.listdir(self.current_event_path_abs)
                if os.path.isfile(os.path.join(self.current_event_path_abs, f)) and f.lower().endswith(photo_extensions)
            ])
        except Exception as e:
            messagebox.showerror("Error", f"Error loading photo list for event:\n{self.current_event_path_abs}\n{e}", parent=self)
            self.current_photo_list = [] # Ensure it's empty on error

    def _display_pil_image_on_canvas(self, pil_image, tk_canvas, tk_image_attr_name):
        tk_canvas.delete("all") 
        self.current_crop_rect_id = None # Reset crop rect ID since image is new/cleared

        if pil_image is None:
            # Ensure canvas dimensions are known before creating text
            tk_canvas.update_idletasks() 
            canvas_width = tk_canvas.winfo_width()
            canvas_height = tk_canvas.winfo_height()
            tk_canvas.create_text(canvas_width/2 if canvas_width > 1 else 200, 
                                  canvas_height/2 if canvas_height > 1 else 150, 
                                  text="No Image", anchor="center", font=("Helvetica", 16))
            setattr(self, tk_image_attr_name, None)
            self.display_to_original_scale_x = 1.0 
            self.display_to_original_scale_y = 1.0
            return

        # Ensure canvas dimensions are known before thumbnailing
        tk_canvas.update_idletasks() 
        canvas_width = tk_canvas.winfo_width()
        canvas_height = tk_canvas.winfo_height()
        if canvas_width <= 1: canvas_width = 400 # Fallback width if not rendered
        if canvas_height <= 1: canvas_height = 300 # Fallback height if not rendered

        img_copy = pil_image.copy()
        original_w, original_h = img_copy.size
        
        # Create thumbnail to fit canvas, preserving aspect ratio
        img_copy.thumbnail((canvas_width - 4, canvas_height - 4), Image.Resampling.LANCZOS) # -4 for border
        thumb_w, thumb_h = img_copy.size
        
        # Calculate scaling factors from original image to displayed thumbnail
        self.display_to_original_scale_x = original_w / thumb_w if thumb_w > 0 else 1.0
        self.display_to_original_scale_y = original_h / thumb_h if thumb_h > 0 else 1.0

        tk_image_ref = ImageTk.PhotoImage(img_copy)
        setattr(self, tk_image_attr_name, tk_image_ref) # Store reference to avoid garbage collection

        # Position image in the center of the canvas
        x_pos = (canvas_width - thumb_w) / 2
        y_pos = (canvas_height - thumb_h) / 2
        tk_canvas.create_image(x_pos, y_pos, image=tk_image_ref, anchor="nw", tags="bg_image")
        # tk_canvas.image = tk_image_ref # Another way to keep reference, usually setattr is enough

    def _display_pil_image_on_label(self, pil_image, label_widget, tk_image_attr_name):
        if pil_image is None:
            label_widget.config(image='', text="No Image")
            setattr(self, tk_image_attr_name, None)
            return
        try:
            # Ensure widget dimensions are known before thumbnailing
            label_widget.update_idletasks() 
            max_width = label_widget.winfo_width() - 10 # some padding
            max_height = label_widget.winfo_height() - 10

            if max_width <= 1: max_width = 400 # Fallback if not rendered
            if max_height <= 1: max_height = 300 # Fallback if not rendered

            img_copy = pil_image.copy()
            img_copy.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            tk_image = ImageTk.PhotoImage(img_copy)
            setattr(self, tk_image_attr_name, tk_image) # Keep a reference
            label_widget.config(image=tk_image, text="")
        except Exception as e:
            label_widget.config(image='', text=f"Error displaying: {e}")
            setattr(self, tk_image_attr_name, None)
            print(f"Error in _display_pil_image_on_label: {e}", exc_info=True)

    def _show_enlarged_image(self, pil_image_to_show, title="Enlarged Image", base_path_for_saving=None): 
        if not pil_image_to_show: return
        top = tk.Toplevel(self)
        top.title(title)
        # Store the full resolution image and base path on the Toplevel window 
        # so the save button's command can access them.
        top.pil_image_to_save = pil_image_to_show 
        top.base_path_for_saving = base_path_for_saving

        img_w, img_h = pil_image_to_show.size
        max_screen_w = int(self.winfo_screenwidth() * 0.8); max_screen_h = int(self.winfo_screenheight() * 0.8)
        display_img = pil_image_to_show.copy()
        if img_w > max_screen_w or img_h > max_screen_h:
            display_img.thumbnail((max_screen_w, max_screen_h), Image.Resampling.LANCZOS)
        
        photo_img = ImageTk.PhotoImage(display_img)
        img_label = ttk.Label(top, image=photo_img)
        img_label.image = photo_img # Keep reference for display
        img_label.pack(padx=10, pady=10)
        
        # Frame for buttons
        button_frame = ttk.Frame(top)
        button_frame.pack(pady=5)

        # Save This View Button
        save_button = ttk.Button(button_frame, text="Save This View", 
                                 command=lambda: self._save_enlarged_action(top.pil_image_to_save, top.base_path_for_saving, top))
        save_button.pack(side=tk.LEFT, padx=5)
        
        # Close Button
        close_button = ttk.Button(button_frame, text="Close", command=top.destroy)
        close_button.pack(side=tk.LEFT, padx=5)
        
        top.grab_set(); top.transient(self.winfo_toplevel())

    # In ProcessTab class:
    def _save_enlarged_action(self, image_to_save_pil, base_path_for_saving, toplevel_window):
        if not image_to_save_pil:
            messagebox.showerror("Save Error", "No image data to save.", parent=toplevel_window)
            return
        
        # Suggest a filename
        initial_dir = os.path.expanduser("~") # Default to home directory
        suggested_filename = "enlarged_image.jpg" # Default filename

        if base_path_for_saving:
            initial_dir = os.path.dirname(base_path_for_saving)
            name, ext = os.path.splitext(os.path.basename(base_path_for_saving))
            suggested_filename = f"{name}_enlarged{ext if ext else '.jpg'}"
        
        file_types = [("JPEG files", "*.jpg"), ("PNG files", "*.png"), ("All files", "*.*")]
        
        save_path = filedialog.asksaveasfilename(
            parent=toplevel_window, # Make dialog modal to the enlarged image window
            title="Save Enlarged Image As...",
            initialdir=initial_dir,
            initialfile=suggested_filename,
            defaultextension=".jpg",
            filetypes=file_types
        )
        if save_path:
            try:
                # Use the full resolution image_to_save_pil for saving
                self.image_processor.save_image_pil(image_to_save_pil, save_path)
                messagebox.showinfo("Image Saved", f"Enlarged image saved to:\n{save_path}", parent=toplevel_window)
            except Exception as e:
                messagebox.showerror("Save Error", f"Could not save image: {e}", parent=toplevel_window)
                print(f"Error saving enlarged image: {e}", exc_info=True)
