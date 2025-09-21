import tkinter as tk
from tkinter import ttk, messagebox
import logging
from appearance import appearance_manager
from advance_ui import AdvanceUI
from settings import Settings, is_valid_hotkey
from simplified_hotkey_ui import SimplifiedHotkeyUI  # เพิ่มบรรทัดนี้


class HotkeyUI:
    def __init__(self, parent, settings, apply_settings_callback, update_hotkeys_callback):
        self.parent = parent
        self.settings = settings
        self.apply_settings_callback = apply_settings_callback
        self.update_hotkeys_callback = update_hotkeys_callback
        self.settings_window = None
        self.settings_visible = False
        self.ocr_toggle_callback = None
        self.advance_ui = None
        
        # เปลี่ยนจาก self.hotkey_ui เป็น self.simplified_hotkey_ui
        self.hotkey_ui = None  # ตัวเก่า - คงไว้ชั่วคราว
        self.simplified_hotkey_ui = None  # ตัวใหม่
        
        self.create_settings_window()

    def show(self):
        """แสดงหน้าต่าง HotkeyUI"""
        try:
            if self.hotkey_window is None or not self.hotkey_window.winfo_exists():
                self.create_hotkey_window()
                # ตั้งค่า size เริ่มต้นที่แน่นอน
                self.hotkey_window.geometry("340x320")
                
            # แสดงหน้าต่าง
            self.hotkey_window.deiconify()
            self.hotkey_window.attributes("-topmost", True)
            self.hotkey_window.lift()
            
            # รอให้หน้าต่างแสดงเสร็จก่อน
            self.hotkey_window.update_idletasks()
            
            # โหลดค่า hotkeys ปัจจุบัน
            self.load_current_hotkeys()
            
            # บังคับให้อัพเดต Entry widgets โดยตรง
            self.hotkey_window.after(50, self.force_update_entries)
            
            return self.hotkey_window
        except Exception as e:
            print(f"Error showing hotkey window: {e}")
            return None

    def create_hotkey_window(self):
        self.hotkey_window = tk.Toplevel(self.parent)
        self.hotkey_window.title("Hotkey Settings")
        self.hotkey_window.geometry("340x320")  # เพิ่มขนาดให้ใหญ่กว่าเดิม
        self.hotkey_window.overrideredirect(True)
        self.hotkey_window.resizable(True, True)  # อนุญาตให้ขยายขนาดได้
        appearance_manager.apply_style(self.hotkey_window)

        # ปรับขนาดฟอนต์ให้ใหญ่ขึ้น
        title_label = tk.Label(
            self.hotkey_window,
            text="ตั้งค่า Hotkey",
            bg=appearance_manager.bg_color,
            fg="#00FFFF",  # สีฟ้าเพื่อเน้นหัวข้อ
            font=("IBM Plex Sans Thai Medium", 12, "bold"),
            justify=tk.CENTER,
        )
        title_label.pack(pady=(10, 5))

        description_label = tk.Label(
            self.hotkey_window,
            text="พิมพ์ตัวอักษรคีย์ลัดที่ต้องการ\nแล้วกด save",
            bg=appearance_manager.bg_color,
            fg="white",
            font=("IBM Plex Sans Thai Medium", 10),
            justify=tk.LEFT,
        )
        description_label.pack(pady=5, padx=15)

        # Toggle UI
        toggle_frame = tk.Frame(self.hotkey_window, bg=appearance_manager.bg_color)
        toggle_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(
            toggle_frame,
            text="Toggle UI:",
            bg=appearance_manager.bg_color,
            fg=appearance_manager.fg_color,
        ).pack(side=tk.LEFT)
        self.toggle_ui_entry = tk.Entry(toggle_frame, textvariable=self.toggle_ui_var)
        self.toggle_ui_entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)

        # Start/Stop
        start_stop_frame = tk.Frame(self.hotkey_window, bg=appearance_manager.bg_color)
        start_stop_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(
            start_stop_frame,
            text="Start/Stop Translate:",
            bg=appearance_manager.bg_color,
            fg=appearance_manager.fg_color,
        ).pack(side=tk.LEFT)
        self.start_stop_entry = tk.Entry(
            start_stop_frame, textvariable=self.start_stop_var
        )
        self.start_stop_entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)

        # เพิ่ม Previous Dialog (R-Click)
        previous_frame = tk.Frame(self.hotkey_window, bg=appearance_manager.bg_color)
        previous_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(
            previous_frame,
            text="Previous Dialog:",
            bg=appearance_manager.bg_color,
            fg=appearance_manager.fg_color,
        ).pack(side=tk.LEFT)
        self.previous_dialog_entry = tk.Entry(
            previous_frame, textvariable=self.previous_dialog_hotkey_var
        )
        self.previous_dialog_entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)

        # Default และ Save Button
        button_frame = tk.Frame(self.hotkey_window, bg=appearance_manager.bg_color)
        button_frame.pack(pady=10)
        
        # เพิ่มปุ่ม Default
        default_button = appearance_manager.create_styled_button(
            button_frame, "Default", self.reset_to_default
        )
        default_button.pack(side=tk.LEFT, padx=5)
        
        # ปุ่ม Save
        self.save_button = appearance_manager.create_styled_button(
            button_frame, "Save", self.save_hotkeys
        )
        self.save_button.pack(side=tk.LEFT, padx=5)

        # ปุ่มปิด
        close_button = appearance_manager.create_styled_button(
            self.hotkey_window, "X", self.close
        )
        close_button.place(x=5, y=5, width=20, height=20)

        # Bindings
        self.hotkey_window.bind("<Button-1>", self.start_move)
        self.hotkey_window.bind("<ButtonRelease-1>", self.stop_move)
        self.hotkey_window.bind("<B1-Motion>", self.do_move)

    def adjust_hotkey_ui(self):
        """ปรับปรุงการแสดงผลของ Hotkey UI ให้มีขนาดคงที่"""
        try:
            # กำหนดขนาดคงที่สำหรับหน้าต่าง
            FIXED_WIDTH = 340
            FIXED_HEIGHT = 320
            
            # ปรับขนาดช่องกรอกให้กว้างขึ้น และกำหนดสีพื้นหลังชัดเจน
            entry_config = {
                "width": 12,
                "bg": "#333333",
                "fg": "#00FFFF",  # สีฟ้าเพื่อให้เห็นได้ชัดเจน
                "font": ("Consolas", 12),
                "insertbackground": "white",  # สีของ cursor
                "justify": "center"
            }
            
            # อัพเดทช่องกรอกทั้งหมด
            if hasattr(self, "toggle_ui_entry"):
                self.toggle_ui_entry.config(**entry_config)
            
            if hasattr(self, "start_stop_entry"):
                self.start_stop_entry.config(**entry_config)
            
            if hasattr(self, "previous_dialog_entry"):
                self.previous_dialog_entry.config(**entry_config)
            
            # กำหนดขนาดคงที่ - สำคัญมาก เพื่อป้องกันการขยายขนาดซ้ำซ้อน
            self.hotkey_window.geometry(f"{FIXED_WIDTH}x{FIXED_HEIGHT}")
            print(f"Fixed HotkeyUI window size to {FIXED_WIDTH}x{FIXED_HEIGHT}")
            
        except Exception as e:
            print(f"Error adjusting hotkey UI: {e}")
    
    def print_current_hotkeys(self):
        """แสดงค่าปัจจุบันของ hotkeys เพื่อการ debug"""
        print("\n=== Current Hotkey Settings ===")
        print(f"Variable values:")
        print(f"- toggle_ui_var: '{self.toggle_ui_var.get()}'")
        print(f"- start_stop_var: '{self.start_stop_var.get()}'")
        print(f"- previous_dialog_hotkey_var: '{self.previous_dialog_hotkey_var.get()}'")
        
        print("\nEntry values:")
        if hasattr(self, "toggle_ui_entry"):
            print(f"- toggle_ui_entry: '{self.toggle_ui_entry.get()}'")
        if hasattr(self, "start_stop_entry"):
            print(f"- start_stop_entry: '{self.start_stop_entry.get()}'")
        if hasattr(self, "previous_dialog_entry"):
            print(f"- previous_dialog_entry: '{self.previous_dialog_entry.get()}'")
        
        print("\nSettings values:")
        print(f"- toggle_ui: '{self.settings.get_shortcut('toggle_ui', 'alt+l')}'")
        print(f"- start_stop_translate: '{self.settings.get_shortcut('start_stop_translate', 'f9')}'")
        print(f"- previous_dialog: '{self.settings.get_shortcut('previous_dialog', 'r-click')}'")
        print("==============================\n")
    
    def reset_to_default(self):
        """รีเซ็ตค่าเป็นค่าเริ่มต้น"""
        self.toggle_ui_var.set("alt+l")
        self.start_stop_var.set("f9")
        self.previous_dialog_hotkey_var.set("r-click")

    def load_current_hotkeys(self):
        """โหลดค่า hotkey ปัจจุบันและอัพเดตแสดงใน Entry fields"""
        try:
            # ดึงค่าจาก settings โดยมีค่าเริ่มต้นถ้าไม่พบค่า
            toggle_ui = self.settings.get_shortcut("toggle_ui", "alt+l")
            start_stop = self.settings.get_shortcut("start_stop_translate", "f9")
            previous_dialog = self.settings.get_shortcut("previous_dialog", "r-click")
            
            print(f"DEBUG: Loading hotkeys - Toggle: '{toggle_ui}', Start/Stop: '{start_stop}', Previous: '{previous_dialog}'")
            
            # กรณีค่าเป็นค่าว่าง ใช้ค่าเริ่มต้น
            if not toggle_ui: toggle_ui = "alt+l"
            if not start_stop: start_stop = "f9"
            if not previous_dialog: previous_dialog = "r-click"
            
            # อัพเดต StringVar สำหรับผูกกับ Entry
            self.toggle_ui_var.set(toggle_ui)
            self.start_stop_var.set(start_stop)
            self.previous_dialog_hotkey_var.set(previous_dialog)
            
            # อัพเดต Entry widgets โดยตรง
            if hasattr(self, "toggle_ui_entry"):
                self.toggle_ui_entry.delete(0, tk.END)
                self.toggle_ui_entry.insert(0, toggle_ui)
            
            if hasattr(self, "start_stop_entry"):
                self.start_stop_entry.delete(0, tk.END)
                self.start_stop_entry.insert(0, start_stop)
            
            if hasattr(self, "previous_dialog_entry"):
                self.previous_dialog_entry.delete(0, tk.END)
                self.previous_dialog_entry.insert(0, previous_dialog)
            
            print(f"Successfully loaded hotkeys: Toggle UI: {toggle_ui}, Start/Stop: {start_stop}, Previous: {previous_dialog}")
        except Exception as e:
            print(f"Error loading hotkeys: {e}")

    def force_update_entries(self):
        """บังคับอัพเดตค่าใน Entry โดยตรงโดยไม่พึ่ง StringVar"""
        # ข้อมูลจาก settings
        toggle_ui = self.settings.get_shortcut("toggle_ui", "alt+l")
        start_stop = self.settings.get_shortcut("start_stop_translate", "f9")
        previous_dialog = self.settings.get_shortcut("previous_dialog", "r-click")
        
        # อัพเดตโดยตรงไปที่ Entry widgets
        if hasattr(self, "toggle_ui_entry") and self.toggle_ui_entry.winfo_exists():
            self.toggle_ui_entry.delete(0, tk.END)
            self.toggle_ui_entry.insert(0, toggle_ui)
            print(f"Updated toggle_ui_entry directly: '{toggle_ui}'")
        
        if hasattr(self, "start_stop_entry") and self.start_stop_entry.winfo_exists():
            self.start_stop_entry.delete(0, tk.END)
            self.start_stop_entry.insert(0, start_stop)
            print(f"Updated start_stop_entry directly: '{start_stop}'")
        
        if hasattr(self, "previous_dialog_entry") and self.previous_dialog_entry.winfo_exists():
            self.previous_dialog_entry.delete(0, tk.END)
            self.previous_dialog_entry.insert(0, previous_dialog)
            print(f"Updated previous_dialog_entry directly: '{previous_dialog}'")
        
        self.toggle_ui_var.set(toggle_ui)
        self.start_stop_var.set(start_stop)
        self.previous_dialog_hotkey_var.set(previous_dialog)        
        
        # หลังจากอัพเดต entries เสร็จแล้ว ให้ปรับขนาดหน้าต่างให้คงที่
        self.hotkey_window.after(100, self.adjust_hotkey_ui)

    def save_hotkeys(self):
        """บันทึกค่า hotkey ใหม่"""
        toggle_ui = self.toggle_ui_var.get().lower()
        start_stop = self.start_stop_var.get().lower()
        previous_dialog = self.previous_dialog_hotkey_var.get().lower()
        
        # ตรวจสอบความถูกต้องของค่า
        valid_toggleui = is_valid_hotkey(toggle_ui)
        valid_startstop = is_valid_hotkey(start_stop)
        # ยกเว้น r-click ซึ่งเป็นค่าพิเศษ
        valid_previous = previous_dialog == "r-click" or is_valid_hotkey(previous_dialog)

        if valid_toggleui and valid_startstop and valid_force:
            self.settings.set_shortcut("toggle_ui", toggle_ui)
            self.settings.set_shortcut("start_stop_translate", start_stop)
            self.settings.set_shortcut("previous_dialog", previous_dialog)
            
            self.save_button.config(text="Saved!")
            print(
                f"New hotkeys saved: Toggle UI: {toggle_ui}, Start/Stop: {start_stop}, Previous: {previous_dialog}"
            )
            # แสดงข้อความชั่วคราวเมื่อบันทึกสำเร็จ
            feedback = tk.Label(
                self.hotkey_window,
                text="บันทึกคีย์ลัดเรียบร้อยแล้ว!",
                bg="#1E8449",
                fg="white",
                font=("IBM Plex Sans Thai Medium", 10),
                padx=10,
                pady=5,
            )
            feedback.place(relx=0.5, rely=0.9, anchor="center")
            
            # ซ่อนข้อความหลังจาก 2 วินาที
            self.hotkey_window.after(2000, feedback.destroy)
            
            # คืนค่าปุ่มกลับเป็นปกติ
            self.hotkey_window.after(
                2000, 
                lambda: self.save_button.config(text="Save")
            )
            
            # เรียกใช้ callback เพื่ออัพเดต hotkeys ในระบบ
            if self.update_hotkeys_callback:
                self.update_hotkeys_callback()
        else:
            messagebox.showerror("Invalid Hotkey", "กรุณากรอกคีย์ลัดที่ถูกต้อง")

    def close(self):
        if self.hotkey_window and self.hotkey_window.winfo_exists():
            self.save_button.config(text="Save")
            self.hotkey_window.withdraw()

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        self.x = None
        self.y = None

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.hotkey_window.winfo_x() + deltax
        y = self.hotkey_window.winfo_y() + deltay
        self.hotkey_window.geometry(f"+{x}+{y}")


