import keyboard
import pygetwindow as gw
import pytesseract
import PIL.ImageGrab
import tkinter as tk
from deep_translator import GoogleTranslator
from PIL import Image, ImageDraw, ImageTk
import cv2
import numpy as np
import sys
from datetime import datetime
import json
import os
import time

class ConfigManager:
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.last_modified = 0
        self.config = self.load_config()

    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            else:
                default_config = {
                    "dev_mode": True,
                    "text": {
                        "font_family": "Arial",
                        "font_size": 22,
                        "font_bold": True,
                        "font_color": "#FFFFFF",
                        "background_color": "#000000"
                    },
                    "layout": {
                        "padding": {
                            "left": 20,
                            "right": 20,
                            "top": 50,
                            "bottom": 50
                        },
                        "margin": {
                            "left": 20,
                            "right": 20
                        },
                        "result_window": {
                            "width": 400,
                            "height": 200,
                            "x": 100,
                            "y": 100
                        }
                    },
                    "translation": {
                        "source": "auto",
                        "target": "id"
                    }
                }
                with open(self.config_file, 'w') as f:
                    json.dump(default_config, f, indent=4)
                return default_config
        except Exception as e:
            print(f"Error loading config: {e}")
            return None

    def check_update(self):
        try:
            current_mtime = os.path.getmtime(self.config_file)
            if current_mtime > self.last_modified:
                self.config = self.load_config()
                self.last_modified = current_mtime
                return True
            return False
        except Exception as e:
            print(f"Error checking config update: {e}")
            return False

class ResultWindow:
    def __init__(self, config_manager, on_capture, on_quit):
        self.config_manager = config_manager
        self.on_capture_callback = on_capture
        self.on_quit_callback = on_quit
        
        # Create window
        self.window = tk.Toplevel()
        self.window.title("Translation Result")
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        
        # Load position
        config = self.config_manager.config['layout']['result_window']
        self.window.geometry(f"{config['width']}x{config['height']}+{config['x']}+{config['y']}")
        
        # Create main container
        self.container = tk.Frame(self.window)
        self.container.pack(fill='both', expand=True)
        
        # Create title bar
        self.title_bar = tk.Frame(self.container, bg='#2e2e2e', height=30)
        self.title_bar.pack(fill='x')
        self.title_bar.pack_propagate(False)
        self.title_bar.bind('<Button-1>', self.start_drag)
        self.title_bar.bind('<B1-Motion>', self.on_drag)
        
        # Title label
        self.title_label = tk.Label(self.title_bar, text="Translation Result", bg='#2e2e2e', fg='white')
        self.title_label.pack(side='left', padx=5)
        
        # Buttons
        buttons_frame = tk.Frame(self.title_bar, bg='#2e2e2e')
        buttons_frame.pack(side='right', padx=5)
        
        self.capture_btn = tk.Button(buttons_frame, text="Capture", command=self.on_capture, 
                                   bg='#404040', fg='white', relief='flat')
        self.capture_btn.pack(side='left', padx=2)
        
        self.close_btn = tk.Button(buttons_frame, text="✕", command=self.on_quit, 
                                 bg='#404040', fg='white', relief='flat', width=3)
        self.close_btn.pack(side='left', padx=2)
        
        # Text area
        self.text_frame = tk.Frame(self.container, bg='black')
        self.text_frame.pack(fill='both', expand=True)
        
        self.text_area = tk.Text(self.text_frame, 
            wrap='word',
            bg='black', 
            fg='white',
            font=('Arial', 22, 'bold'),
            padx=10,
            pady=10
        )
        self.text_area.pack(fill='both', expand=True)
        
        # Initialize drag variables
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # Set minimum window size
        self.min_width = 200
        self.min_height = 100
        
        # Make window semi-transparent when not focused
        self.window.bind('<FocusIn>', self.on_focus_in)
        self.window.bind('<FocusOut>', self.on_focus_out)
        
        # Add resize bindings
        self.window.bind('<Button-3>', self.start_resize)
        self.window.bind('<B3-Motion>', self.on_resize)

    def start_drag(self, event):
        self.drag_start_x = event.x_root - self.window.winfo_x()
        self.drag_start_y = event.y_root - self.window.winfo_y()

    def on_drag(self, event):
        x = event.x_root - self.drag_start_x
        y = event.y_root - self.drag_start_y
        self.window.geometry(f"+{x}+{y}")

    def start_resize(self, event):
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        self.initial_width = self.window.winfo_width()
        self.initial_height = self.window.winfo_height()

    def on_resize(self, event):
        width_diff = event.x_root - self.drag_start_x
        height_diff = event.y_root - self.drag_start_y
        
        new_width = max(self.min_width, self.initial_width + width_diff)
        new_height = max(self.min_height, self.initial_height + height_diff)
        
        self.window.geometry(f"{new_width}x{new_height}")

    def on_focus_in(self, event):
        self.window.attributes('-alpha', 1.0)

    def on_focus_out(self, event):
        self.window.attributes('-alpha', 0.8)

    def on_capture(self):
        self.set_status("Capturing Text...")
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(tk.END, "Capturing Text...")
        self.window.update()
        self.on_capture_callback()

    def on_quit(self):
        self.on_quit_callback()

    def set_status(self, status):
        self.title_label.config(text=status)
        self.window.update()

    def update_text(self, text):
        self.text_area.delete(1.0, tk.END)
        cleaned_text = ' '.join(text.split())
        self.text_area.insert(tk.END, cleaned_text)
        self.set_status("Translation Result")

    def save_position(self):
        config = self.config_manager.config
        config['layout']['result_window'].update({
            'width': self.window.winfo_width(),
            'height': self.window.winfo_height(),
            'x': self.window.winfo_x(),
            'y': self.window.winfo_y()
        })
        with open(self.config_manager.config_file, 'w') as f:
            json.dump(config, f, indent=4)

