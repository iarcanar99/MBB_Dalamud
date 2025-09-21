import tkinter as tk
from tkinter import ttk
from appearance import appearance_manager


def is_valid_hotkey(hotkey):
    hotkey = hotkey.lower()
    valid_keys = set("abcdefghijklmnopqrstuvwxyz0123456789")
    valid_functions = set(
        ["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12"]
    )
    valid_modifiers = set(["ctrl", "alt", "shift"])

    parts = hotkey.split("+")

    if len(parts) == 1:
        return parts[0] in valid_keys or parts[0] in valid_functions

    if len(parts) > 1:
        modifiers = parts[:-1]
        key = parts[-1]
        return all(mod in valid_modifiers for mod in modifiers) and (
            key in valid_keys or key in valid_functions
        )

    return False


class SimplifiedHotkeyUI:
    """UI แสดงการตั้งค่าคีย์ลัดแบบเรียบง่าย ออกแบบใหม่เพื่อหลีกเลี่ยงปัญหาทางเทคนิค"""

    def __init__(self, parent, settings, update_callback):
        self.parent = parent
        self.settings = settings
        self.callback = update_callback
        self.window = None
        self.x = None
        self.y = None
        self.is_showing = False
        self._temp_message = None

        # StringVars for hotkey entries
        self.toggle_ui_var = tk.StringVar()
        self.start_stop_var = tk.StringVar()
        self.previous_dialog_var = tk.StringVar()
        self.previous_dialog_key_var = tk.StringVar()

    def open(self):
        """เปิดหน้าต่าง Hotkey UI"""
        try:
            if not self.window or not self.window.winfo_exists():
                self.create_window()
                self.load_current_hotkeys()
                self.position_window()
            else:
                self.window.deiconify()
                self.position_window()

            self.window.lift()
            self.is_showing = True

        except Exception as e:
            print(f"Error opening window: {e}")
            self.show_temp_message(f"เกิดข้อผิดพลาด: {str(e)}", 2000, "#E74C3C")

    def close(self):
        """ปิดหน้าต่าง Hotkey UI"""
        try:
            if self.window and self.window.winfo_exists():
                self.window.destroy()
                self.window = None
                self.is_showing = False
            else:
                self.window = None
                self.is_showing = False
        except Exception as e:
            print(f"Error closing window: {e}")

    def create_window(self):
        """สร้างหน้าต่าง Hotkey UI"""
        try:
            # ทำลายหน้าต่างเก่าถ้ามี
            if self.window and self.window.winfo_exists():
                self.window.destroy()

            self.window = tk.Toplevel(self.parent)
            self.window.title("Hotkey Settings")
            self.window.geometry("340x280")
            self.window.overrideredirect(True)
            appearance_manager.apply_style(self.window)

            # เพิ่ม event เมื่อปิดหน้าต่าง
            self.window.protocol("WM_DELETE_WINDOW", self.close)

            # Create UI elements
            title_label = tk.Label(
                self.window,
                text="ตั้งค่า Hotkey",
                bg=appearance_manager.bg_color,
                fg="#00FFFF",
                font=("IBM Plex Sans Thai Medium", 12, "bold"),
            )
            title_label.pack(pady=(10, 5))

            # Toggle UI entry
            toggle_frame = tk.Frame(self.window, bg=appearance_manager.bg_color)
            toggle_frame.pack(fill=tk.X, padx=10, pady=5)
            tk.Label(
                toggle_frame,
                text="Toggle UI:",
                bg=appearance_manager.bg_color,
                fg="white",
                font=("IBM Plex Sans Thai Medium", 10),
            ).pack(side=tk.LEFT)
            self.toggle_ui_entry = self.create_hotkey_entry(
                toggle_frame, self.toggle_ui_var, "Toggle UI:"
            )
            self.toggle_ui_entry.pack(side=tk.RIGHT, padx=5)

            # Start/Stop entry
            start_frame = tk.Frame(self.window, bg=appearance_manager.bg_color)
            start_frame.pack(fill=tk.X, padx=10, pady=5)
            tk.Label(
                start_frame,
                text="Start/Stop:",
                bg=appearance_manager.bg_color,
                fg="white",
                font=("IBM Plex Sans Thai Medium", 10),
            ).pack(side=tk.LEFT)
            self.start_stop_entry = self.create_hotkey_entry(
                start_frame, self.start_stop_var, "Start/Stop:"
            )
            self.start_stop_entry.pack(side=tk.RIGHT, padx=5)

            # Force translate entry
            previous_frame = tk.Frame(self.window, bg=appearance_manager.bg_color)
            previous_frame.pack(fill=tk.X, padx=10, pady=5)
            tk.Label(
                previous_frame,
                text="Previous:",
                bg=appearance_manager.bg_color,
                fg="white",
                font=("IBM Plex Sans Thai Medium", 10),
            ).pack(side=tk.LEFT)
            self.previous_dialog_entry = self.create_hotkey_entry(
                previous_frame, self.previous_dialog_var, "Previous:"
            )
            self.previous_dialog_entry.pack(side=tk.RIGHT, padx=5)

            # Force translate key entry
            previous_key_frame = tk.Frame(self.window, bg=appearance_manager.bg_color)
            previous_key_frame.pack(fill=tk.X, padx=10, pady=5)
            tk.Label(
                previous_key_frame,
                text="Previous Key:",
                bg=appearance_manager.bg_color,
                fg="white",
                font=("IBM Plex Sans Thai Medium", 10),
            ).pack(side=tk.LEFT)
            self.previous_dialog_key_entry = self.create_hotkey_entry(
                previous_key_frame, self.previous_dialog_key_var, "Previous Key:"
            )
            self.previous_dialog_key_entry.pack(side=tk.RIGHT, padx=5)

            # Buttons
            button_frame = tk.Frame(self.window, bg=appearance_manager.bg_color)
            button_frame.pack(pady=10)

            self.default_button = tk.Button(
                button_frame,
                text="Default",
                command=self.reset_to_default,
                bg="#404040",
                fg="white",
                font=("Nasalization Rg", 10),
                width=8,
            )
            self.default_button.pack(side=tk.LEFT, padx=5)

            self.save_button = tk.Button(
                button_frame,
                text="Save",
                command=self.save_hotkeys,
                bg="#404040",
                fg="white",
                font=("Nasalization Rg", 10),
                width=8,
            )
            self.save_button.pack(side=tk.LEFT, padx=5)

            # Close button
            close_button = tk.Button(
                self.window,
                text="X",
                command=self.close,
                bg="#404040",
                fg="white",
                font=("Nasalization Rg", 8),
                width=2,
            )
            close_button.place(x=5, y=5)

            # Window movement
            self.window.bind("<Button-1>", self.start_move)
            self.window.bind("<ButtonRelease-1>", self.stop_move)
            self.window.bind("<B1-Motion>", self.do_move)

        except Exception as e:
            print(f"Error creating window: {e}")

    def load_current_hotkeys(self):
        """โหลดค่า hotkey ปัจจุบัน"""
        self.toggle_ui_var.set(self.settings.get_shortcut("toggle_ui", "alt+h"))
        self.start_stop_var.set(
            self.settings.get_shortcut("start_stop_translate", "f9")
        )
        self.previous_dialog_var.set(
            self.settings.get_shortcut("previous_dialog", "r-click")
        )
        self.previous_dialog_key_var.set(
            self.settings.get_shortcut("previous_dialog_key", "f10")
        )

    def save_hotkeys(self):
        """บันทึกค่าคีย์ลัดทั้งหมด"""
        try:
            # ดึงค่าจาก entry
            toggle_ui = self.toggle_ui_var.get().lower()
            start_stop = self.start_stop_var.get().lower()
            previous_dialog = self.previous_dialog_var.get().lower()
            previous_dialog_key = self.previous_dialog_key_var.get().lower()

            # ตรวจสอบความถูกต้อง
            valid_toggleui = is_valid_hotkey(toggle_ui)
            valid_startstop = is_valid_hotkey(start_stop)
            valid_previous = previous_dialog == "r-click" or is_valid_hotkey(
                previous_dialog
            )
            valid_previous_key = is_valid_hotkey(previous_dialog_key)

            # ถ้าถูกต้องทั้งหมด
            if valid_toggleui and valid_startstop and valid_previous and valid_previous_key:
                # บันทึกค่าลง settings
                self.settings.set_shortcut("toggle_ui", toggle_ui)
                self.settings.set_shortcut("start_stop_translate", start_stop)
                self.settings.set_shortcut("previous_dialog", previous_dialog)
                self.settings.set_shortcut("previous_dialog_key", previous_dialog_key)

                # ปรับปุ่ม save
                self.save_button.config(text="✓ Saved")

                # ใช้ callback ถ้ามี
                if self.callback:
                    self.callback()

                # แสดงข้อความแจ้งเตือนแบบลอย
                self.show_temp_message("บันทึกคีย์ลัดเรียบร้อยแล้ว!", 1500, "#1E8449")

                # กำหนดเวลารีเซ็ตปุ่ม
                self.window.after(2000, lambda: self.save_button.config(text="Save"))
            else:
                # แสดงข้อความแจ้งเตือนกรณีไม่ถูกต้อง
                self.show_temp_message("กรุณากรอกคีย์ลัดที่ถูกต้อง", 2000, "#E74C3C")
        except Exception as e:
            # แสดงข้อความแจ้งเตือนกรณีเกิดข้อผิดพลาด
            self.show_temp_message(f"เกิดข้อผิดพลาด: {str(e)}", 2000, "#E74C3C")

    def reset_to_default(self):
        """รีเซ็ตค่าเป็นค่าเริ่มต้น"""
        self.toggle_ui_var.set("alt+l")
        self.start_stop_var.set("f9")
        self.previous_dialog_var.set("r-click")
        self.previous_dialog_key_var.set("f10")

        # อัพเดต entries
        if hasattr(self, "toggle_ui_entry"):
            self.toggle_ui_entry.delete(0, tk.END)
            self.toggle_ui_entry.insert(0, "alt+l")
        if hasattr(self, "start_stop_entry"):
            self.start_stop_entry.delete(0, tk.END)
            self.start_stop_entry.insert(0, "f9")
        if hasattr(self, "previous_dialog_entry"):
            self.previous_dialog_entry.delete(0, tk.END)
            self.previous_dialog_entry.insert(0, "r-click")
        if hasattr(self, "previous_dialog_key_entry"):
            self.previous_dialog_key_entry.delete(0, tk.END)
            self.previous_dialog_key_entry.insert(0, "f10")

        # แสดงข้อความยืนยัน
        self.show_temp_message("รีเซ็ตเป็นค่าเริ่มต้นแล้ว", 1500, "#2980B9")

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        self.x = None
        self.y = None

    def do_move(self, event):
        if self.x is not None and self.y is not None:
            deltax = event.x - self.x
            deltay = event.y - self.y
            x = self.window.winfo_x() + deltax
            y = self.window.winfo_y() + deltay
            self.window.geometry(f"+{x}+{y}")

    def create_hotkey_entry(self, frame, variable, label_text):
        """สร้าง Entry สำหรับ hotkey พร้อมการจัดการ events"""
        entry = tk.Entry(
            frame,
            textvariable=variable,
            width=12,
            bg="#333333",
            fg="#00FFFF",
            font=("Consolas", 12),
            justify="center",
        )

        def on_entry_click(event):
            """เมื่อคลิกที่ Entry"""
            entry.select_range(0, tk.END)
            entry.focus_set()

        def on_entry_key(event):
            """จัดการเมื่อกดปุ่มใดๆ"""
            if event.keysym == "Escape":
                # ยกเลิกการแก้ไขและคืนค่าเดิม
                entry.delete(0, tk.END)
                entry.insert(0, self.get_original_value(label_text))
                entry.select_clear()
                self.window.focus_set()
                return "break"

            elif event.keysym == "Return":
                # บันทึกค่าและออกจากโหมดแก้ไข
                self.save_single_hotkey(label_text, entry.get())
                entry.select_clear()
                self.window.focus_set()
                return "break"

            # อนุญาตให้พิมพ์ได้เฉพาะตัวอักษรที่กำหนด
            valid_keys = {
                "Control_L",
                "Alt_L",
                "Shift_L",
                "F1",
                "F2",
                "F3",
                "F4",
                "F5",
                "F6",
                "F7",
                "F8",
                "F9",
                "F10",
                "F11",
                "F12",
            }
            if event.keysym not in valid_keys and len(event.char) == 1:
                if not event.char.isalnum():
                    return "break"

        def on_focus_out(event):
            """เมื่อ focus ออกจาก Entry"""
            entry.select_clear()
            # คืนค่าเดิมถ้าไม่ได้กด Enter
            if not hasattr(entry, "value_confirmed"):
                entry.delete(0, tk.END)
                entry.insert(0, self.get_original_value(label_text))

        # ผูก events
        entry.bind("<FocusIn>", on_entry_click)
        entry.bind("<Key>", on_entry_key)
        entry.bind("<FocusOut>", on_focus_out)

        return entry

    def get_original_value(self, label_text):
        """รับค่าเดิมตาม label"""
        if "Toggle UI" in label_text:
            return self.settings.get_shortcut("toggle_ui", "alt+h")
        elif "Start/Stop" in label_text:
            return self.settings.get_shortcut("start_stop_translate", "f9")
        elif "Previous Key" in label_text:
            return self.settings.get_shortcut("previous_dialog_key", "f10")
        elif "Previous" in label_text:
            return self.settings.get_shortcut("previous_dialog", "r-click")
        return ""

    def save_single_hotkey(self, label_text, value):
        """บันทึกคีย์ลัดเดี่ยว"""
        try:
            if "Toggle UI" in label_text:
                self.settings.set_shortcut("toggle_ui", value.lower())
            elif "Start/Stop" in label_text:
                self.settings.set_shortcut("start_stop_translate", value.lower())
            elif "Previous Key" in label_text:
                self.settings.set_shortcut("previous_dialog_key", value.lower())
            elif "Previous" in label_text:
                self.settings.set_shortcut("previous_dialog", value.lower())

            if self.callback:
                self.callback()

            # แสดงข้อความสำเร็จชั่วคราว
            self.show_temp_message("บันทึกแล้ว!", 1000, "#1E8449")

        except Exception as e:
            # แสดงข้อความแจ้งเตือนกรณีเกิดข้อผิดพลาด
            self.show_temp_message(f"เกิดข้อผิดพลาด: {str(e)}", 2000, "#E74C3C")

    def show_temp_message(self, message, duration=1500, color="#1E8449", font_size=10):
        """แสดงข้อความชั่วคราวด้านล่างของหน้าต่าง

        Args:
            message: ข้อความที่ต้องการแสดง
            duration: ระยะเวลาที่แสดง (ms)
            color: สีพื้นหลัง (success: #1E8449, error: #E74C3C)
            font_size: ขนาดตัวอักษร
        """
        # ลบข้อความเก่า ถ้ามี
        if hasattr(self, "_temp_message") and self._temp_message is not None:
            try:
                self._temp_message.destroy()
            except:
                pass

        # สร้างข้อความใหม่
        self._temp_message = tk.Label(
            self.window,
            text=message,
            bg=color,
            fg="white",
            font=("IBM Plex Sans Thai Medium", font_size),
            padx=10,
            pady=5,
            relief=tk.RAISED,
        )
        self._temp_message.place(relx=0.5, rely=0.9, anchor="center")

        # กำหนดเวลาให้หายไป
        self.window.after(duration, self._hide_temp_message)

    def _hide_temp_message(self):
        """ซ่อนข้อความชั่วคราว"""
        if hasattr(self, "_temp_message") and self._temp_message is not None:
            self._temp_message.destroy()
            self._temp_message = None

    def position_window(self):
        """จัดตำแหน่งหน้าต่างให้อยู่ด้านขวาของ settings"""
        if self.parent and self.window:
            # รับตำแหน่งและขนาดของ parent (settings window)
            parent_x = self.parent.winfo_x()
            parent_y = self.parent.winfo_y()
            parent_width = self.parent.winfo_width()

            # กำหนดตำแหน่งใหม่
            new_x = parent_x + parent_width + 10  # ห่างจากขอบขวา 10 pixels
            new_y = parent_y  # ความสูงเดียวกับ parent

            self.window.geometry(f"+{new_x}+{new_y}")
