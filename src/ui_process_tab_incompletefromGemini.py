import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from PIL import Image, ImageTk
import shutil 
import tkinter.simpledialog 
import piexif 
import piexif.helper 
import numpy as np 
import json 
from datetime import datetime # For update_exif_status_indicators date check

from image_processor import ImageProcessor
from file_utils import ensure_directory_exists, create_dot_nomedia

class ProcessTab(ttk.Frame):
    def __init__(self, parent_notebook, app_config):
        super().__init__(parent_notebook)
        self.app_config = app_config
        self.image_processor = ImageProcessor(self.app_config)
        
        # These paths are now fetched dynamically when needed using app_config.get_path()
        # self.imported_phone_events_root_abs = self.app_config.get_path('imported_phone_events_path')
        # self.processed_events_root_abs = self.app_config.get_path('processed_events_path')
        # self.final_photos_root_abs = self.app_config.get_path('final_photos_path')

        self.current_event_name_str = None
        self.current_event_path_abs = None # Path to event folder IN ImportedPhoneEvents
        self.current_photo_list = []
        self.current_photo_index = -1
        self.original_image_pil = None 
        self.original_image_tk_canvas_ref = None 
        self.processed_image_tk = None 
        self.current_processed_preview_pil = None 

        self.manual_crop_active = False
        self.crop_rect_start_x = None; self.crop_rect_start_y = None 
        self.current_crop_rect_id = None; self.manual_crop_coords_display = None 
        self.display_to_original_scale_x = 1.0; self.display_to_original_scale_y = 1.0 

        self.hsv_default_lower_fallback = [90, 40, 100]
        self.hsv_default_upper_fallback = [130, 255, 255]
        config_hsv_lower = self.app_config.get_setting('pale_blue_hsv_lower', self.hsv_default_lower_fallback)
        config_hsv_upper = self.app_config.get_setting('pale_blue_hsv_upper', self.hsv_default_upper_fallback)
        if not isinstance(config_hsv_lower, list) or len(config_hsv_lower)!=3: config_hsv_lower=list(self.hsv_default_lower_fallback)
        if not isinstance(config_hsv_upper, list) or len(config_hsv_upper)!=3: config_hsv_upper=list(self.hsv_default_upper_fallback)

        self.alternative_hsv_ranges = [
            {'name': 'From Config/Defaults', 'lower': list(config_hsv_lower), 'upper': list(config_hsv_upper)}, 
            {'name': 'Wider Saturation', 'lower': [90, 20, 90], 'upper': [135, 255, 255]}, 
            # ... (other HSV ranges as before) ...
            {'name': 'Darker Overall (Lower V_max, if needed)', 'lower': [90, 40, 100], 'upper': [130, 255, 200]},
        ]
        
        self.style = ttk.Style(); self.style.configure("Green.TLabel", foreground="green", font=('Helvetica',12,'bold')); self.style.configure("Red.TLabel", foreground="red", font=('Helvetica',12,'bold'))

        # --- UI Layout (structurally same, paths updated in methods) ---
        # ... (All UI setup from previous version photo_processor_ui_process_tab_py_v9) ...
        # For brevity, assuming the UI layout code is identical to the previous version.
        # The key changes are in methods that use paths.
        top_controls_frame = ttk.Frame(self); top_controls_frame.pack(fill=tk.X, padx=5, pady=5)
        event_selection_frame = ttk.LabelFrame(top_controls_frame, text="Event"); event_selection_frame.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        ttk.Label(event_selection_frame, text="Select Event from Imported Phone Events:").pack(side=tk.LEFT, padx=5)
        self.event_var = tk.StringVar(); self.event_dropdown = ttk.Combobox(event_selection_frame, textvariable=self.event_var, state="readonly", width=30); self.event_dropdown.pack(side=tk.LEFT, padx=5)
        self.event_dropdown.bind("<<ComboboxSelected>>", self.on_event_selected) 
        ttk.Button(event_selection_frame, text="Refresh List", command=self.populate_event_dropdown).pack(side=tk.LEFT, padx=5)
        main_process_frame = ttk.Frame(self); main_process_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        controls_panel = ttk.Frame(main_process_frame, width=300); controls_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0,10), pady=5); controls_panel.pack_propagate(False) 
        image_display_pane = ttk.PanedWindow(main_process_frame, orient=tk.HORIZONTAL); image_display_pane.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, pady=5)
        original_display_container = ttk.Frame(image_display_pane)
        original_frame = ttk.LabelFrame(original_display_container, text="Original (Click Enlarge, Drag for Manual Crop)"); self.original_canvas = tk.Canvas(original_frame, bg="lightgrey", relief="groove", bd=2); self.original_canvas.pack(fill=tk.BOTH, expand=True)
        self.original_canvas.bind("<ButtonPress-1>", self.on_canvas_press); self.original_canvas.bind("<B1-Motion>", self.on_canvas_drag); self.original_canvas.bind("<ButtonRelease-1>", self.on_canvas_release); self.original_canvas.bind("<Button-3>", self.enlarge_original_image)
        original_frame.pack(fill=tk.BOTH, expand=True)
        original_exif_frame = ttk.Frame(original_display_container); self.original_exif_button = ttk.Button(original_exif_frame, text="EXIF", command=self.show_original_exif_data, state=tk.DISABLED); self.original_exif_button.pack(side=tk.LEFT, pady=2)
        self.original_exif_status_label = ttk.Label(original_exif_frame, text="✗", font=('Helvetica',12,'bold')); self.original_exif_status_label.pack(side=tk.LEFT,padx=(5,0),pady=2); original_exif_frame.pack(); image_display_pane.add(original_display_container,weight=1)
        processed_display_container = ttk.Frame(image_display_pane)
        processed_frame = ttk.LabelFrame(processed_display_container, text="Processed Preview (Click to Enlarge)"); self.processed_image_label = ttk.Label(processed_frame, text="Processed Preview", anchor="center", relief="groove"); self.processed_image_label.pack(fill=tk.BOTH, expand=True)
        self.processed_image_label.bind("<Button-1>", self.enlarge_processed_image); processed_frame.pack(fill=tk.BOTH, expand=True)
        processed_exif_frame = ttk.Frame(processed_display_container); self.processed_exif_button = ttk.Button(processed_exif_frame, text="EXIF", command=self.show_processed_exif_data, state=tk.DISABLED); self.processed_exif_button.pack(side=tk.LEFT, pady=2)
        self.processed_exif_status_label = ttk.Label(processed_exif_frame, text="✗", font=('Helvetica',12,'bold')); self.processed_exif_status_label.pack(side=tk.LEFT,padx=(5,0),pady=2); processed_exif_frame.pack(); image_display_pane.add(processed_display_container,weight=1)
        self.auto_orient_var = tk.BooleanVar(value=True); ttk.Checkbutton(controls_panel, text="Auto-Orient (from EXIF)", variable=self.auto_orient_var).pack(anchor="w",pady=2)
        crop_mode_frame = ttk.LabelFrame(controls_panel, text="Cropping Mode"); crop_mode_frame.pack(fill=tk.X,pady=5); self.crop_mode_var = tk.StringVar(value="auto_color_bg") 
        ttk.Radiobutton(crop_mode_frame, text="Auto-Crop (Blue BG)", variable=self.crop_mode_var, value="auto_color_bg", command=self.on_crop_mode_changed).pack(anchor="w")
        self.auto_crop_params_frame = ttk.Frame(crop_mode_frame)
        hsv_lower_frame = ttk.Frame(self.auto_crop_params_frame); ttk.Label(hsv_lower_frame, text="HSV Lower (H,S,V):").pack(side=tk.LEFT,padx=(20,2)); self.hsv_lower_vars = [tk.IntVar(),tk.IntVar(),tk.IntVar()]
        for i,var in enumerate(self.hsv_lower_vars): var.set(config_hsv_lower[i]); ttk.Entry(hsv_lower_frame,textvariable=var,width=4).pack(side=tk.LEFT,padx=1)
        hsv_lower_frame.pack(fill=tk.X)
        hsv_upper_frame = ttk.Frame(self.auto_crop_params_frame); ttk.Label(hsv_upper_frame, text="HSV Upper (H,S,V):").pack(side=tk.LEFT,padx=(20,2)); self.hsv_upper_vars = [tk.IntVar(),tk.IntVar(),tk.IntVar()]
        for i,var in enumerate(self.hsv_upper_vars): var.set(config_hsv_upper[i]); ttk.Entry(hsv_upper_frame,textvariable=var,width=4).pack(side=tk.LEFT,padx=1)
        hsv_upper_frame.pack(fill=tk.X)
        inward_offset_sub_frame = ttk.Frame(self.auto_crop_params_frame); ttk.Label(inward_offset_sub_frame, text="Inward Offset (px):").pack(side=tk.LEFT,padx=(20,0)); self.auto_crop_inward_offset_var = tk.IntVar(value=self.app_config.get_setting('auto_crop_inward_offset',5)); ttk.Entry(inward_offset_sub_frame,textvariable=self.auto_crop_inward_offset_var,width=4).pack(side=tk.LEFT); inward_offset_sub_frame.pack(fill=tk.X)
        self.find_hsv_button = ttk.Button(self.auto_crop_params_frame, text="Find Optimal HSV", command=self.find_optimal_hsv_for_autocrop); self.find_hsv_button.pack(pady=5,padx=20,fill=tk.X)
        ttk.Radiobutton(crop_mode_frame, text="Percentage", variable=self.crop_mode_var, value="percent", command=self.on_crop_mode_changed).pack(anchor="w")
        self.crop_percent_frame = ttk.Frame(crop_mode_frame); self.crop_vars = {}
        for i,side in enumerate(["Top","Right","Bottom","Left"]): ttk.Label(self.crop_percent_frame,text=f"{side}:").grid(row=i,column=0,sticky="w",padx=(20,0)); var=tk.DoubleVar(value=self.app_config.get_setting(f'default_crop_{side.lower()}',2.0)); ttk.Entry(self.crop_percent_frame,textvariable=var,width=5).grid(row=i,column=1); self.crop_vars[side.lower()]=var
        ttk.Radiobutton(crop_mode_frame, text="Manual Draw (on Original)", variable=self.crop_mode_var, value="manual", command=self.on_crop_mode_changed).pack(anchor="w"); self.on_crop_mode_changed() 
        rotation_frame = ttk.LabelFrame(controls_panel, text="Rotation (CCW Deg)"); rotation_frame.pack(fill=tk.X,pady=5); self.rotation_var = tk.DoubleVar(value=0.0); ttk.Scale(rotation_frame,from_=-45,to=45,orient=tk.HORIZONTAL,variable=self.rotation_var,length=180).pack(fill=tk.X,padx=5)
        rotation_buttons_frame = ttk.Frame(rotation_frame); rotation_buttons_frame.pack(fill=tk.X,pady=2)
        ttk.Button(rotation_buttons_frame,text="-90°",command=lambda:self.adjust_rotation(-90)).pack(side=tk.LEFT,padx=2); ttk.Entry(rotation_buttons_frame,textvariable=self.rotation_var,width=5,justify='center').pack(side=tk.LEFT,padx=2); ttk.Button(rotation_buttons_frame,text="+90°",command=lambda:self.adjust_rotation(90)).pack(side=tk.LEFT,padx=2); ttk.Button(rotation_buttons_frame,text="180°",command=lambda:self.adjust_rotation(180)).pack(side=tk.LEFT,padx=2); ttk.Button(rotation_buttons_frame,text="Reset",command=self.reset_rotation).pack(side=tk.LEFT,padx=2)
        enhancement_frame = ttk.LabelFrame(controls_panel, text="OpenCV Enhancements"); enhancement_frame.pack(fill=tk.X,pady=5); self.use_clahe_var = tk.BooleanVar(value=True); ttk.Checkbutton(enhancement_frame,text="Use CLAHE (Contrast)",variable=self.use_clahe_var).pack(anchor="w"); self.use_bilateral_var = tk.BooleanVar(value=True); ttk.Checkbutton(enhancement_frame,text="Use Bilateral Filter (Smooth)",variable=self.use_bilateral_var).pack(anchor="w"); self.use_sharpen_var = tk.BooleanVar(value=True); ttk.Checkbutton(enhancement_frame,text="Use Unsharp Mask (Sharpen)",variable=self.use_sharpen_var).pack(anchor="w")
        action_buttons_frame = ttk.Frame(self); action_buttons_frame.pack(fill=tk.X,pady=10); self.preview_button = ttk.Button(action_buttons_frame,text="Preview Changes",command=self.preview_current_photo_processing); self.preview_button.pack(side=tk.LEFT,padx=10); self.save_processed_button = ttk.Button(action_buttons_frame,text="Save Processed Photo",command=self.save_current_processed_photo); self.save_processed_button.pack(side=tk.LEFT,padx=10); self.process_all_button = ttk.Button(action_buttons_frame,text="Process All in Event",command=self.process_all_photos_in_event); self.process_all_button.pack(side=tk.LEFT,padx=10); self.finalize_event_button = ttk.Button(action_buttons_frame,text="Move Processed to Final",command=self.finalize_event); self.finalize_event_button.pack(side=tk.RIGHT,padx=10)
        navigation_frame = ttk.Frame(self); navigation_frame.pack(fill=tk.X,pady=5,before=action_buttons_frame); self.prev_button = ttk.Button(navigation_frame,text="<< Previous",command=self.prev_photo,state=tk.DISABLED); self.prev_button.pack(side=tk.LEFT,padx=10); self.photo_info_label = ttk.Label(navigation_frame,text="Photo X of Y"); self.photo_info_label.pack(side=tk.LEFT,expand=True,fill=tk.X,anchor="center"); self.next_button = ttk.Button(navigation_frame,text="Next >>",command=self.next_photo,state=tk.DISABLED); self.next_button.pack(side=tk.RIGHT,padx=10)
        self.populate_event_dropdown()

    # ... (All other methods: _method_missing_dummy, adjust_rotation, reset_rotation, on_crop_mode_changed, etc. are assumed to be here)
    # The key changes for pathing will be in populate_event_dropdown, on_event_selected,
    # load_and_display_current_photo, save_current_processed_photo, process_all_photos_in_event, finalize_event.

    def _method_missing_dummy(self, method_name):
        def dummy_command(): print(f"ERROR: Method ProcessTab.{method_name} is not defined!"); messagebox.showerror("Internal Error", f"Functionality for '{method_name}' is missing.", parent=self)
        return dummy_command

    def adjust_rotation(self, angle_change):
        current_angle = self.rotation_var.get(); new_angle = current_angle + angle_change
        while new_angle > 180: new_angle -= 360
        while new_angle <= -180: new_angle += 360 
        self.rotation_var.set(new_angle)

    def reset_rotation(self): self.rotation_var.set(0.0)

    def on_crop_mode_changed(self):
        mode = self.crop_mode_var.get()
        if mode == "percent": self.auto_crop_params_frame.pack_forget(); self.crop_percent_frame.pack(fill=tk.X, padx=(20,0)) 
        elif mode == "auto_color_bg": self.crop_percent_frame.pack_forget(); self.auto_crop_params_frame.pack(fill=tk.X, padx=(0,0)) 
        else: self.crop_percent_frame.pack_forget(); self.auto_crop_params_frame.pack_forget()
        if self.manual_crop_active and mode != "manual": self.clear_crop_rect(); self.manual_crop_active = False
        
    def get_current_processing_settings(self):
        settings = {"auto_orient": self.auto_orient_var.get(), "crop_mode": self.crop_mode_var.get(), "rotation": self.rotation_var.get(), "use_clahe": self.use_clahe_var.get(), "use_bilateral": self.use_bilateral_var.get(), "use_sharpen": self.use_sharpen_var.get()}
        current_crop_mode_ui = settings["crop_mode"]
        if current_crop_mode_ui == "percent": settings["crop_percent"] = {side: var.get() for side, var in self.crop_vars.items()}
        elif current_crop_mode_ui == "manual" and self.manual_crop_coords_display:
            disp_x1, disp_y1, disp_x2, disp_y2 = self.manual_crop_coords_display
            settings["manual_crop_box_scaled"] = (disp_x1*self.display_to_original_scale_x, disp_y1*self.display_to_original_scale_y, disp_x2*self.display_to_original_scale_x, disp_y2*self.display_to_original_scale_y)
            settings["crop_mode"] = "manual_scaled_coords" 
        elif current_crop_mode_ui == "auto_color_bg":
            settings["auto_crop_inward_offset"] = self.auto_crop_inward_offset_var.get()
            try: settings["hsv_lower_ui"] = [var.get() for var in self.hsv_lower_vars]; settings["hsv_upper_ui"] = [var.get() for var in self.hsv_upper_vars]
            except tk.TclError: messagebox.showwarning("Warning","Could not read HSV values. Using defaults.",parent=self); settings["hsv_lower_ui"]=self.app_config.get_setting('pale_blue_hsv_lower'); settings["hsv_upper_ui"]=self.app_config.get_setting('pale_blue_hsv_upper')
        return settings
        
    def _is_crop_effective(self, original_pil, cropped_pil):
        if cropped_pil is None or original_pil is None: return False
        width_diff = abs(original_pil.width - cropped_pil.width); height_diff = abs(original_pil.height - cropped_pil.height)
        if width_diff > 5 or height_diff > 5 or width_diff > original_pil.width * 0.01 or height_diff > original_pil.height * 0.01:
            if (cropped_pil.width * cropped_pil.height) > (0.05 * original_pil.width * original_pil.height): return True
        return False

    def find_optimal_hsv_for_autocrop(self): 
        if not self.original_image_pil: messagebox.showwarning("Find HSV", "No original image loaded.", parent=self); return
        print("Starting search for optimal HSV..."); self.update_idletasks() 
        oriented_pil = self.image_processor.auto_orient_pil(self.original_image_pil.copy()) if self.auto_orient_var.get() else self.original_image_pil.copy()
        cv_oriented = self.image_processor._pil_to_cv(oriented_pil)
        inward_offset = self.auto_crop_inward_offset_var.get()
        initial_hsv_lower = [var.get() for var in self.hsv_lower_vars]; initial_hsv_upper = [var.get() for var in self.hsv_upper_vars]
        all_ranges_to_try = [{'name': 'Current UI', 'lower': initial_hsv_lower, 'upper': initial_hsv_upper}] + [r for r in self.alternative_hsv_ranges if not (r['lower'] == initial_hsv_lower and r['upper'] == initial_hsv_upper)]
        found_effective_hsv = False; best_hsv_set_found = None
        for i, hsv_set in enumerate(all_ranges_to_try):
            current_hsv_lower, current_hsv_upper = hsv_set['lower'], hsv_set['upper']
            if not (isinstance(current_hsv_lower,list) and len(current_hsv_lower)==3 and isinstance(current_hsv_upper,list) and len(current_hsv_upper)==3 and all(isinstance(x,int) for x in current_hsv_lower) and all(isinstance(x,int) for x in current_hsv_upper)):
                print(f"Skipping invalid HSV: {hsv_set['name']}"); continue
            print(f"Trying HSV '{hsv_set['name']}': L={current_hsv_lower}, U={current_hsv_upper}"); self.update_idletasks() 
            cropped_cv = self.image_processor.auto_crop_on_color_background(cv_oriented.copy(), current_hsv_lower, current_hsv_upper, inward_offset_pixels=inward_offset)
            cropped_pil = self.image_processor._cv_to_pil(cropped_cv) if cropped_cv.size > 0 else None
            if cropped_pil and self._is_crop_effective(oriented_pil, cropped_pil):
                print(f"Effective crop with '{hsv_set['name']}'"); [v.set(current_hsv_lower[j]) for j,v in enumerate(self.hsv_lower_vars)]; [v.set(current_hsv_upper[j]) for j,v in enumerate(self.hsv_upper_vars)]; best_hsv_set_found = hsv_set; found_effective_hsv = True; break
            else: print(f"'{hsv_set['name']}' not effective.")
        if found_effective_hsv: messagebox.showinfo("Optimal HSV", f"Found: {best_hsv_set_found['name']}.\nUI updated. Preview to apply.", parent=self); self.preview_current_photo_processing() 
        else: messagebox.showwarning("Optimal HSV", "No better HSV settings found.", parent=self)

    def populate_event_dropdown(self):
        imported_phone_events_root = self.app_config.get_path('imported_phone_events_path') # UPDATED
        if not imported_phone_events_root or not os.path.isdir(imported_phone_events_root):
            self.event_dropdown['values'] = []; self.event_var.set(""); self.clear_photo_display_and_list(); return
        try:
            events = sorted([d for d in os.listdir(imported_phone_events_root) if os.path.isdir(os.path.join(imported_phone_events_root, d))])
            self.event_dropdown['values'] = events
            current_selection = self.event_var.get()
            if events:
                if current_selection not in events: self.event_var.set(events[0])
            else: self.event_var.set("")
            self.on_event_selected(None) 
        except Exception as e: messagebox.showerror("Error", f"Could not list events: {e}", parent=self)

    def on_event_selected(self, event_unused=None): 
        event_name = self.event_var.get()
        self.current_processed_preview_pil = None 
        if not event_name: self.clear_photo_display_and_list(); self.current_event_name_str=None; self.current_event_path_abs=None; return
        self.current_event_name_str = event_name
        self.current_event_path_abs = os.path.join(self.app_config.get_path('imported_phone_events_path'), event_name) # UPDATED
        self.clear_crop_rect(); self.load_photo_list_for_event()
        if self.current_photo_list: self.current_photo_index = 0; self.load_and_display_current_photo()
        else: self.clear_photo_display_and_list()
        self.update_navigation_buttons_state()

    def load_photo_list_for_event(self):
        self.current_photo_list = []
        if not self.current_event_path_abs or not os.path.isdir(self.current_event_path_abs): return
        photo_extensions = ('.png','.jpg','.jpeg','.tif','.tiff','.heic','.webp')
        try: self.current_photo_list = sorted([f for f in os.listdir(self.current_event_path_abs) if os.path.isfile(os.path.join(self.current_event_path_abs,f)) and f.lower().endswith(photo_extensions)])
        except Exception as e: messagebox.showerror("Error",f"Error loading photo list for event:\n{self.current_event_path_abs}\n{e}",parent=self); self.current_photo_list=[]

    def _display_pil_image_on_canvas(self, pil_image, tk_canvas, tk_image_attr_name):
        tk_canvas.delete("all"); self.current_crop_rect_id = None 
        if pil_image is None:
            tk_canvas.update_idletasks(); cw=tk_canvas.winfo_width(); ch=tk_canvas.winfo_height()
            tk_canvas.create_text(cw/2 if cw>1 else 200, ch/2 if ch>1 else 150, text="No Image",anchor="center",font=("Helvetica",16))
            setattr(self,tk_image_attr_name,None); self.display_to_original_scale_x=1.0; self.display_to_original_scale_y=1.0; return
        tk_canvas.update_idletasks(); cw=tk_canvas.winfo_width(); ch=tk_canvas.winfo_height()
        if cw <= 1: 
            cw = 400; 
        If ch <= 1: 
            ch = 300
        img=pil_image.copy(); orig_w,orig_h=img.size; img.thumbnail((cw-4,ch-4),Image.Resampling.LANCZOS); tw,th=img.size
        self.display_to_original_scale_x=orig_w/tw if tw>0 else 1.0; self.display_to_original_scale_y=orig_h/th if th>0 else 1.0
        tk_img=ImageTk.PhotoImage(img); setattr(self,tk_image_attr_name,tk_img)
        x_pos=(cw-tw)/2; y_pos=(ch-th)/2; tk_canvas.create_image(x_pos,y_pos,image=tk_img,anchor="nw",tags="bg_image")

    def _display_pil_image_on_label(self, pil_image, label_widget, tk_image_attr_name):
        if pil_image is None: label_widget.config(image='',text="No Image"); setattr(self,tk_image_attr_name,None); return
        try:
            label_widget.update_idletasks(); mw=label_widget.winfo_width()-10; mh=label_widget.winfo_height()-10
            if mw<=1: mw=400; If mh<=1: mh=300
            img=pil_image.copy(); img.thumbnail((mw,mh),Image.Resampling.LANCZOS)
            tk_img=ImageTk.PhotoImage(img); setattr(self,tk_image_attr_name,tk_img); label_widget.config(image=tk_img,text="")
        except Exception as e: label_widget.config(image='',text=f"Error: {e}"); setattr(self,tk_image_attr_name,None); print(f"Error in _display_pil_image_on_label: {e}",exc_info=True)

    def load_and_display_current_photo(self):
        self.clear_crop_rect(); self.current_processed_preview_pil = None 
        if not self.current_photo_list or self.current_photo_index == -1: self.clear_photo_display_and_list(); return
        photo_name = self.current_photo_list[self.current_photo_index]
        original_photo_path = os.path.join(self.current_event_path_abs, photo_name) # Path in ImportedPhoneEvents
        try:
            self.original_image_pil = Image.open(original_photo_path)
            self._display_pil_image_on_canvas(self.original_image_pil, self.original_canvas, "original_image_tk_canvas_ref")
            self.original_exif_button.config(state=tk.NORMAL) 
        except Exception as e: self.original_image_pil=None; self._display_pil_image_on_canvas(None,self.original_canvas,"original_image_tk_canvas_ref"); self.original_exif_button.config(state=tk.DISABLED); messagebox.showerror("Error",f"Could not load {photo_name}: {e}",parent=self)
        
        # Path for processed image is now in ProcessedEvents/EventName/
        processed_photo_path = os.path.join(self.app_config.get_path('processed_events_path'), self.current_event_name_str, photo_name)
        self._display_pil_image_on_label(None, self.processed_image_label, "processed_image_tk") # Clear previous preview
        self.processed_exif_button.config(state=tk.DISABLED) 
        if os.path.exists(processed_photo_path):
            try:
                processed_pil_disk = Image.open(processed_photo_path)
                self._display_pil_image_on_label(processed_pil_disk, self.processed_image_label, "processed_image_tk")
                # Do NOT set self.current_processed_preview_pil here, so EXIF indicator stays 'x'
                self.processed_exif_button.config(state=tk.NORMAL) 
            except Exception as e: print(f"Error loading saved processed {photo_name}: {e}")
        
        self.photo_info_label.config(text=f"{photo_name} ({self.current_photo_index+1} of {len(self.current_photo_list)})")
        self.update_navigation_buttons_state(); self.update_exif_status_indicators() 

    def clear_photo_display_and_list(self):
        self.current_photo_list=[]; self.current_photo_index=-1; self.original_image_pil=None
        self._display_pil_image_on_canvas(None,self.original_canvas,"original_image_tk_canvas_ref")
        self._display_pil_image_on_label(None,self.processed_image_label,"processed_image_tk")
        self.current_processed_preview_pil=None; self.photo_info_label.config(text="Photo X of Y")
        self.original_exif_button.config(state=tk.DISABLED); self.processed_exif_button.config(state=tk.DISABLED)
        self.update_exif_status_indicators(); self.clear_crop_rect(); self.update_navigation_buttons_state()

    def update_navigation_buttons_state(self):
        has_photos=bool(self.current_photo_list)
        self.prev_button.config(state=tk.NORMAL if has_photos and self.current_photo_index>0 else tk.DISABLED)
        self.next_button.config(state=tk.NORMAL if has_photos and self.current_photo_index<len(self.current_photo_list)-1 else tk.DISABLED)
        action_state=tk.NORMAL if self.original_image_pil else tk.DISABLED
        self.preview_button.config(state=action_state); self.save_processed_button.config(state=action_state)
        self.original_exif_button.config(state=action_state)
        self.processed_exif_button.config(state=tk.NORMAL if self.current_processed_preview_pil or \
            (self.current_event_name_str and self.current_photo_list and self.current_photo_index != -1 and \
             os.path.exists(os.path.join(self.app_config.get_path('processed_events_path'), self.current_event_name_str, self.current_photo_list[self.current_photo_index]))) \
            else tk.DISABLED) # Enable if preview OR saved file exists
        self.process_all_button.config(state=tk.NORMAL if has_photos else tk.DISABLED)
        self.finalize_event_button.config(state=tk.NORMAL if has_photos else tk.DISABLED)

    def next_photo(self): 
        if self.current_photo_index < len(self.current_photo_list)-1: self.current_photo_index+=1; self.load_and_display_current_photo()
        self.update_navigation_buttons_state()

    def prev_photo(self): 
        if self.current_photo_index > 0: self.current_photo_index-=1; self.load_and_display_current_photo()
        self.update_navigation_buttons_state()

    def preview_current_photo_processing(self):
        if not self.original_image_pil: messagebox.showwarning("Preview","No original loaded.",parent=self); return
        settings = self.get_current_processing_settings(); print(f"Previewing: {settings}")
        try:
            processed_pil = self.image_processor.process_image(self.original_image_pil, settings, base_image_for_processing=None)
            self.current_processed_preview_pil = processed_pil 
            self._display_pil_image_on_label(processed_pil, self.processed_image_label, "processed_image_tk")
        except Exception as e: messagebox.showerror("Processing Error",f"Preview failed: {e}",parent=self); print(f"Preview error: {e}",exc_info=True); self.current_processed_preview_pil=None; self._display_pil_image_on_label(None,self.processed_image_label,"processed_image_tk")
        self.update_exif_status_indicators(); self.processed_exif_button.config(state=tk.NORMAL if self.current_processed_preview_pil else tk.DISABLED)

    def save_current_processed_photo(self):
        img_to_save = self.current_processed_preview_pil
        if not img_to_save:
            if not self.original_image_pil: messagebox.showerror("Error","No original image.",parent=self); return
            print("No preview, re-processing for save..."); settings=self.get_current_processing_settings()
            try: img_to_save = self.image_processor.process_image(self.original_image_pil, settings, base_image_for_processing=None)
            except Exception as e: messagebox.showerror("Processing Error",f"Could not process for saving: {e}",parent=self); return
        if not img_to_save: messagebox.showerror("Error","Failed to generate for saving.",parent=self); return
        if not self.current_event_name_str or not self.current_photo_list or self.current_photo_index==-1: messagebox.showerror("Error","No photo selected.",parent=self); return
        
        photo_name = self.current_photo_list[self.current_photo_index]
        processed_event_dir = ensure_directory_exists(os.path.join(self.app_config.get_path('processed_events_path'), self.current_event_name_str))
        create_dot_nomedia(processed_event_dir)
        processed_photo_path = os.path.join(processed_event_dir, photo_name)
        try:
            self.image_processor.save_image_pil(img_to_save, processed_photo_path)
            messagebox.showinfo("Saved",f"Processed photo saved to:\n{processed_photo_path}",parent=self)
            self.current_processed_preview_pil = img_to_save 
            self._display_pil_image_on_label(img_to_save, self.processed_image_label, "processed_image_tk")
        except Exception as e: messagebox.showerror("Save Error",f"Could not save: {e}",parent=self); print(f"Save error: {e}",exc_info=True)
        self.update_exif_status_indicators(); self.processed_exif_button.config(state=tk.NORMAL if self.current_processed_preview_pil else tk.DISABLED)

    def process_all_photos_in_event(self):
        if not self.current_event_path_abs or not self.current_photo_list: messagebox.showerror("Error","No event/photos loaded.",parent=self); return
        if not messagebox.askyesno("Confirm","Process all in event with current settings? May overwrite.",parent=self): return
        settings_for_batch = self.get_current_processing_settings() 
        if settings_for_batch.get("crop_mode")=="manual_scaled_coords": print("Batch: Manual crop selected, NO CROP for batch."); settings_for_batch["crop_mode"]="none"
        
        source_event_dir = self.current_event_path_abs # From ImportedPhoneEvents
        target_processed_event_dir = ensure_directory_exists(os.path.join(self.app_config.get_path('processed_events_path'), self.current_event_name_str))
        create_dot_nomedia(target_processed_event_dir)
        
        s_count,f_count=0,0
        for i,name in enumerate(self.current_photo_list):
            self.photo_info_label.config(text=f"Processing: {name} ({i+1}/{len(self.current_photo_list)})"); self.update_idletasks()
            orig_path=os.path.join(source_event_dir,name); target_path=os.path.join(target_processed_event_dir,name)
            try:
                with Image.open(orig_path) as img:
                    proc_img=self.image_processor.process_image(img,settings_for_batch,base_image_for_processing=None)
                    if proc_img: self.image_processor.save_image_pil(proc_img,target_path); s_count+=1
                    else: print(f"Processing {name} gave None."); f_count+=1
            except Exception as e: print(f"Error processing {name}: {e}",exc_info=True); f_count+=1
        messagebox.showinfo("Batch Process",f"Processed {s_count} photos.\nFailed for {f_count}.",parent=self)
        self.load_and_display_current_photo()

    def finalize_event(self):
        if not self.current_event_name_str: messagebox.showerror("Error","No event selected.",parent=self); return
        source_dir = os.path.join(self.app_config.get_path('processed_events_path'), self.current_event_name_str)
        if not os.path.isdir(source_dir) or not any(f.lower().endswith(('.png','.jpg','.jpeg','.webp')) for f in os.listdir(source_dir)):
            messagebox.showinfo("Info","No processed photos to move.",parent=self); return
        target_dir = ensure_directory_exists(os.path.join(self.app_config.get_path('final_photos_path'), self.current_event_name_str))
        create_dot_nomedia(target_dir)
        if os.path.exists(target_dir) and any(f.lower().endswith(('.png','.jpg','.jpeg','.webp')) for f in os.listdir(target_dir)):
            if not messagebox.askyesno("Confirm",f"Event '{self.current_event_name_str}' already in Final. Overwrite?",parent=self): return
        try:
            count=0
            for item in os.listdir(source_dir):
                s=os.path.join(source_dir,item); d=os.path.join(target_dir,item)
                if os.path.isfile(s) and s.lower().endswith(('.png','.jpg','.jpeg','.webp')): shutil.copy2(s,d); count+=1
            messagebox.showinfo("Finalized",f"{count} photos moved to Final.",parent=self)
        except Exception as e: messagebox.showerror("Finalize Error",f"Could not move: {e}",parent=self)

    def _format_exif_data(self, exif_dict):
        if not exif_dict: return "No EXIF data."
        lines=[]
        for ifd,tags in exif_dict.items():
            if ifd=="thumbnail": lines.append(f"Thumbnail: {'Present' if tags else 'None'}"); continue
            lines.append(f"\n--- {ifd} ---")
            if not isinstance(tags,dict): lines.append(f" Invalid IFD {ifd}"); continue
            for tag,val in tags.items():
                info=piexif.TAGS.get(ifd,{}).get(tag); name=info["name"] if info else f"Unknown_{tag}"
                dv=val
                if isinstance(val,bytes):
                    if name=="UserComment" and ifd=="Exif": try: dv=piexif.helper.load_comment(val)
                    except: dv=str(val)
                    else: try: dv=val.decode('utf-8',errors='replace').rstrip('\x00')
                    except: dv=str(val)
                elif isinstance(val,tuple) and len(val)>10: dv=f"{str(val)[:80]}..."
                else: dv=str(val)
                if len(str(dv))>150: dv=str(dv)[:150]+"..."
                lines.append(f"  {name} (0x{tag:04x}): {dv}")
        return "\n".join(lines)

    def _show_exif_window(self, photo_path, title):
        if not photo_path or not os.path.exists(photo_path): messagebox.showwarning("EXIF","Path invalid.",parent=self); return
        try: exif_dict=piexif.load(photo_path); exif_str=self._format_exif_data(exif_dict)
        except piexif.InvalidImageDataError: exif_str="Not valid image/no EXIF."
        except Exception as e: exif_str=f"Error reading EXIF: {e}"
        win=tk.Toplevel(self); win.title(title); win.geometry("600x450"); win.transient(self.winfo_toplevel()); win.grab_set()
        txt=tk.Text(win,wrap=tk.WORD,padx=5,pady=5,font=("Menlo",10) if os.name=='posix' else ("Consolas",10)); scroll=ttk.Scrollbar(win,command=txt.yview); txt.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT,fill=tk.Y); txt.pack(side=tk.LEFT,fill=tk.BOTH,expand=True); txt.insert(tk.END,exif_str); txt.configure(state='disabled')
        ttk.Button(win,text="Close",command=win.destroy).pack(pady=5)

    def show_original_exif_data(self):
        if not self.original_image_pil or not self.current_event_path_abs or self.current_photo_index==-1: messagebox.showinfo("EXIF","No original loaded.",parent=self); return
        name=self.current_photo_list[self.current_photo_index]; path=os.path.join(self.current_event_path_abs,name)
        self._show_exif_window(path,f"EXIF - Original: {name}")

    def show_processed_exif_data(self):
        if not self.current_event_name_str or not self.current_photo_list or self.current_photo_index == -1: messagebox.showinfo("EXIF","No photo selected.",parent=self); return
        name=self.current_photo_list[self.current_photo_index]
        path=os.path.join(self.app_config.get_path('processed_events_path'), self.current_event_name_str, name)
        if not os.path.exists(path):
            if self.current_processed_preview_pil: messagebox.showinfo("EXIF","Preview EXIF. Save to see saved file EXIF.",parent=self); return
            else: messagebox.showinfo("EXIF","Processed file not found. Process/save first.",parent=self); return
        self._show_exif_window(path,f"EXIF - Processed: {name}")

    def update_exif_status_indicators(self):
        orig_text="✗"; proc_text="✗"; orig_meta=False
        if self.current_event_path_abs and self.original_image_pil:
            meta_path=os.path.join(self.current_event_path_abs,"EventMetadata.json")
            if os.path.exists(meta_path):
                try:
                    with open(meta_path,'r') as f: data=json.load(f)
                    if any(data.get(k) for k in ['event_keywords','event_city','event_country','event_latitude','event_longitude']) or \
                       (data.get('event_date') and not data.get('event_date').startswith(datetime.now().strftime("%Y-%m-%d"))): # Basic check for non-default date
                        orig_meta=True
                except Exception as e: print(f"Error checking metadata for EXIF status: {e}")
        if orig_meta: orig_text="✓"
        
        if self.current_processed_preview_pil and orig_meta: proc_text="✓" # Only if current preview exists and original metadata was defined
        
        self.original_exif_status_label.config(text=orig_text)
        self.processed_exif_status_label.config(text=proc_text)