class SettingsUI:
    def __init__(self, parent, settings, apply_settings_callback, update_hotkeys_callback):
        self.parent = parent
        self.settings = settings
        self.apply_settings_callback = apply_settings_callback
        self.update_hotkeys_callback = update_hotkeys_callback
        self.settings_window = None
        self.settings_visible = False
        self.ocr_toggle_callback = None
        self.advance_ui = None

        # ประกาศ attribute สำหรับ SimplifiedHotkeyUI
        self.simplified_hotkey_ui = None  

        self.create_settings_window()

    def create_settings_window(self):
        self.settings_window = tk.Toplevel(self.parent)
        self.settings_window.overrideredirect(True)
        appearance_manager.apply_style(self.settings_window)
        self.create_settings_ui()
        self.settings_window.withdraw()

    def set_ocr_toggle_callback(self, callback):
        self.ocr_toggle_callback = callback
        if self.advance_ui:
            self.advance_ui.settings_ui.ocr_toggle_callback = callback

    def open_settings(self, parent_x, parent_y, parent_width):
        """Open settings window at specified position relative to parent"""
        x = parent_x + parent_width + 20
        y = parent_y
        self.settings_window.geometry(f"+{x}+{y}")

        self.transparency_scale.set(int(self.settings.get("transparency") * 100))
        self.font_size_var.set(str(self.settings.get("font_size")))
        self.font_var.set(self.settings.get("font"))
        self.width_entry.delete(0, tk.END)
        self.width_entry.insert(0, str(self.settings.get("width")))
        self.height_entry.delete(0, tk.END)
        self.height_entry.insert(0, str(self.settings.get("height")))
        self.previous_dialog_var.set(self.settings.get("enable_previous_dialog"))
        self.auto_hide_var.set(self.settings.get("enable_auto_hide"))
        self.ui_toggle_var.set(self.settings.get("enable_ui_toggle"))

        self.settings_window.deiconify()
        self.settings_window.lift()
        self.settings_window.attributes("-topmost", True)
        self.settings_visible = True

        if hasattr(self, "advance_button"):
            self.advance_button.config(text="Screen/API")
        if hasattr(self, "hotkey_button"):
            self.hotkey_button.config(text="HotKey")

    def close_settings(self):
        self.settings_window.withdraw()
        self.settings_visible = False
        
        # ปิด advance_ui ถ้ามี
        if self.advance_ui:
            self.advance_ui.close()
        
        # ปิด SimplifiedHotkeyUI
        if self.simplified_hotkey_ui:
            self.simplified_hotkey_ui.close()
        
        self.hotkey_button.config(text="HotKey")

    def create_toggle_switch(self, text, variable):
        frame = tk.Frame(self.settings_window, bg=appearance_manager.bg_color)
        frame.pack(pady=5, padx=10, fill=tk.X)

        label = tk.Label(
            frame,
            text=text,
            bg=appearance_manager.bg_color,
            fg=appearance_manager.fg_color,
        )
        label.pack(side=tk.LEFT)

        switch = ttk.Checkbutton(frame, style="Switch.TCheckbutton", variable=variable)
        switch.pack(side=tk.RIGHT)

    def toggle_hotkey_ui(self):
        """เปิด/ปิดหน้าต่าง Hotkey UI"""
        try:
            logging.debug("Toggle hotkey UI called...")
            
            # สร้าง instance ใหม่ถ้ายังไม่มี
            if not hasattr(self, "simplified_hotkey_ui") or self.simplified_hotkey_ui is None:
                logging.debug("Creating new SimplifiedHotkeyUI instance...")
                self.simplified_hotkey_ui = SimplifiedHotkeyUI(
                    self.settings_window,
                    self.settings,
                    self.update_hotkeys_callback
                )
            
            # ตรวจสอบว่าหน้าต่างมีอยู่จริงและกำลังแสดงอยู่หรือไม่
            has_window = (hasattr(self.simplified_hotkey_ui, 'window') and 
                        self.simplified_hotkey_ui.window is not None)
            window_exists = False
            
            if has_window:
                try:
                    window_exists = self.simplified_hotkey_ui.window.winfo_exists()
                except tk.TclError:  # จัดการกรณีหน้าต่างถูกทำลายไปแล้ว
                    window_exists = False
            
            # ตรวจสอบสถานะการแสดงผล
            logging.debug(f"Window status: has_window={has_window}, exists={window_exists}, is_showing={self.simplified_hotkey_ui.is_showing}")
            
            if self.simplified_hotkey_ui.is_showing:
                logging.debug("Closing hotkey UI...")
                self.simplified_hotkey_ui.close()
                self.hotkey_button.config(text="HotKey")
            else:
                logging.debug("Opening hotkey UI...")
                # กรณีพบ window ที่ไม่ถูกต้อง ให้ทำความสะอาดก่อน
                if has_window and not window_exists:
                    self.simplified_hotkey_ui.window = None
                    
                self.simplified_hotkey_ui.open()
                self.position_hotkey_window()
                self.hotkey_button.config(text="Close Hotkeys")
                    
        except Exception as e:
            logging.error(f"Error in toggle_hotkey_ui: {e}")
            messagebox.showerror("Error", f"เกิดข้อผิดพลาดในการเปิด Hotkey UI: {e}")

    def position_hotkey_window(self):
        """จัดตำแหน่งหน้าต่าง Hotkey UI"""
        if self.simplified_hotkey_ui and self.simplified_hotkey_ui.window:
            settings_x = self.settings_window.winfo_x()
            settings_y = self.settings_window.winfo_y()
            settings_width = self.settings_window.winfo_width()
            
            # กำหนดตำแหน่งด้านขวาของ settings window
            hotkey_x = settings_x + settings_width + 10
            hotkey_y = settings_y
            
            self.simplified_hotkey_ui.window.geometry(f"+{hotkey_x}+{hotkey_y}")

    def create_settings_ui(self):
        appearance_manager.create_styled_label(
            self.settings_window, text="Transparency:"
        ).pack(pady=5)
        # แก้ไขส่วนของ transparency_scale
        transparency_frame, self.transparency_scale = (
            appearance_manager.create_styled_scale(
                self.settings_window, from_=0, to=100, orient=tk.HORIZONTAL
            )
        )
        transparency_frame.pack(pady=5, padx=10, fill=tk.X)

        appearance_manager.create_styled_label(
            self.settings_window, text="Font Size:"
        ).pack(pady=5)
        font_sizes = [16, 20, 24, 28, 32, 36]
        self.font_size_var = tk.StringVar()
        self.font_size_dropdown = appearance_manager.create_styled_combobox(
            self.settings_window, values=font_sizes, textvariable=self.font_size_var
        )
        self.font_size_dropdown.pack(pady=5, padx=10, fill=tk.X)

        self.transparency_value = self.transparency_scale.get()

        appearance_manager.create_styled_label(self.settings_window, text="Font:").pack(
            pady=5
        )
        thai_fonts = [
            "Fc Minimal",
            "Bai Jamjuree SemiBold",
            "PK Nakhon Sawan Regular Demo",
            "MaliThin",
            "Sarabun",
            "Noto Sans Thai Looped",
            "IBM Plex Sans Thai Medium",
        ]
        self.font_var = tk.StringVar()
        self.font_dropdown = appearance_manager.create_styled_combobox(
            self.settings_window, values=thai_fonts, textvariable=self.font_var
        )
        self.font_dropdown.pack(pady=5, padx=10, fill=tk.X)

        appearance_manager.create_styled_label(
            self.settings_window, text="Window Width (px):"
        ).pack(pady=5)
        self.width_entry = tk.Entry(self.settings_window, width=10)
        self.width_entry.pack(pady=5, padx=10, fill=tk.X)

        appearance_manager.create_styled_label(
            self.settings_window, text="Window Height (px):"
        ).pack(pady=5)
        self.height_entry = tk.Entry(self.settings_window, width=10)
        self.height_entry.pack(pady=5, padx=10, fill=tk.X)

        apply_button = appearance_manager.create_styled_button(
            self.settings_window, "Apply", self.apply_settings
        )
        apply_button.pack(pady=20)

        self.previous_dialog_var = tk.BooleanVar()
        self.auto_hide_var = tk.BooleanVar()
        self.ui_toggle_var = tk.BooleanVar()

        # StringVar variables for hotkeys
        self.toggle_ui_var = tk.StringVar()
        self.start_stop_var = tk.StringVar()
        self.previous_dialog_hotkey_var = tk.StringVar()

        self.create_toggle_switch(
            "Enable 'R-click' to Previous Dialog", self.previous_dialog_var
        )
        self.create_toggle_switch("Enable Auto-hide on Movement", self.auto_hide_var)
        self.create_toggle_switch("Enable UI Toggle", self.ui_toggle_var)

        self.shortcut_label = tk.Label(
            self.settings_window,
            text="Shortcuts:\nALT+H: Toggle UI\nF9: Start/Stop Translation",
            bg=appearance_manager.bg_color,
            fg=appearance_manager.fg_color,
            font=("IBM Plex Sans Thai Medium", 8, "bold"),
            justify=tk.LEFT,
        )
        self.shortcut_label.pack(side=tk.BOTTOM, pady=10)

        self.credit_label = tk.Label(
            self.settings_window,
            text="Magicite-Babel v3.1 beta, \nDeveloped by iarcanar",
            bg=appearance_manager.bg_color,
            fg=appearance_manager.fg_color,
            font=("IBM Plex Sans Thai Medium", 10, "normal"),
            justify=tk.CENTER,
        )
        self.credit_label.pack(side=tk.BOTTOM, pady=5)

        self.advance_button = appearance_manager.create_styled_button(
            self.settings_window, "Screen/API", self.open_advance_ui
        )
        self.advance_button.pack(pady=16)

        self.hotkey_button = appearance_manager.create_styled_button(
            self.settings_window, "HotKey", self.toggle_hotkey_ui
        )
        self.hotkey_button.pack(pady=16)

        close_button = appearance_manager.create_styled_button(
            self.settings_window, "X", self.close_settings
        )
        close_button.place(x=5, y=5, width=20, height=20)

        self.settings_window.bind("<Button-1>", self.start_move_settings)
        self.settings_window.bind("<ButtonRelease-1>", self.stop_move_settings)
        self.settings_window.bind("<B1-Motion>", self.do_move_settings)

    def apply_settings(self, new_settings=None):
        """Apply settings with validation"""
        try:
            # กรณีกดปุ่ม Apply จาก settings UI
            if new_settings is None:
                try:
                    transparency = max(
                        0.1, min(1.0, float(self.transparency_scale.get()) / 100)
                    )
                    font_size = int(self.font_size_var.get())
                    font = str(self.font_var.get()).strip()
                    width = max(100, min(2000, int(self.width_entry.get())))
                    height = max(100, min(1000, int(self.height_entry.get())))

                    enable_force = bool(self.previous_dialog_var.get())
                    enable_auto_hide = bool(self.auto_hide_var.get())
                    enable_ui_toggle = bool(self.ui_toggle_var.get())

                    settings_dict = {
                        "transparency": transparency,
                        "font_size": font_size,
                        "font": font,
                        "width": width,
                        "height": height,
                        "enable_previous_dialog": enable_force,
                        "enable_auto_hide": enable_auto_hide,
                        "enable_ui_toggle": enable_ui_toggle,
                    }

                    for key, value in settings_dict.items():
                        self.settings.set(key, value)

                    if self.apply_settings_callback:
                        self.apply_settings_callback(self.settings)
                        logging.info("Settings applied successfully")

                    return True, None

                except ValueError as e:
                    raise ValueError(f"Invalid input value: {str(e)}")

            # กรณีเรียกจาก advance settings
            else:
                logging.info("Applying advanced settings")
                if not isinstance(new_settings, dict):
                    raise ValueError("New settings must be a dictionary")

                old_model = self.settings.get("api_parameters", {}).get("model", "")
                new_model = new_settings.get("api_parameters", {}).get("model", "")

                if self.apply_settings_callback:
                    self.apply_settings_callback(new_settings)

                # Log model change
                if old_model != new_model:
                    print(f"\n=== API Model Changed ===")
                    print(f"Previous model: {old_model}")
                    print(f"New model: {new_model}")
                    print(f"Parameters: {self.settings.get_api_parameters()}")
                    print("=====================\n")
                    logging.info(f"API model changed from {old_model} to {new_model}")

                return True, None

        except Exception as e:
            error_msg = f"Error applying settings: {str(e)}"
            logging.error(error_msg)
            return False, error_msg

    def open_advance_ui(self):
        if (
            self.advance_ui is None
            or not hasattr(self.advance_ui, "advance_window")
            or not self.advance_ui.advance_window.winfo_exists()
        ):
            self.advance_ui = AdvanceUI(
                self.settings_window, self.settings, self.apply_settings_callback, None
            )
        self.advance_ui.open()

    def start_move_settings(self, event):
        self.settings_x = event.x
        self.settings_y = event.y

    def stop_move_settings(self, event):
        self.settings_x = None
        self.settings_y = None

    def do_move_settings(self, event):
        if hasattr(self, "settings_x") and hasattr(self, "settings_y"):
            deltax = event.x - self.settings_x
            deltay = event.y - self.settings_y
            x = self.settings_window.winfo_x() + deltax
            y = self.settings_window.winfo_y() + deltay
            self.settings_window.geometry(f"+{x}+{y}")

            # เคลื่อนย้าย SimplifiedHotkeyUI แทนที่ HotkeyUI เดิม
            if (
                hasattr(self, "simplified_hotkey_ui") and 
                self.simplified_hotkey_ui and 
                hasattr(self.simplified_hotkey_ui, "window") and
                self.simplified_hotkey_ui.window and 
                self.simplified_hotkey_ui.window.winfo_exists()
            ):
                window = self.simplified_hotkey_ui.window
                # ตำแหน่งด้านขวา
                hotkey_x = x + self.settings_window.winfo_width() + 10
                hotkey_y = y + 50
                window.geometry(f"+{hotkey_x}+{hotkey_y}")