class MinimalistOCRBox:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.window_config_file = "window_position.json"
        self.dev_logs_dir = "dev_logs"
        self.dev_images_dir = os.path.join(self.dev_logs_dir, "images")
        self.dev_data_file = os.path.join(self.dev_logs_dir, "capture_data.json")
        
        if self.config_manager.config.get('dev_mode', False):
            os.makedirs(self.dev_images_dir, exist_ok=True)
            
            if os.path.exists(self.dev_data_file):
                with open(self.dev_data_file, 'r', encoding='utf-8') as f:
                    self.capture_data = json.load(f)
            else:
                self.capture_data = []
        
        # Create main window
        self.root = tk.Tk()
        self.root.withdraw()
        
        # Create the bounding box window
        self.box_window = tk.Toplevel(self.root)
        self.box_window.attributes('-topmost', True)
        self.box_window.overrideredirect(True)
        self.box_window.wm_attributes('-transparentcolor', 'black')
        
        # Load window position
        self.load_window_position()
        
        # Create canvas
        self.canvas = tk.Canvas(
            self.box_window, 
            highlightthickness=0,
            bg='black'
        )
        self.canvas.pack(fill='both', expand=True)
        
        # Create result window
        self.result_window = ResultWindow(
            self.config_manager,
            self.capture_area,
            self.quit_application
        )
        
        # Initialize drag variables
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.window_start_x = 0
        self.window_start_y = 0
        self.resize_edge = None
        self.resize_margin = 15
        
        # Bind events
        self.canvas.bind('<Button-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.canvas.bind('<Configure>', self.on_configure)
        
        # Draw initial border
        self.draw_border()
        
        # Start config check timer
        self.check_config_updates()

    def load_window_position(self):
        try:
            if os.path.exists(self.window_config_file):
                with open(self.window_config_file, 'r') as f:
                    pos = json.load(f)
                    self.box_window.geometry(f"{pos['width']}x{pos['height']}+{pos['x']}+{pos['y']}")
            else:
                screen_width = self.box_window.winfo_screenwidth()
                screen_height = self.box_window.winfo_screenheight()
                initial_width = 400
                initial_height = 200
                x = (screen_width - initial_width) // 2
                y = (screen_height - initial_height) // 2
                self.box_window.geometry(f"{initial_width}x{initial_height}+{x}+{y}")
        except Exception as e:
            print(f"Error loading window position: {e}")

    def save_window_position(self):
        try:
            pos = {
                'width': self.box_window.winfo_width(),
                'height': self.box_window.winfo_height(),
                'x': self.box_window.winfo_x(),
                'y': self.box_window.winfo_y()
            }
            with open(self.window_config_file, 'w') as f:
                json.dump(pos, f)
        except Exception as e:
            print(f"Error saving window position: {e}")

    def check_config_updates(self):
        if self.config_manager.check_update():
            pass
        self.root.after(1000, self.check_config_updates)

    def draw_border(self):
        self.canvas.delete("border")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        
        self.canvas.create_rectangle(
            2, 2, w-2, h-2,
            outline="#00FF00",
            width=4,
            tags="border"
        )
        
        handle_size = 8
        corners = [(0, 0), (w, 0), (0, h), (w, h)]
        
        for x, y in corners:
            self.canvas.create_rectangle(
                x - handle_size, y - handle_size,
                x + handle_size, y + handle_size,
                fill="#00FF00",
                outline="#FFFFFF",
                width=2,
                tags="border"
            )

    def get_resize_edge(self, x, y):
        w = self.box_window.winfo_width()
        h = self.box_window.winfo_height()
        m = self.resize_margin
        
        edges = []
        if x < m: edges.append('left')
        if x > w - m: edges.append('right')
        if y < m: edges.append('top')
        if y > h - m: edges.append('bottom')
        
        return edges

    def on_press(self, event):
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        self.window_start_x = self.box_window.winfo_x()
        self.window_start_y = self.box_window.winfo_y()
        self.resize_edge = self.get_resize_edge(event.x, event.y)

    def on_drag(self, event):
        dx = event.x_root - self.drag_start_x
        dy = event.y_root - self.drag_start_y
        
        if self.resize_edge:
            x = self.box_window.winfo_x()
            y = self.box_window.winfo_y()
            w = self.box_window.winfo_width()
            h = self.box_window.winfo_height()
            
            if 'right' in self.resize_edge:
                w = max(100, w + dx)
            if 'bottom' in self.resize_edge:
                h = max(100, h + dy)
            if 'left' in self.resize_edge:
                if w - dx > 100:
                    x += dx
                    w -= dx
            if 'top' in self.resize_edge:
                if h - dy > 100:
                    y += dy
                    h -= dy
            
            self.box_window.geometry(f"{w}x{h}+{x}+{y}")
            self.drag_start_x = event.x_root
            self.drag_start_y = event.y_root
        else:
            new_x = self.window_start_x + dx
            new_x = self.window_start_x + dx
            new_y = self.window_start_y + dy
            self.box_window.geometry(f"+{new_x}+{new_y}")

    def on_release(self, event):
        self.resize_edge = None
        self.save_window_position()

    def on_configure(self, event):
        self.draw_border()

    def capture_area(self):
        # Hide result window temporarily
        self.result_window.window.withdraw()
        self.box_window.update()
        
        # Capture the area
        x = self.box_window.winfo_x()
        y = self.box_window.winfo_y()
        w = self.box_window.winfo_width()
        h = self.box_window.winfo_height()
        
        self.box_window.after(100)
        
        screenshot = PIL.ImageGrab.grab(bbox=(x, y, x+w, h+y))
        
        # Show result window again
        self.result_window.window.deiconify()
        
        try:
            # Initialize capture data
            capture_entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "image_path": None,
                "detected_text": "",
                "translated_text": ""
            }

            # Save image if dev_mode is enabled
            if self.config_manager.config.get('dev_mode', False):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                image_filename = f"capture_{timestamp}.png"
                image_path = os.path.join(self.dev_images_dir, image_filename)
                screenshot.save(image_path)
                capture_entry["image_path"] = image_path

            # OCR Process
            text = pytesseract.image_to_string(screenshot)
            text = text.strip()
            capture_entry["detected_text"] = text
            
            if not text:
                self.result_window.update_text("No Text Detected")
                if self.config_manager.config.get('dev_mode', False):
                    self.capture_data.append(capture_entry)
                    self.save_dev_data()
                return
            
            # Translation Process
            self.result_window.set_status("Translating...")
            self.result_window.text_area.delete(1.0, tk.END)
            self.result_window.text_area.insert(tk.END, "Translating...")
            self.result_window.window.update()
            
            config = self.config_manager.config['translation']
            translator = GoogleTranslator(
                source=config['source'],
                target=config['target']
            )
            translated = translator.translate(text)
            capture_entry["translated_text"] = translated
            
            # Save dev data if enabled
            if self.config_manager.config.get('dev_mode', False):
                self.capture_data.append(capture_entry)
                self.save_dev_data()
            
            self.log_translation(text, translated)
            self.result_window.update_text(translated)
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.result_window.update_text(error_msg)
            if self.config_manager.config.get('dev_mode', False):
                capture_entry["error"] = error_msg
                self.capture_data.append(capture_entry)
                self.save_dev_data()

    def save_dev_data(self):
        """Save development mode capture data to JSON file"""
        if self.config_manager.config.get('dev_mode', False):
            try:
                with open(self.dev_data_file, 'w', encoding='utf-8') as f:
                    json.dump(self.capture_data, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"Error saving dev data: {e}")

    def log_translation(self, original, translated):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"""
=== {timestamp} ===
Original: {original}
Translation: {translated}
"""
        with open("translation_log.txt", "a", encoding="utf-8") as f:
            f.write(log_entry)

    def quit_application(self):
        self.save_window_position()
        self.result_window.save_position()
        if self.config_manager.config.get('dev_mode', False):
            self.save_dev_data()
        self.root.quit()
        sys.exit()

    def run(self):
        print("=== OCR Translator ===")
        print("Use 'Capture' button or press capture area")
        print("Use '✕' button to quit")
        print("Translations are being logged to 'translation_log.txt'")
        if self.config_manager.config.get('dev_mode', False):
            print("Dev mode is enabled - saving captures to dev_logs/")
        print("Config can be edited in 'config.json'")
        self.root.mainloop()

if __name__ == "__main__":
    box = MinimalistOCRBox()
    box.run()