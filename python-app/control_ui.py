import threading
import time
import tkinter as tk
from tkinter import messagebox
from PIL import ImageTk, Image, ImageDraw, ImageFilter
import logging
import json
import os
from appearance import appearance_manager
from settings import Settings

# เพิ่ม imports สำหรับการทำขอบโค้งมน
import win32gui
import win32con
import win32api
from ctypes import windll, byref, sizeof, c_int

logging.basicConfig(level=logging.INFO)

print("Loading control_ui.py")


class Control_UI:
    def __init__(self, root, previous_dialog_callback, switch_area, settings, parent_callback=None, trigger_temporary_area_display_callback=None, on_close_callback=None):
        self.root = root
        self.previous_dialog_callback = previous_dialog_callback
        self.switch_area_callback = switch_area
        self.settings = settings
        self.parent_root = None
        self.parent_callback = parent_callback  # เก็บ callback สำหรับแจ้งเตือน mbb.py
        self.on_close_callback = on_close_callback  # เก็บ callback สำหรับเมื่อปิดหน้าต่าง
        
        # ตัวแปรสำหรับ auto-hide functionality
        self.auto_hide_timer = None
        self.is_closing = False  # ป้องกันการปิดซ้ำ
        
        # เพิ่มตัวแปรสำหรับติดตามสถานะการแปล
        self.is_translating = False

        # ระบบควบคุมการ hover force translate
        self._force_hover_active = False  # สถานะว่ากำลัง hover อยู่หรือไม่
        self._force_last_triggered_time = 0  # เวลาล่าสุดที่ trigger force
        self._force_cooldown_period = 1.0  # ระยะเวลาคูลดาวน์ (1 วินาที)
        
        # เพิ่มตัวแปรสำหรับเก็บ tooltip ของ Manual Force Mode
        self.manual_force_tooltip = None
        
        # โหลด theme ก่อนใช้
        self.theme = appearance_manager.get_current_theme()

        # เพิ่มตัวแปรเก็บสถานะ click_translate
        self.click_translate_var = tk.BooleanVar()
        self.click_translate_var.set(settings.get("enable_click_translate", False))
        
        # *** ลบโค้ดการสร้าง self.click_translate_switch ตรงนี้ออก ***
        # เพราะจะไปสร้างใน setup_buttons แทน

        # เพิ่มตัวแปรสำหรับการควบคุม CPU Limit
        self.cpu_limit = self.settings.get("cpu_limit", 80)

        # เก็บ callback ใหม่ที่รับเข้ามา
        self.trigger_temporary_area_display_callback = trigger_temporary_area_display_callback

        # ตัวแปรสำหรับการเคลื่อนที่หน้าต่าง
        self.x = None
        self.y = None

        # เพิ่มตัวแปรสำหรับ preset system
        self.current_preset = self.settings.get("current_preset", 1)
        self.max_presets = 5
        self.presets = self.settings.get_all_presets()
        self.settings.set("current_preset", self.current_preset)

        # โหลดค่า current_area จาก settings
        initial_area_str = self.settings.get("current_area", "A+B")
        initial_areas = initial_area_str.split("+")
        self.area_states = {
            "A": "A" in initial_areas,
            "B": "B" in initial_areas,
            "C": "C" in initial_areas,
        }
        if not any(self.area_states.values()):
            self.area_states["A"] = True
            initial_area_str = "A"
            self.settings.set("current_area", initial_area_str)

        self.ensure_preset_area_consistency()

        self.ui_cache = {
            "position_x": None,
            "position_y": None,
            "current_area": initial_area_str,
        }

        self.setup_window()
        self.setup_buttons()  # สร้าง toggle switch ตรงนี้
        self.setup_bindings()

        self.load_preset(self.current_preset)

        self.root.update_idletasks()
        self.apply_rounded_corners()

        try:
            hwnd = windll.user32.GetParent(self.root.winfo_id())
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            style &= ~win32con.WS_CAPTION
            style &= ~win32con.WS_THICKFRAME
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

            rgnw = self.root.winfo_width()
            rgnh = self.root.winfo_height()
            if rgnw > 0 and rgnh > 0:
                region = win32gui.CreateRoundRectRgn(0, 0, rgnw, rgnh, 15, 15)
                win32gui.SetWindowRgn(hwnd, region, True)
            else:
                logging.warning("Could not apply rounded corners, window size is zero.")
        except Exception as e:
            logging.error(f"Error applying rounded corners in __init__: {e}")

        self.update_button_highlights()
        # Auto-save is always active, no need to track unsaved changes

        if self.trigger_temporary_area_display_callback is None:
            logging.warning("Temporary area display callback not provided to Control_UI.")
        if self.parent_callback is None:
            logging.warning("Control_UI: parent_callback is not provided. Cannot notify main app of mode changes.")

    def create_toggle_switch(self, parent, text, variable, command, width=40, height=20):
        """สร้าง Toggle Switch ที่ดูดีและใช้งานง่ายด้วย Canvas"""
        # ตรวจสอบว่า theme โหลดหรือยัง ถ้ายัง ให้ใช้ค่า fallback
        current_theme = getattr(self, 'theme', {})
        bg_color = current_theme.get("bg", "#1a1a1a")

        container = tk.Frame(parent, bg=bg_color)

        if text:
            label = tk.Label(
                container,
                text=text,
                bg=bg_color,
                fg=current_theme.get("fg", "white"),
                font=("IBM Plex Sans Thai Medium", 9), # ปรับ font ให้เหมาะสม
                anchor="w"
            )
            label.pack(side=tk.LEFT, padx=(0, 5))

        canvas = tk.Canvas(
            container,
            width=width,
            height=height,
            bg=bg_color,
            highlightthickness=0,
            cursor="hand2"
        )
        canvas.pack(side=tk.LEFT) # หรือ RIGHT ตามต้องการ

        # สีและขนาด
        padding = 2
        knob_radius = (height - 2 * padding) / 2
        # ป้องกันค่าติดลบถ้า height เล็กไป
        knob_diameter = max(0, height - 2 * padding)
        off_x = padding
        on_x = width - knob_diameter - padding
        bg_on_color = current_theme.get("success", "#4CAF50")
        bg_off_color = current_theme.get("button_inactive_bg", "#555555")
        knob_color = current_theme.get("fg", "white")
        bg_outline = current_theme.get("border", "#444444")

        # --- วาดพื้นหลัง (Track) ---
        try:
            # ส่วนโค้งด้านซ้าย
            canvas.create_oval(
                padding, padding,
                height - padding, height - padding, # ใช้ height สำหรับเส้นผ่านศูนย์กลาง
                fill=bg_off_color, outline=bg_outline, tags="track"
            )
            # ส่วนโค้งด้านขวา
            canvas.create_oval(
                width - height + padding, padding, # เลื่อน x ไปด้านขวา
                width - padding, height - padding, # ใช้ height สำหรับเส้นผ่านศูนย์กลาง
                fill=bg_off_color, outline=bg_outline, tags="track"
            )
            # ส่วนสี่เหลี่ยมตรงกลาง
            canvas.create_rectangle(
                height / 2, padding, # เริ่มจากกึ่งกลางส่วนโค้งซ้าย
                width - height / 2, height - padding, # สิ้นสุดที่กึ่งกลางส่วนโค้งขวา
                fill=bg_off_color, outline=bg_off_color, tags="track" # ใช้สีเดียวกับ oval เพื่อให้ดูเชื่อมกัน
            )
        except tk.TclError as e_draw:
             logging.error(f"Error drawing toggle switch track: {e_draw}. Maybe invalid dimensions?")
             # อาจจะวาดสี่เหลี่ยมง่ายๆแทนถ้า error
             canvas.create_rectangle(0,0, width, height, fill=bg_off_color, tags="track")


        # --- วาดตัวเลื่อน (Knob) ---
        try:
            knob = canvas.create_oval(
                off_x, padding,
                off_x + knob_diameter, padding + knob_diameter,
                fill=knob_color, outline=knob_color, tags="knob"
            )
        except tk.TclError as e_knob:
            logging.error(f"Error drawing toggle switch knob: {e_knob}")
            knob = None # กำหนดเป็น None ถ้าสร้างไม่ได้

        # --- ฟังก์ชันภายในสำหรับอัพเดท UI ---
        def update_switch_ui(is_on):
            if not knob: return # ออกถ้าสร้าง knob ไม่สำเร็จ
            try:
                target_x = on_x if is_on else off_x
                current_coords = canvas.coords(knob)
                if not current_coords:
                    # logging.warning("Could not get knob coordinates for toggle switch update.")
                    # ลองวาดใหม่ที่ตำแหน่งเป้าหมายเลย
                     canvas.coords(knob, target_x, padding, target_x + knob_diameter, padding + knob_diameter)
                else:
                    current_x = current_coords[0]
                    # ตรวจสอบว่าต้องย้ายหรือไม่ ป้องกันการคำนวณที่ผิดพลาด
                    if abs(target_x - current_x) > 0.1: # ใช้ค่า threshold เล็กน้อย
                        canvas.move(knob, target_x - current_x, 0)

                # เปลี่ยนสีพื้นหลัง track
                bg_color = bg_on_color if is_on else bg_off_color
                outline_color = bg_color if is_on else bg_outline
                canvas.itemconfigure("track", fill=bg_color, outline=outline_color)
            except tk.TclError as e_update:
                 logging.error(f"Error updating toggle switch UI: {e_update}")
            except Exception as e_gen_update:
                 logging.error(f"Generic error updating toggle switch UI: {e_gen_update}")


        # --- ฟังก์ชันภายในสำหรับ Toggle ---
        def toggle(event=None):
            new_state = not variable.get()
            variable.set(new_state)
            update_switch_ui(new_state)
            if command:
                try:
                    command(new_state)
                except Exception as e_cmd:
                    logging.error(f"Error executing toggle switch command: {e_cmd}")

        # --- ผูก Event ---
        canvas.bind("<Button-1>", toggle)

        # --- ตั้งค่า UI เริ่มต้น ---
        # เรียก update_switch_ui ครั้งแรกเพื่อแสดงสถานะปัจจุบันของ variable
        update_switch_ui(variable.get())

        # --- ทำให้ label คลิกได้ด้วย (ถ้ามี) ---
        if text and 'label' in locals() and label.winfo_exists():
             label.bind("<Button-1>", toggle)
             label.configure(cursor="hand2")

        # --- คืนค่า container ---
        return container
    
    def toggle_click_translate(self, value):
        """จัดการเมื่อมีการเปลี่ยนสถานะ Click Translate mode"""
        # บันทึกค่าใหม่ลงใน settings
        self.settings.set("enable_click_translate", value)
        
        # อัพเดท UI (เช่น เปลี่ยนสี หรือข้อความบนปุ่ม Force)
        force_button = getattr(self, "force_button", None)
        if force_button:
            if value:
                # ถ้าเปิด Click Translate mode ให้เน้นปุ่ม Force ให้ชัดเจนขึ้น
                force_button.config(bg="#e74c3c")  # สีแดงเข้ม
                force_button.config(text="1-CLICK")  # เปลี่ยนเป็น "1-CLICK" เพื่อให้ชัดเจนว่าเป็นโหมด 1-click
            else:
                # ถ้าปิด Click Translate mode ให้กลับไปใช้สีปกติ
                force_button.config(bg=self.theme.get("accent", "#00aaff"))
                force_button.config(text="FORCE")
        
        # แจ้ง parent callback (MBB.py) ถ้ามี
        if self.parent_callback:
            try:
                self.parent_callback("click_translate_mode_changed", value)
            except Exception as e:
                logging.error(f"Error calling parent callback: {e}")
        
        # แจ้ง log การเปลี่ยนแปลง
        mode_str = "ON (1-Click Mode)" if value else "OFF (Auto Mode)"
        logging.info(f"Click Translate mode: {mode_str}")

    def _on_force_button_hover_enter(self, event: tk.Event) -> None:
        """
        จัดการเมื่อ mouse hover เข้าบริเวณปุ่ม Force
        - แสดง visual feedback
        - เรียกใช้ force translate โดยอัตโนมัติและทำงานซ้ำตามระยะเวลาคูลดาวน์
        
        Args:
            event: Mouse enter event
        """
        try:
            # ถ้าไม่ได้อยู่ในสถานะแปล ไม่ทำอะไร
            if not self.is_translating:
                return
                
            # ตั้งค่าสถานะว่ากำลัง hover อยู่
            self._force_hover_active = True
            
            # บันทึกสีเดิมไว้ เผื่อต้องคืนค่ากลับ (ถ้ายังไม่เคยบันทึก)
            if not hasattr(self, "_force_button_original_bg"):
                self._force_button_original_bg = self.force_button.cget("bg")
                self._force_button_original_fg = self.force_button.cget("fg")
                self._force_button_original_relief = self.force_button.cget("relief")
            
            # ตรวจสอบว่าผ่านระยะเวลาคูลดาวน์หรือยัง
            current_time = time.time()
            time_diff = current_time - self._force_last_triggered_time
            
            # ถ้าเพิ่งเข้ามา hover หรือผ่านระยะเวลาคูลดาวน์แล้ว ให้ trigger force translate
            if time_diff >= self._force_cooldown_period:
                # 1. แสดง Visual Feedback - เปลี่ยนสีปุ่มให้เด่นชัด
                highlight_bg = "#e74c3c"  # สีแดงเข้ม หรือใช้ error color จาก theme
                if hasattr(self, "theme") and "error" in self.theme:
                    highlight_bg = self.theme["error"]
                
                self.force_button.configure(
                    bg=highlight_bg,
                    fg="white",
                    relief="sunken"  # ทำให้ดูเหมือนกดปุ่ม
                )
                
                # 2. แสดง feedback ว่ากำลังทำ Force Translate
                self.show_force_feedback()
                
                # 3. เรียกใช้ force translate โดยอัตโนมัติ
                self.safe_previous_dialog()
                
                # 4. บันทึกเวลาที่ trigger ล่าสุด
                self._force_last_triggered_time = current_time
                
                # 5. ตั้ง Timer เพื่อตรวจสอบซ้ำหลังจากผ่านระยะเวลาคูลดาวน์
                # (เฉพาะถ้ายังคง hover อยู่)
                self.root.after(
                    int(self._force_cooldown_period * 1000),  # แปลงเป็นมิลลิวินาที
                    self._check_force_hover_cooldown
                )
                
                logging.info(f"Force triggered by hover. Next available in {self._force_cooldown_period} seconds")
            
        except Exception as e:
            logging.error(f"Error in Force button hover enter: {e}")

    def _check_force_hover_cooldown(self):
        """
        ตรวจสอบว่าถ้ายังคง hover อยู่และผ่านระยะเวลาคูลดาวน์แล้ว ให้ trigger force translate อีกครั้ง
        เมธอดนี้จะถูกเรียกโดย timer หลังจากผ่านระยะเวลาคูลดาวน์
        """
        try:
            # ตรวจสอบว่ายังคง hover อยู่หรือไม่
            if not self._force_hover_active:
                return
            
            # ตรวจสอบว่าผ่านระยะเวลาคูลดาวน์หรือยัง
            current_time = time.time()
            time_diff = current_time - self._force_last_triggered_time
            
            if time_diff >= self._force_cooldown_period:
                # 1. เรียกใช้ force translate อีกครั้ง
                self.safe_previous_dialog()
                
                # 2. บันทึกเวลาที่ trigger ล่าสุด
                self._force_last_triggered_time = current_time
                
                # 3. แสดง feedback ว่ากำลังทำ Force Translate อีกครั้ง
                self.show_force_feedback()
                
                logging.info("Force triggered again after cooldown period")
                
                # 4. ตั้ง Timer อีกครั้งเพื่อตรวจสอบซ้ำ
                self.root.after(
                    int(self._force_cooldown_period * 1000),
                    self._check_force_hover_cooldown
                )
        
        except Exception as e:
            logging.error(f"Error in force hover cooldown check: {e}")
    
    def _on_force_button_hover_leave(self, event: tk.Event) -> None:
        """
        จัดการเมื่อ mouse ออกจากบริเวณปุ่ม Force
        - คืนค่าสถานะปุ่มกลับเป็นปกติ
        - รีเซ็ตสถานะ hover active
        
        Args:
            event: Mouse leave event
        """
        try:
            # รีเซ็ตสถานะ hover เป็น False เสมอ
            self._force_hover_active = False
            
            # คืนค่าสีและสถานะเดิม
            if hasattr(self, "_force_button_original_bg"):
                self.force_button.configure(
                    bg=self._force_button_original_bg,
                    fg=self._force_button_original_fg,
                    relief=self._force_button_original_relief
                )
            else:
                # ถ้าไม่มีการบันทึกสีเดิม ใช้ค่าจาก theme
                self.force_button.configure(
                    bg=self.theme.get("button_bg", "#262637"),
                    fg=self.theme.get("fg", "white"),
                    relief="flat"
                )
                
                # อัพเดตข้อความตามสถานะ Click Translate ด้วย
                if hasattr(self, "click_translate_var") and self.click_translate_var.get():
                    self.force_button.configure(text="1-CLICK")
                else:
                    self.force_button.configure(text="FORCE")
            
            logging.info("Force button hover deactivated")
                    
        except Exception as e:
            logging.error(f"Error in Force button hover leave: {e}")
            # ถึงแม้จะเกิด exception ก็ต้องรีเซ็ตสถานะ
            self._force_hover_active = False

    def show_force_feedback(self):
        """แสดง feedback เมื่อทำการ Force Translate จากการ hover"""
        try:
            # สร้างหน้าต่าง feedback
            feedback = tk.Toplevel(self.root)
            feedback.overrideredirect(True)
            feedback.configure(bg=self.theme.get("bg", "#1a1a1a"))
            feedback.attributes("-alpha", 0.9)
            feedback.attributes("-topmost", True)

            # ใช้สีพื้นหลังจาก theme
            bg_color = self.theme.get("bg", "#1a1a1a")
            border_color = self.theme.get("accent", "#6c5ce7")
            
            # สร้าง Frame หลักพร้อมขอบสี
            outer_frame = tk.Frame(feedback, bg=border_color, padx=1, pady=1)
            outer_frame.pack()
            
            # สร้าง Frame ภายในสำหรับเนื้อหา
            main_frame = tk.Frame(outer_frame, bg=bg_color, padx=15, pady=10)
            main_frame.pack()

            # สร้างข้อความ
            msg_frame = tk.Frame(main_frame, bg=bg_color)
            msg_frame.pack()

            # ไอคอนแฟลช (lightning)
            icon_label = tk.Label(
                msg_frame,
                text="⚡",  # lightning emoji
                fg=self.theme.get("highlight", "#00FFFF"),
                bg=bg_color,
                font=("Segoe UI Emoji", 14, "bold"),
            )
            icon_label.pack(side=tk.LEFT, padx=(0, 5))

            # ข้อความ
            tk.Label(
                msg_frame,
                text="Force Translation!",
                fg=self.theme.get("highlight", "#00FFFF"),
                bg=bg_color,
                font=("Nasalization Rg", 10, "bold"),
            ).pack(side=tk.LEFT)

            # คำนวณตำแหน่ง - ให้อยู่ด้านบนกึ่งกลางของ Control UI
            feedback.update_idletasks()  # จำเป็นต้องเรียกเพื่อให้ได้ขนาดที่ถูกต้อง
            feedback_width = feedback.winfo_width()
            feedback_height = feedback.winfo_height()
            
            # คำนวณตำแหน่งกึ่งกลาง
            x = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - (feedback_width // 2)
            y = self.root.winfo_rooty() - feedback_height - 10  # 10px เหนือ Control UI
            
            # กำหนดตำแหน่ง
            feedback.geometry(f"+{x}+{y}")

            # เอฟเฟกต์ fade-in fade-out
            feedback.attributes("-alpha", 0.0)

            def fade_in():
                for i in range(0, 10):
                    if feedback.winfo_exists():
                        feedback.attributes("-alpha", i / 10)
                        feedback.update()
                        time.sleep(0.02)

            def fade_out():
                for i in range(10, -1, -1):
                    if feedback.winfo_exists():
                        feedback.attributes("-alpha", i / 10)
                        feedback.update()
                        time.sleep(0.02)
                    if feedback.winfo_exists():
                        feedback.destroy()

            # ใช้ Thread แยกสำหรับ fade effect เพื่อไม่ให้ freeze UI
            fade_in_thread = threading.Thread(target=fade_in)
            fade_in_thread.daemon = True
            fade_in_thread.start()
            
            # ตั้งเวลาสำหรับ fade out
            feedback.after(800, lambda: threading.Thread(target=fade_out, daemon=True).start())
            
        except Exception as e:
            logging.error(f"Error showing force feedback: {e}")

    def reset_force_hover_state(self):
        """
        รีเซ็ตสถานะของปุ่ม Force hover
        เรียกใช้เมื่อต้องการรีเซ็ตสถานะแบบบังคับ เช่น เมื่อเปลี่ยนหน้า
        """
        # รีเซ็ตสถานะ hover
        self._force_hover_active = False
        
        # ไม่รีเซ็ต _force_last_triggered_time เพื่อให้คูลดาวน์ยังคงทำงาน
        # แม้จะเปลี่ยนหน้าก็ตาม
        
        logging.info("Force hover state manually reset")
        
        # คืนค่าสถานะปุ่มกลับเป็นปกติด้วย
        if hasattr(self, "force_button") and self.force_button.winfo_exists():
            if hasattr(self, "_force_button_original_bg"):
                self.force_button.configure(
                    bg=self._force_button_original_bg,
                    fg=self._force_button_original_fg,
                    relief=self._force_button_original_relief
                )
            else:
                # ถ้าไม่มีการบันทึกสีเดิม ใช้ค่าจาก theme
                self.force_button.configure(
                    bg=self.theme.get("button_bg", "#262637"),
                    fg=self.theme.get("fg", "white"),
                    relief="flat"
                )
    
    def create_tooltip(self, widget, text):
        """
        สร้าง tooltip แบบง่ายสำหรับ widget
        
        Args:
            widget: Widget ที่ต้องการแสดง tooltip
            text: ข้อความที่จะแสดงใน tooltip
        """
        def on_enter(event):
            # ซ่อน tooltip เก่าก่อน (ถ้ามี)
            self.hide_tooltip()
            
            # สร้าง tooltip window ใหม่
            self.manual_force_tooltip = tk.Toplevel(self.root)
            self.manual_force_tooltip.wm_overrideredirect(True)
            self.manual_force_tooltip.wm_attributes("-topmost", True)
            
            # สีพื้นหลังและขอบ
            bg_color = self.theme.get("bg", "#1a1a1a")
            border_color = self.theme.get("accent", "#6c5ce7")
            
            # สร้าง frame พร้อมขอบ
            border_frame = tk.Frame(self.manual_force_tooltip, bg=border_color, bd=1)
            border_frame.pack(fill="both", expand=True)
            
            # สร้าง label แสดงข้อความ
            label = tk.Label(
                border_frame,
                text=text,
                bg=bg_color,
                fg="white",
                font=("IBM Plex Sans Thai Medium", 10),
                padx=8,
                pady=4,
                justify=tk.LEFT
            )
            label.pack()
            
            # คำนวณตำแหน่ง (ใกล้เมาส์)
            x = self.root.winfo_pointerx() + 10
            y = self.root.winfo_pointery() - 30
            
            # ตรวจสอบไม่ให้ tooltip หลุดจากหน้าจอ
            self.manual_force_tooltip.update_idletasks()
            tooltip_width = self.manual_force_tooltip.winfo_width()
            tooltip_height = self.manual_force_tooltip.winfo_height()
            
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            if x + tooltip_width > screen_width:
                x = screen_width - tooltip_width - 10
            if y < 0:
                y = self.root.winfo_pointery() + 20
            if y + tooltip_height > screen_height:
                y = screen_height - tooltip_height - 10
                
            self.manual_force_tooltip.wm_geometry(f"+{x}+{y}")
        
        def on_leave(event):
            self.hide_tooltip()
        
        # ผูก events
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def hide_tooltip(self):
        """ซ่อน tooltip อย่างง่าย"""
        if self.manual_force_tooltip:
            try:
                self.manual_force_tooltip.destroy()
            except:
                pass
            finally:
                self.manual_force_tooltip = None
    
    def create_circular_button_image(self, original_image, bg_color, hover_color):
        """สร้างรูปภาพปุ่มทรงกลมแบบโมเดิร์น

        Args:
            original_image: รูปภาพเดิม
            bg_color: สีพื้นหลัง
            hover_color: สีเมื่อ hover

        Returns:
            ImageTk.PhotoImage: รูปภาพปุ่มทรงกลม
        """
        try:
            # ขนาดภาพ
            width, height = original_image.size
            size = max(width, height)

            # สร้างรูปภาพใหม่เป็นวงกลม
            new_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

            # วาดวงกลมเป็นพื้นหลัง
            draw = ImageDraw.Draw(new_img)
            draw.ellipse((0, 0, size, size), fill=bg_color)

            # วางรูปภาพเดิมลงตรงกลาง
            offset_x = (size - width) // 2
            offset_y = (size - height) // 2
            new_img.paste(original_image, (offset_x, offset_y), original_image)

            # แปลงเป็น PhotoImage
            return ImageTk.PhotoImage(new_img)
        except Exception as e:
            print(f"Error creating circular button: {e}")
            # ถ้าเกิดข้อผิดพลาด ให้ใช้รูปภาพเดิม
            return ImageTk.PhotoImage(original_image)

    def create_pill_button_image(self, original_image, bg_color, hover_color):
        """สร้างรูปภาพปุ่มทรงยาว (pill shape) แบบโมเดิร์น

        Args:
            original_image: รูปภาพเดิม
            bg_color: สีพื้นหลัง
            hover_color: สีเมื่อ hover

        Returns:
            ImageTk.PhotoImage: รูปภาพปุ่มทรงยาว
        """
        try:
            # ขนาดภาพ
            width, height = original_image.size

            # เพิ่มพื้นที่ขอบ
            padding = 8
            new_width = width + padding * 2
            new_height = height + padding * 2

            # สร้างรูปภาพใหม่
            new_img = Image.new("RGBA", (new_width, new_height), (0, 0, 0, 0))

            # วาดพื้นหลังทรงยาว
            draw = ImageDraw.Draw(new_img)
            radius = new_height // 2  # รัศมีเท่ากับครึ่งหนึ่งของความสูง
            draw.rounded_rectangle(
                (0, 0, new_width, new_height), radius=radius, fill=bg_color
            )

            # วางรูปภาพเดิมลงตรงกลาง
            offset_x = padding
            offset_y = padding
            new_img.paste(original_image, (offset_x, offset_y), original_image)

            # แปลงเป็น PhotoImage
            return ImageTk.PhotoImage(new_img)
        except Exception as e:
            print(f"Error creating pill button: {e}")
            # ถ้าเกิดข้อผิดพลาด ให้ใช้รูปภาพเดิม
            return ImageTk.PhotoImage(original_image)

    def create_rounded_frame(self, frame, radius=15):
        """ทำให้ frame มีขอบโค้งมน

        Args:
            frame: tk.Frame ที่ต้องการทำให้โค้งมน
            radius: รัศมีของขอบโค้ง
        """
        try:
            # รอให้ frame แสดงผล
            frame.update_idletasks()

            # ดึงค่า HWND ของ frame
            hwnd = windll.user32.GetParent(frame.winfo_id())

            # ลบกรอบและหัวข้อ
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            style &= ~win32con.WS_CAPTION
            style &= ~win32con.WS_THICKFRAME
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

            # สร้างภูมิภาค (region) โค้งมน
            width = frame.winfo_width()
            height = frame.winfo_height()
            region = win32gui.CreateRoundRectRgn(0, 0, width, height, radius, radius)

            # กำหนดภูมิภาคให้กับ frame
            win32gui.SetWindowRgn(hwnd, region, True)

            return True
        except Exception as e:
            print(f"Error creating rounded frame: {e}")
            return False

    def create_modern_button(
        self,
        parent,
        text,
        command,
        width=95,
        height=30,
        fg="#ffffff",
        bg=None,
        hover_bg=None,
        font=("Nasalization Rg", 10),
        corner_radius=15,
    ):
        """สร้างปุ่มโมเดิร์นสำหรับ Control UI (ใช้ Colorkey สำหรับ Canvas bg)"""
        # กำหนดค่าสีเริ่มต้นจากธีมปัจจุบันถ้าไม่ได้ระบุมา
        # current_theme_bg = self.theme.get("bg", "#1a1a1a") # ไม่ใช้แล้ว
        colorkey = "#00FF00"  # สีเขียวมะนาว เป็น Colorkey (เลือกสีที่ไม่น่าจะใช้ในดีไซน์)

        if bg is None:
            bg = self.theme.get("button_bg", "#262637")
        if hover_bg is None:
            hover_bg = self.theme.get("accent", "#6c5ce7")

        # สร้าง canvas สำหรับวาดปุ่ม - *** ตั้ง bg เป็น Colorkey และเอาขอบออก ***
        canvas = tk.Canvas(
            parent,
            width=width,
            height=height,
            bg=colorkey,  # *** ตั้งเป็น Colorkey ***
            highlightthickness=0,
            bd=0,
        )

        # วาดรูปทรงปุ่ม (เหมือนเดิม)
        try:
            button_bg_shape = canvas.create_rounded_rectangle(
                0, 0, width, height, radius=corner_radius, fill=bg, outline=""
            )
        except AttributeError:
            print(
                "Error: Canvas missing create_rounded_rectangle. Did appearance.py run?"
            )
            button_bg_shape = canvas.create_rectangle(
                0, 0, width, height, fill=bg, outline=""
            )  # Fallback

        # สร้างข้อความบนปุ่ม (เหมือนเดิม)
        button_text_item = canvas.create_text(
            width // 2, height // 2, text=text, fill=fg, font=font
        )

        # ผูกคำสั่งเมื่อคลิก (เหมือนเดิม)
        if command:
            canvas.bind("<Button-1>", lambda event: command())

        # เพิ่ม tag สำหรับระบุสถานะ hover (เหมือนเดิม)
        canvas._is_hovering = False

        # สร้าง hover effect (เหมือนเดิม)
        def on_enter(event):
            if hasattr(canvas, "selected") and canvas.selected:
                return
            canvas._is_hovering = True
            canvas.itemconfig(button_bg_shape, fill=hover_bg)

        def on_leave(event):
            canvas._is_hovering = False
            if not hasattr(canvas, "selected") or not canvas.selected:
                current_original_bg = getattr(canvas, "original_bg", bg)
                canvas.itemconfig(button_bg_shape, fill=current_original_bg)

        canvas.bind("<Enter>", on_enter)
        canvas.bind("<Leave>", on_leave)

        # เพิ่ม metadata (เหมือนเดิม)
        canvas.selected = False
        canvas.original_bg = bg
        canvas.hover_bg = hover_bg
        canvas.button_bg = button_bg_shape
        canvas.button_text = button_text_item

        # *** ไม่ต้องเรียกใช้ Windows API ที่นี่ เพราะอาจจะยังไม่พร้อม ***
        # *** เราจะไปทำใน update_theme แทน ***

        return canvas

    def _preset_button_hover(self, canvas, is_hover):
        """สร้าง hover effect สำหรับปุ่ม preset

        Args:
            canvas: Canvas ที่เป็นปุ่ม preset
            is_hover: สถานะ hover (True/False)
        """
        # ไม่เปลี่ยนสีถ้าปุ่มนี้กำลังถูกเลือก
        if canvas.selected:
            return

        if is_hover:
            # เอฟเฟกต์เมื่อ hover
            canvas.itemconfig(canvas.circle, fill=self.theme["accent_light"])
            canvas.itemconfig(canvas.text, fill=self.theme["text"])
        else:
            # คืนค่าเริ่มต้น
            canvas.itemconfig(canvas.circle, fill=self.theme["button_bg"])
            canvas.itemconfig(canvas.text, fill=self.theme["text_dim"])

    def ensure_preset_area_consistency(self):
        """
        ตรวจสอบและรักษาความสอดคล้องระหว่าง preset และสถานะพื้นที่
        เพื่อให้มั่นใจว่า preset 1 เป็น A+B เสมอ
        """
        try:
            # ตรวจสอบว่า preset 1 มีข้อมูลหรือไม่
            if len(self.presets) >= 1:
                preset_1 = self.presets[0]

                # ตรวจสอบว่า preset 1 มีพื้นที่ A+B หรือไม่
                if preset_1.get("areas") != "A+B":
                    # ถ้าไม่ใช่ ให้อัพเดตเป็น A+B
                    preset_1["areas"] = "A+B"
                    # บันทึกกลับไปที่ settings
                    self.settings.save_preset(1, "A+B", preset_1.get("coordinates", {}))

                # อัพเดตสถานะพื้นที่ให้ตรงกับ preset 1
                self.area_states["A"] = True
                self.area_states["B"] = True
                self.area_states["C"] = False
            else:
                # ถ้ายังไม่มี preset 1 ให้สร้างใหม่
                default_presets = [
                    {"name": "Preset 1", "areas": "A+B"},
                    {"name": "Preset 2", "areas": "C"},
                    {"name": "Preset 3", "areas": "A"},
                    {"name": "Preset 4", "areas": "B"},
                    {"name": "Preset 5", "areas": "B+C"},
                ]
                self.settings.set("area_presets", default_presets)
                self.presets = default_presets

                # อัพเดตสถานะพื้นที่
                self.area_states["A"] = True
                self.area_states["B"] = True
                self.area_states["C"] = False

        except Exception as e:
            print(f"Error ensuring preset-area consistency: {e}")
            # ในกรณีที่เกิดข้อผิดพลาด ให้ใช้ค่าเริ่มต้น
            self.area_states["A"] = True
            self.area_states["B"] = True
            self.area_states["C"] = False

    def setup_window(self):
        """ตั้งค่าหน้าต่าง UI (แก้ไขปัญหาเส้นขอบ)"""
        self.root.title("Control Panel")
        # ลองปรับความสูงลดลงเล็กน้อยก่อน เนื่องจากเอา Speed Control ออก
        self.root.geometry("280x260")
        self.root.overrideredirect(True)
        self.root.attributes("-alpha", 0.95)
        self.root.attributes("-topmost", True)
        
        # FIX: เพิ่มการลบ border ทั้งหมด
        self.root.configure(highlightthickness=0, bd=0, relief="flat")
        self.root.update_idletasks()  # Force immediate update

        # ใช้ค่าโดยตรงจาก appearance_manager ในการสร้างธีม
        # (ส่วนนี้เหมือนเดิม)
        self.theme = {
            "bg": appearance_manager.bg_color,  # ใช้สีพื้นหลังหลักที่โหลดมา
            "accent": appearance_manager.get_accent_color(),
            "accent_light": appearance_manager.get_theme_color("accent_light"),
            "secondary": appearance_manager.get_theme_color("secondary"),
            "button_bg": appearance_manager.get_theme_color("button_bg"),
            "text": "#ffffff",
            "text_dim": "#b2b2b2",
            "highlight": appearance_manager.get_highlight_color(),
            "error": "#e74c3c",
        }

        # สร้าง main frame - ปรับปรุงเพื่อแก้ไขปัญหาเส้นขอบด้านบน
        self.main_frame = tk.Frame(
            self.root,
            bg=self.theme["bg"],
            highlightthickness=0,
            bd=0,  # เอาขอบของ main_frame ออก
            relief="flat"  # FIX: เพิ่ม relief flat
        )
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)  # ลด padding เป็น 0

        # สร้างเฟรมส่วนหัวแยกอย่างชัดเจน - ปรับปรุงเพื่อลบเส้นขอบด้านบน
        header_frame = tk.Frame(
            self.main_frame, bg=self.theme["bg"], height=35, bd=0, highlightthickness=0
        )
        header_frame.pack(fill=tk.X, pady=(0, 8))  # ลด pady บน

        # ชื่อหน้าต่าง
        self.title_label = tk.Label(
            header_frame,
            text="Control UI",
            font=("Nasalization Rg", 16, "bold"),
            bg=self.theme["bg"],
            fg=self.theme["accent"],
        )
        self.title_label.pack(pady=(5, 0))  # เพิ่ม padding บนเล็กน้อย

        # สร้างเส้นคั่น
        self.header_separator = tk.Frame(
            self.main_frame, height=1, bg=self.theme["accent_light"]  # ลดความหนาเส้นคั่น
        )
        self.header_separator.pack(fill=tk.X, padx=15, pady=(0, 10))

        # จัดวางตำแหน่งหน้าต่าง (เหมือนเดิม)
        self.position_below_main_ui()

    def load_preset(self, preset_number=None):
        """
        โหลด preset ตามหมายเลขที่กำหนด หรือใช้ preset ปัจจุบัน
        และอัพเดท UI รวมถึงแจ้ง MBB (คล้าย _complete_preset_switch)

        Args:
            preset_number: หมายเลข preset (1-5) หรือไม่ระบุ (ใช้ค่าปัจจุบัน)
        """
        try:
            # ถ้าไม่ระบุหมายเลข preset ให้ใช้ค่าปัจจุบัน
            if preset_number is None:
                preset_number = self.current_preset

            # ตรวจสอบว่า preset_number อยู่ในช่วงที่ถูกต้อง
            if not (1 <= preset_number <= self.max_presets):
                preset_number = 1  # ถ้าไม่ถูกต้อง ใช้ preset 1

            # ไม่เปลี่ยน current_preset ที่นี่ เพราะอาจเป็นการโหลดเพื่อแสดงผลชั่วคราว
            # หรือถ้าเป็นการโหลดถาวร ควรเรียกผ่าน select_preset/_complete_preset_switch

            # ดึงข้อมูล preset จาก settings
            preset_data = self.settings.get_preset(preset_number)
            if not preset_data:
                logging.error(
                    f"Cannot find preset data for {preset_number} during load_preset"
                )
                preset_data = self.settings.get_preset(1)  # Fallback to preset 1
                if not preset_data:
                    logging.error(
                        "Failed to load even Preset 1 data during load_preset."
                    )
                    return False  # Indicate failure

            # ดึงข้อมูลพื้นที่และพิกัด
            area_config = preset_data.get("areas", "A")
            coordinates = preset_data.get("coordinates", {})

            # *** ส่วนที่แตกต่าง: เราอาจจะแค่ต้องการอัพเดท state และ UI ชั่วคราว ***
            # *** หรือถ้าเป็นการโหลดถาวร ก็ควรทำเหมือน _complete_preset_switch ***

            # --- สมมติว่าเป็นการโหลดเพื่อใช้งานจริง ---
            self.current_preset = (
                preset_number  # ถ้าเป็นการโหลดถาวร ก็ต้องตั้ง current_preset
            )
            self.settings.set("current_preset", self.current_preset)

            # อัพเดตพิกัด (เหมือน _complete_preset_switch)
            if isinstance(coordinates, dict):
                for area, coords in coordinates.items():
                    if isinstance(coords, dict) and all(
                        k in coords for k in ["start_x", "start_y", "end_x", "end_y"]
                    ):
                        self.settings.set_translate_area(
                            coords["start_x"],
                            coords["start_y"],
                            coords["end_x"],
                            coords["end_y"],
                            area,
                        )
                    else:
                        logging.warning(
                            f"Invalid coordinates data for area {area} in preset {preset_number} during load_preset: {coords}"
                        )

            # อัพเดตสถานะการแสดงพื้นที่ใน Control UI ให้ตรงกับ preset
            active_areas = area_config.split("+")
            for area in ["A", "B", "C"]:
                self.area_states[area] = area in active_areas

            # อัพเดต UI ของ Control Panel
            self.update_preset_buttons()
            self.update_button_highlights()

            # แจ้งการเปลี่ยนแปลงพื้นที่ไปยัง MBB.py
            if self.switch_area_callback:
                self.switch_area_callback(active_areas)

            # Auto-save is always active, no need to track unsaved changes

            logging.info(
                f"Loaded preset {preset_number}. Active areas set to: {area_config}"
            )
            return True
            # --- จบส่วนสมมติว่าโหลดถาวร ---

        except Exception as e:
            print(f"Error loading preset: {e}")
            logging.error(f"Error loading preset: {e}")
            # Fallback logic (อาจจะไม่จำเป็นถ้าใช้ _complete_preset_switch)
            for area in ["A", "B", "C"]:
                self.area_states[area] = area in ["A", "B"]
            self.update_button_highlights()
            return False

    def show_preset_switch_feedback(self, old_preset, new_preset):
        """แสดงข้อความแจ้งเตือนเมื่อมีการสลับ preset

        Args:
            old_preset: หมายเลข preset เดิม
            new_preset: หมายเลข preset ใหม่
        """
        try:
            # สร้างหน้าต่างแจ้งเตือน
            feedback = tk.Toplevel(self.root)
            feedback.overrideredirect(True)
            feedback.configure(bg=self.theme["bg"])
            feedback.attributes("-alpha", 0.9)
            feedback.attributes("-topmost", True)

            # สร้าง frame หลักแบบโค้งมน
            main_frame = tk.Frame(feedback, bg=self.theme["bg"], padx=15, pady=10)
            main_frame.pack()

            # สร้างข้อความที่สวยงาม
            msg_frame = tk.Frame(main_frame, bg=self.theme["bg"])
            msg_frame.pack()

            # ดึงชื่อของพื้นที่จาก preset
            old_areas = "unknown"
            new_areas = "unknown"

            if old_preset <= len(self.presets):
                old_areas = self.presets[old_preset - 1].get("areas", "unknown")
            if new_preset <= len(self.presets):
                new_areas = self.presets[new_preset - 1].get("areas", "unknown")
                
            # ดึงชื่อที่จะแสดงของ preset
            old_display_name = self.settings.get_preset_display_name(old_preset)
            new_display_name = self.settings.get_preset_display_name(new_preset)

            # สร้างข้อความแจ้งเตือน
            tk.Label(
                msg_frame,
                text=f"Switched preset",
                fg=self.theme["highlight"],
                bg=self.theme["bg"],
                font=("Nasalization Rg", 10, "bold"),
            ).pack(side=tk.TOP)

            tk.Label(
                msg_frame,
                text=f"{old_display_name} ({old_areas}) → {new_display_name} ({new_areas})",
                fg="#2ecc71",
                bg=self.theme["bg"],
                font=("Nasalization Rg", 9),
            ).pack(side=tk.TOP)

            # คำนวณตำแหน่ง (กลางจอ)
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()

            feedback_width = 220  # กำหนดขนาดของ feedback
            feedback_height = 80

            x = (screen_width - feedback_width) // 2
            y = (screen_height - feedback_height) // 2

            # กำหนดตำแหน่ง
            feedback.geometry(f"{feedback_width}x{feedback_height}+{x}+{y}")

            # เอฟเฟกต์ fade-in fade-out
            feedback.attributes("-alpha", 0.0)

            def fade_in():
                for i in range(0, 10):
                    if feedback.winfo_exists():
                        feedback.attributes("-alpha", i / 10)
                        feedback.update()
                        feedback.after(20)

            def fade_out():
                for i in range(10, -1, -1):
                    if feedback.winfo_exists():
                        feedback.attributes("-alpha", i / 10)
                        feedback.update()
                        feedback.after(20)
                    if feedback.winfo_exists():
                        feedback.destroy()

            fade_in()
            feedback.after(1500, fade_out)  # แสดง 1.5 วินาที
        except Exception as e:
            print(f"Error showing preset switch feedback: {e}")

    def save_preset(self):
        """บันทึก preset ปัจจุบันพร้อมพิกัด"""
        current_areas = self.get_current_area_string()

        # รวบรวมพิกัดของพื้นที่ที่เลือก
        coordinates = {}
        for area in current_areas.split("+"):
            area_coords = self.settings.get_translate_area(area)
            if area_coords:
                coordinates[area] = area_coords

        # บันทึกทั้งพื้นที่และพิกัด
        self.settings.save_preset(self.current_preset, current_areas, coordinates)

        # เพิ่มบรรทัดนี้: บันทึกค่า current_preset ลง settings เพื่อการโหลดครั้งถัดไป
        self.settings.set("current_preset", self.current_preset)
        # บันทึก settings ทันที (เพื่อความแน่ใจว่าจะถูกบันทึก)
        if hasattr(self.settings, "save_settings"):
            self.settings.save_settings()

        # Auto-save is always active, no need to track unsaved changes
        # Removed old notification system - now using area-positioned notifications from MBB.py
        # self.show_save_feedback()

    def auto_save_current_preset(self):
        """บันทึก preset ปัจจุบันอัตโนมัติ (เรียกจาก MBB เมื่อ crop พื้นที่ใหม่)"""
        try:
            # บันทึก preset ทันที
            self.save_preset()
            
            # Save button feedback removed - using area-positioned notifications only
            
            logging.info(f"Auto-saved preset {self.current_preset}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to auto-save preset: {e}")
            return False
    
    def load_current_preset(self):
        """โหลด preset พร้อมพิกัด"""
        if self.current_preset <= len(self.presets):
            preset = self.presets[self.current_preset - 1]

            # โหลดพื้นที่
            areas = preset["areas"].split("+")
            for area in ["A", "B", "C"]:
                self.area_states[area] = area in areas

            # โหลดพิกัด
            if "coordinates" in preset:
                for area, coords in preset["coordinates"].items():
                    self.settings.set_translate_area(
                        coords["start_x"],
                        coords["start_y"],
                        coords["end_x"],
                        coords["end_y"],
                        area,
                    )

            self.update_button_highlights()
            self.update_preset_display()

    def update_preset_display(self):
        """อัพเดทการแสดงผลชื่อ preset ที่ label หลัก"""
        try: # เพิ่ม try-except เพื่อความปลอดภัย
            if hasattr(self, "preset_label") and self.preset_label.winfo_exists():
                # *** แก้ไขจุดนี้: ใช้ชื่อที่ต้องการแสดงโดยตรงจาก settings ***
                display_name = self.settings.get_preset_display_name(self.current_preset)
                self.preset_label.config(text=display_name)
        except Exception as e:
             logging.error(f"Error updating preset display label: {e}")

    def show_save_feedback(self):
        """แสดงข้อความ feedback เมื่อบันทึก preset แบบโมเดิร์น"""
        try:
            feedback = tk.Toplevel(self.root)
            feedback.overrideredirect(True)
            feedback.configure(bg=self.theme["bg"])
            feedback.attributes("-alpha", 0.9)
            feedback.attributes("-topmost", True)

            # คำนวณตำแหน่งให้แสดงทับ control ui
            win_width = self.root.winfo_width()
            win_height = self.root.winfo_height()
            win_x = self.root.winfo_x()
            win_y = self.root.winfo_y()

            # สร้าง frame หลักแบบโค้งมน
            main_frame = tk.Frame(feedback, bg=self.theme["bg"], padx=15, pady=10)
            main_frame.pack()

            # สร้างข้อความที่สวยงาม
            msg_frame = tk.Frame(main_frame, bg=self.theme["bg"])
            msg_frame.pack()

            # ไอคอนเช็คถูก
            check_label = tk.Label(
                msg_frame,
                text="✓",
                fg="#2ecc71",  # สีเขียว
                bg=self.theme["bg"],
                font=("Arial", 14, "bold"),
            )
            check_label.pack(side=tk.LEFT, padx=(0, 5))

            # ข้อความ
            tk.Label(
                msg_frame,
                text=f"บันทึก Preset {self.current_preset} แล้ว!",
                fg="#2ecc71",
                bg=self.theme["bg"],
                font=("Nasalization Rg", 10),
            ).pack(side=tk.LEFT)

            # แสดงผลทับตำแหน่งของ control ui
            feedback.update_idletasks()
            feedback_width = feedback.winfo_width()
            feedback_height = feedback.winfo_height()

            # จัดให้อยู่ตรงกลางของ control ui
            center_x = win_x + (win_width // 2) - (feedback_width // 2)
            center_y = win_y + (win_height // 2) - (feedback_height // 2)
            feedback.geometry(f"+{center_x}+{center_y}")

            # เอฟเฟกต์ fade-in fade-out
            feedback.attributes("-alpha", 0.0)

            def fade_in():
                for i in range(0, 10):
                    if feedback.winfo_exists():
                        feedback.attributes("-alpha", i / 10)
                        feedback.update()
                        feedback.after(20)

            def fade_out():
                for i in range(10, -1, -1):
                    if feedback.winfo_exists():
                        feedback.attributes("-alpha", i / 10)
                        feedback.update()
                        feedback.after(20)
                    if feedback.winfo_exists():
                        feedback.destroy()

            fade_in()
            feedback.after(1000, fade_out)
        except Exception as e:
            print(f"Error showing save feedback: {e}")
            # Fallback ในกรณีที่มีข้อผิดพลาด
            simple_feedback = tk.Toplevel(self.root)
            simple_feedback.overrideredirect(True)
            simple_feedback.configure(bg="black")
            simple_feedback.attributes("-topmost", True)

            # จัดให้อยู่ตรงกลางของ control ui
            x = self.root.winfo_x() + (self.root.winfo_width() // 2)
            y = self.root.winfo_y() + (self.root.winfo_height() // 2)

            message_label = tk.Label(
                simple_feedback,
                text=f"บันทึก Preset {self.current_preset} แล้ว!",
                fg="lime",
                bg="black",
                font=("Nasalization Rg", 12),
            )
            message_label.pack(padx=20, pady=10)

            # จัดตำแหน่งให้อยู่ตรงกลาง
            simple_feedback.update_idletasks()
            w = simple_feedback.winfo_width()
            h = simple_feedback.winfo_height()
            simple_feedback.geometry(f"+{x-w//2}+{y-h//2}")

            simple_feedback.after(1500, simple_feedback.destroy)

    def create_button(self, parent, command, **kwargs):
        """สร้างปุ่มที่มี style ตามที่กำหนด"""
        base_config = {
            "bg": "#1a1a1a",
            "fg": "#AAAAAA",
            "activebackground": "#1a1a1a",
            "activeforeground": "#FFFFFF",
            "bd": 0,
            "relief": "flat",
            "highlightthickness": 0,
            "borderwidth": 0,
            "command": command,
        }

        base_config.update(kwargs)
        button = tk.Button(parent, **base_config)
        button.selected = False

        def on_enter(e):
            if not button.selected:
                button.configure(fg="#FFFFFF")

        def on_leave(e):
            if not button.selected:
                button.configure(fg="#AAAAAA")
            else:
                button.configure(fg="#00FFFF")

        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
        return button

    def create_cpu_limit_controls(self, parent):
        """สร้างส่วนควบคุม CPU limit บน parent ที่ระบุ (ใช้ tk.Button)"""
        # parent frame ถูก pack ด้วย fill=tk.X แล้ว

        # Label "CPU Limit:" ชิดซ้าย
        cpu_label = tk.Label(
            parent, text="CPU Limit:", bg=self.theme["bg"], fg=self.theme["text"],
            font=("Nasalization Rg", 10), anchor="w"
        )
        cpu_label.pack(side=tk.LEFT, padx=(0, 5))

        # Frame สำหรับปุ่ม CPU (อยู่ตรงกลางของพื้นที่ที่เหลือ)
        cpu_buttons_outer_frame = tk.Frame(parent, bg=self.theme["bg"])
        cpu_buttons_outer_frame.pack(side=tk.LEFT, expand=True, fill=tk.X)
        cpu_buttons_frame = tk.Frame(cpu_buttons_outer_frame, bg=self.theme["bg"])
        cpu_buttons_frame.pack(anchor="center") # จัดกลาง

        # สร้างปุ่ม CPU Limit ด้วย tk.Button
        button_font_cpu = ("Nasalization Rg", 9)
        button_width_cpu = 4
        button_height_cpu = 1
        button_padx_cpu = 6

        self.cpu_50_btn = tk.Button(
            cpu_buttons_frame, text="50%", command=lambda: self.set_cpu_limit(50),
            font=button_font_cpu, width=button_width_cpu, height=button_height_cpu,
            bd=0, relief="flat", cursor="hand2", padx=button_padx_cpu,
        )
        self.cpu_50_btn.pack(side=tk.LEFT, padx=3)

        self.cpu_60_btn = tk.Button(
            cpu_buttons_frame, text="60%", command=lambda: self.set_cpu_limit(60),
            font=button_font_cpu, width=button_width_cpu, height=button_height_cpu,
            bd=0, relief="flat", cursor="hand2", padx=button_padx_cpu,
        )
        self.cpu_60_btn.pack(side=tk.LEFT, padx=3)

        self.cpu_80_btn = tk.Button(
            cpu_buttons_frame, text="80%", command=lambda: self.set_cpu_limit(80),
            font=button_font_cpu, width=button_width_cpu, height=button_height_cpu,
            bd=0, relief="flat", cursor="hand2", padx=button_padx_cpu,
        )
        self.cpu_80_btn.pack(side=tk.LEFT, padx=3)

        # อัพเดตปุ่มตาม CPU limit ปัจจุบัน
        current_limit = self.settings.get("cpu_limit", 80)
        # ย้ายการเรียก update_cpu_buttons ไปท้ายสุด

        # Tooltip icon ชิดขวาของ parent frame
        # ทำลาย tooltip เก่า (ถ้ามี) ก่อนสร้างใหม่
        if hasattr(self, "cpu_tooltip") and self.cpu_tooltip is not None and self.cpu_tooltip.winfo_exists():
             self.cpu_tooltip.destroy()

        self.cpu_tooltip = tk.Label(
             parent, text="ℹ️", font=("Arial", 9),
             bg=self.theme["bg"], fg=self.theme["accent"], cursor="hand2",
        )
        self.cpu_tooltip.pack(side=tk.RIGHT, padx=(0, 5)) # pack ชิดขวา
        
        # ใช้ simple tooltip system
        self.create_tooltip(self.cpu_tooltip, "ตั้งค่าจำกัด CPU เพื่อลดการใช้ทรัพยากร")

        # เรียกอัพเดตสีปุ่ม CPU ครั้งสุดท้ายหลังจากทุกอย่างถูกสร้าง
        self.update_cpu_buttons(current_limit)

    def set_cpu_limit(self, limit):
        """ตั้งค่า CPU limit

        Args:
            limit (int): ค่า CPU limit ในหน่วยเปอร์เซ็นต์ (50, 60, 80)
        """
        try:
            # ไม่ทำอะไรถ้าเป็นค่าเดิม
            current_limit = self.settings.get("cpu_limit", 80)
            if current_limit == limit:
                print(f"Control UI: CPU limit มีค่า {limit}% อยู่แล้ว ไม่มีการเปลี่ยนแปลง")
                return

            # บันทึกค่าใหม่
            print(f"Control UI: กำลังตั้งค่า CPU limit จาก {current_limit}% เป็น {limit}%")
            self.settings.set("cpu_limit", limit)
            self.settings.save_settings()

            # อัพเดทปุ่ม
            self.update_cpu_buttons(limit)

            # เรียกใช้ callback จาก MBB ถ้ามี
            if self.parent_callback is not None:
                try:
                    print(f"Control UI: กำลังเรียก parent_callback ด้วยค่า: {limit}%")
                    # เรียกฟังก์ชันโดยตรง
                    result = self.parent_callback(limit)
                    print(f"Control UI: ผลลัพธ์จาก callback: {result}")
                except Exception as e:
                    print(
                        f"Control UI ERROR: เกิดข้อผิดพลาดในการเรียก CPU limit callback: {e}"
                    )
                    import traceback

                    traceback.print_exc()

            # แสดง Feedback ให้ผู้ใช้
            self.show_cpu_limit_feedback(limit)
            print(f"Control UI: ตั้งค่า CPU limit เป็น {limit}% เสร็จสมบูรณ์")
        except Exception as e:
            print(f"Control UI ERROR: เกิดข้อผิดพลาดในฟังก์ชัน set_cpu_limit: {e}")
            import traceback

            traceback.print_exc()

    def update_cpu_buttons(self, active_limit):
        """อัพเดตสถานะปุ่ม CPU limit (ใช้ tk.Button)

        Args:
            active_limit (int): ค่า CPU limit ที่ active อยู่
        """
        try:  # เพิ่ม try-except
            # ตรวจสอบว่ามีปุ่มครบหรือไม่ และปุ่มยังไม่ถูกทำลาย
            buttons_exist = all(
                hasattr(self, btn_name)
                and getattr(self, btn_name)
                and getattr(self, btn_name).winfo_exists()
                for btn_name in ["cpu_50_btn", "cpu_60_btn", "cpu_80_btn"]
            )
            if not buttons_exist:
                logging.warning("CPU limit buttons not fully initialized or destroyed.")
                return

            # Map ของปุ่มและค่า
            btn_map = {50: self.cpu_50_btn, 60: self.cpu_60_btn, 80: self.cpu_80_btn}

            # ดึงสีจาก theme ปัจจุบัน
            active_bg = self.theme.get("accent", "#6c5ce7")
            active_fg = self.theme.get("text", "#ffffff")
            inactive_bg = self.theme.get("button_bg", "#262637")
            inactive_fg = self.theme.get(
                "text", "#ffffff"
            )  # inactive text ใช้สีขาวปกติก็ได้

            # อัพเดตแต่ละปุ่ม
            for value, btn in btn_map.items():
                if value == active_limit:
                    # ปุ่มที่ถูกเลือก
                    btn.configure(
                        bg=active_bg, fg=active_fg, relief="sunken"
                    )  # ใช้ sunken relief
                    btn.selected = True  # ยังคงใช้ custom attribute นี้ได้ ถ้าต้องการ
                else:
                    # ปุ่มที่ไม่ได้เลือก
                    btn.configure(
                        bg=inactive_bg, fg=inactive_fg, relief="flat"
                    )  # ใช้ flat relief
                    btn.selected = False

        except Exception as e:
            logging.error(f"Error updating CPU buttons: {e}")
            import traceback

            traceback.print_exc()

    def show_cpu_limit_feedback(self, limit):
        """แสดงข้อความ feedback เมื่อตั้งค่า CPU limit

        Args:
            limit (int): ค่า CPU limit ที่ตั้ง
        """
        try:
            # สร้างหน้าต่าง feedback
            feedback = tk.Toplevel(self.root)
            feedback.overrideredirect(True)
            feedback.configure(bg=self.theme["bg"])
            feedback.attributes("-alpha", 0.9)
            feedback.attributes("-topmost", True)

            # สร้าง frame หลัก
            main_frame = tk.Frame(feedback, bg=self.theme["bg"], padx=15, pady=10)
            main_frame.pack()

            # สร้างข้อความ
            msg_frame = tk.Frame(main_frame, bg=self.theme["bg"])
            msg_frame.pack()

            # ข้อความ
            tk.Label(
                msg_frame,
                text=f"CPU Limit ตั้งเป็น {limit}%",
                fg=self.theme["highlight"],
                bg=self.theme["bg"],
                font=("Nasalization Rg", 10),
            ).pack(side=tk.LEFT)

            # คำนวณขนาดและตำแหน่ง
            feedback.update_idletasks()
            feedback_width = feedback.winfo_width()
            feedback_height = feedback.winfo_height()

            # จัดให้อยู่ตรงกลางของ control ui
            center_x = (
                self.root.winfo_rootx()
                + (self.root.winfo_width() // 2)
                - (feedback_width // 2)
            )
            center_y = (
                self.root.winfo_rooty()
                + (self.root.winfo_height() // 2)
                - (feedback_height // 2)
            )
            feedback.geometry(f"+{center_x}+{center_y}")

            # เอฟเฟกต์ fade-in fade-out
            feedback.attributes("-alpha", 0.0)

            def fade_in():
                for i in range(0, 10):
                    if feedback.winfo_exists():
                        feedback.attributes("-alpha", i / 10)
                        feedback.update()
                        feedback.after(20)

            def fade_out():
                for i in range(10, -1, -1):
                    if feedback.winfo_exists():
                        feedback.attributes("-alpha", i / 10)
                        feedback.update()
                        feedback.after(20)
                    if feedback.winfo_exists():
                        feedback.destroy()

            fade_in()
            feedback.after(1000, fade_out)
        except Exception as e:
            print(f"Error showing CPU limit feedback: {e}")

    def set_cpu_limit_callback(self, callback):
        """ตั้งค่า callback function สำหรับใช้เมื่อมีการเปลี่ยน CPU limit

        Args:
            callback: ฟังก์ชันที่จะถูกเรียกเมื่อมีการตั้งค่า CPU limit
        """
        self.parent_callback = callback
        print(f"Control UI: CPU limit callback registered: {callback}")

    def setup_buttons(self):
        """สร้างและจัดวางปุ่มควบคุมทั้งหมดด้วย tk.Button และ Layout ที่ถูกต้อง"""

        # ล้าง main_frame เดิม
        header_frame = getattr(self, 'header_frame', None)
        header_separator = getattr(self, 'header_separator', None)
        widgets_to_keep = [header_frame, header_separator]
        for widget in self.main_frame.winfo_children():
            if widget not in widgets_to_keep:
                try:
                    widget.destroy()
                except tk.TclError: pass

        # Font และ สี
        button_font_normal = ("Nasalization Rg", 10)
        button_font_large = ("Nasalization Rg", 12, "bold")
        preset_font = ("Nasalization Rg", 9)
        theme_bg = self.theme.get("bg", "#1a1a1a")
        inactive_bg = self.theme.get("button_bg", "#262637")

        # --- แถวที่ 1: Camera และ Area Buttons ---
        top_row = tk.Frame(self.main_frame, bg=theme_bg, bd=0, highlightthickness=0)
        top_row.pack(pady=(0, 8), fill=tk.X, padx=10)

        # ปุ่ม Camera
        try:
            camera_original = Image.open("assets/camera.png").resize((20, 20))
            camera_tk_image = ImageTk.PhotoImage(camera_original)
            self.camera_button = tk.Button(
                top_row, image=camera_tk_image, command=self.capture_screen,
                bg=inactive_bg, activebackground=self.theme.get("accent_light"),
                width=30, height=30, bd=0, highlightthickness=0, relief="flat", cursor="hand2",
            )
            self.camera_button.image = camera_tk_image
            self.camera_button.pack(side=tk.LEFT, padx=(0, 10))
        except Exception as e:
            logging.error(f"Error creating camera button: {e}")
            self.camera_button = tk.Button(top_row, text="CAM", command=self.capture_screen)
            self.camera_button.pack(side=tk.LEFT, padx=(0, 10))

        # Area buttons frame (จัดกลาง)
        area_outer_frame = tk.Frame(top_row, bg=theme_bg)
        area_outer_frame.pack(side=tk.LEFT, expand=True, fill=tk.X)
        area_frame = tk.Frame(area_outer_frame, bg=theme_bg, bd=0, highlightthickness=0)
        area_frame.pack(anchor="center")

        button_width_area = 4
        for area in ["A", "B", "C"]:
            btn = tk.Button(
                area_frame, text=area, command=lambda a=area: self.area_button_click(a),
                font=button_font_large, width=button_width_area, height=1,
                bd=0, relief="flat", cursor="hand2",
            )
            btn.pack(side=tk.LEFT, padx=5)
            setattr(self, f"button_{area.lower()}", btn)

        # --- แถวที่ 2: Force Button และ Click Translate Toggle ---
        force_row = tk.Frame(self.main_frame, bg=theme_bg, bd=0, highlightthickness=0)
        force_row.pack(fill=tk.X, pady=(0, 8), padx=10)

        # สร้างปุ่ม Force Translate (จัดชิดซ้ายและขยาย)
        self.force_button = tk.Button(
            force_row, text="PREVIOUS", command=self.safe_previous_dialog,
            font=button_font_large, height=1,
            bg=self.theme.get("button_bg", "#262637"), fg=self.theme.get("fg", "white"),
            activebackground=self.theme.get("button_hover_bg", "#38384a"), activeforeground="white",
            bd=0, relief="flat", cursor="hand2", padx=10,
        )
        # ให้ปุ่ม Force ขยาย แต่เว้นที่ทางขวา
        self.force_button.pack(side=tk.LEFT, padx=(0, 10), expand=True, fill=tk.X)
        
        # เพิ่ม event bindings สำหรับ hover-to-force
        self.force_button.bind("<Enter>", self._on_force_button_hover_enter)
        self.force_button.bind("<Leave>", self._on_force_button_hover_leave)
        
        # อัปเดตสถานะปุ่ม Force ตามสถานะการแปลปัจจุบัน
        self.update_force_button_state()

        # สร้าง Toggle Switch สำหรับ Click Translate (จัดชิดขวา)
        self.click_translate_switch_container = self.create_toggle_switch(
            force_row,  # parent ที่ถูกต้อง
            "", # ไม่มีข้อความกำกับ
            self.click_translate_var,
            lambda value: self.toggle_click_translate(value),
            width=45,
            height=22
        )
        self.click_translate_switch_container.pack(side=tk.RIGHT, anchor='e')

        # เพิ่ม tooltip สำหรับ switch container
        self.create_tooltip(
            self.click_translate_switch_container,
            "Toggle 1-Click Mode:\nOFF = Auto-translate (continuous)\nON = 1-Click translate (click FORCE/1-CLICK button or right-click translated_ui to translate once)"
        )

        # เรียกใช้ toggle_click_translate ครั้งแรกเพื่ออัพเดท UI ปุ่ม Force ตามค่าเริ่มต้น
        self.toggle_click_translate(self.click_translate_var.get())

        # --- แถวที่ 3: Preset Label และ Save Button ---
        middle_row_1 = tk.Frame(self.main_frame, bg=theme_bg, bd=0, highlightthickness=0)
        middle_row_1.pack(fill=tk.X, pady=(0, 8), padx=10)

        # *** แก้ไขจุดนี้: ดึงชื่อ Preset ปัจจุบันเพื่อแสดงผลตั้งแต่ตอนสร้าง ***
        current_preset_display_name = self.settings.get_preset_display_name(self.current_preset)
        self.preset_label = tk.Label(
            middle_row_1, text=current_preset_display_name, # แสดงชื่อที่ถูกต้องตั้งแต่แรก
            font=("Nasalization Rg", 12, "bold"), # ลดขนาดลงเล็กน้อย
            bg=theme_bg, fg=self.theme.get("accent", "#6c5ce7"), anchor="w",
            cursor="hand2"  # เพิ่ม cursor เป็น hand2 เพื่อให้รู้ว่าคลิกได้
        )
        # เพิ่ม binding สำหรับการคลิกที่ Label เพื่อแก้ไขชื่อ
        self.preset_label.bind("<Button-1>", self.edit_preset_name)
        
        # ใช้ grid เพื่อควบคุมการขยายตัวได้ดีขึ้น
        middle_row_1.grid_columnconfigure(0, weight=1) # ให้ label ขยายได้
        self.preset_label.grid(row=0, column=0, sticky="w", padx=(5, 0))

        # Save button removed - auto-save is now always active

        # --- แถวที่ 4: CPU Limit Controls ---
        cpu_controls_frame = tk.Frame(self.main_frame, bg=theme_bg, bd=0, highlightthickness=0)
        cpu_controls_frame.pack(fill=tk.X, pady=(0, 8), padx=10)
        self.create_cpu_limit_controls(cpu_controls_frame)

        # --- แถวที่ 5 & 6: Preset Buttons (จัดใหม่เป็น 2 แถว กลางจอ) ---
        preset_container_frame = tk.Frame(self.main_frame, bg=theme_bg)
        preset_container_frame.pack(pady=(0, 10)) # Frame ใหญ่สำหรับจัดกลาง

        preset_row_1 = tk.Frame(preset_container_frame, bg=theme_bg, bd=0, highlightthickness=0)
        preset_row_1.pack() # แถวแรก

        preset_row_2 = tk.Frame(preset_container_frame, bg=theme_bg, bd=0, highlightthickness=0)
        preset_row_2.pack(pady=(4,0)) # แถวสอง

        self.preset_buttons = []
        button_width_preset = 8 # เพิ่มความกว้างเผื่อชื่อยาว
        preset_font = ("Nasalization Rg", 9)

        for i in range(self.max_presets):
            preset_num = i + 1

            # *** แก้ไขจุดนี้: ใช้ชื่อที่ต้องการแสดงโดยตรงจาก settings ***
            display_name = self.settings.get_preset_display_name(preset_num)

            target_row = preset_row_1 if preset_num <= 3 else preset_row_2 # เลือกแถว

            # Log button creation for debugging
            logging.debug(f"Creating button for preset {preset_num}: text='{display_name}'")
            
            # Create a closure to properly capture the preset number
            def make_command(p):
                return lambda: self.select_preset(p)
            
            btn = tk.Button(
                target_row, text=display_name, command=make_command(preset_num),
                font=preset_font, width=button_width_preset, height=1,
                bd=0, relief="flat", cursor="hand2",
            )
            # เพิ่ม binding สำหรับการคลิกซ้ายเพื่อแก้ไขชื่อ (เฉพาะ preset 4-5)
            if preset_num >= 4:
                def make_edit_handler(p):
                    return lambda event: self.edit_preset_name(event, preset_number=p)
                btn.bind("<Double-Button-1>", make_edit_handler(preset_num))
                
            btn.pack(side=tk.LEFT, padx=5) # Pack ในแถวที่เลือก
            btn.preset_num = preset_num
            btn.selected = False
            self.preset_buttons.append(btn)

        # --- แถวที่ 7 (สุดท้าย): Reset Button ---
        reset_row = tk.Frame(self.main_frame, bg=theme_bg, bd=0, highlightthickness=0)
        reset_row.pack(fill=tk.X, pady=(5, 10), padx=10)  # เพิ่ม padding ล่าง
        
        # เพิ่มตัวแปรสำหรับ reset functionality
        self.reset_timer = None
        self.reset_progress_window = None
        
        self.reset_button = tk.Button(
            reset_row, text="RESET ALL PRESETS",  # ชื่อที่ชัดเจนขึ้น
            command=None,  # ไม่ใช้ command ปกติ
            font=("Nasalization Rg", 9),  # ฟอนต์เล็กลง
            width=15, height=1,
            bg=theme_bg, fg=self.theme.get("text_dim", "#b2b2b2"),  # Gray background matching UI
            activebackground=theme_bg, activeforeground=self.theme.get("text", "#ffffff"),
            bd=0, relief="flat", cursor="hand2", padx=10,
        )
        self.reset_button.pack(anchor="center", pady=(5, 0))  # เพิ่ม padding
        
        # Bind events สำหรับ click & hold
        self.reset_button.bind("<Button-1>", self.on_reset_button_press)
        self.reset_button.bind("<ButtonRelease-1>", self.on_reset_button_release)

        # เพิ่ม tooltips สำหรับปุ่มทั้งหมด
        self.add_tooltips_to_all_buttons()
        
        # อัพเดท UI เริ่มต้น
        self.update_preset_buttons() # ควรเรียกอันนี้เพื่อให้แน่ใจว่าปุ่มมีสีถูกต้อง
        self.update_button_highlights() # ควรเรียกอันนี้เพื่ออัพเดท area และ save button

    def add_tooltips_to_all_buttons(self):
        """เพิ่ม tooltips ให้กับปุ่มทั้งหมดตามที่ระบุในแผน"""
        try:
            # Tooltips สำหรับ Area buttons
            if hasattr(self, 'button_a'):
                self.create_tooltip(self.button_a, "เลือกชื่อตัวละคร")
            if hasattr(self, 'button_b'):
                self.create_tooltip(self.button_b, "เลือกเฉพาะข้อความที่เป็นบทพูด")
            if hasattr(self, 'button_c'):
                self.create_tooltip(self.button_c, "เลือกคำบรรยายทั่วไป")
            
            # Tooltip สำหรับ Camera button
            if hasattr(self, 'camera_button'):
                self.create_tooltip(self.camera_button, "เลือกพื้นที่การแปลใหม่บนหน้าจอ")
            
            # Tooltip สำหรับ Force button
            if hasattr(self, 'force_button'):
                self.create_tooltip(self.force_button, "บังคับแปลทันทีโดยไม่รอข้อความนิ่ง")
            
            # Save button tooltip removed - auto-save is now always active
            
            # Tooltip สำหรับ Reset button
            if hasattr(self, 'reset_button'):
                self.create_tooltip(self.reset_button, "กดค้างไว้ 3 วินาทีเพื่อรีเซ็ตทุก Preset กลับเป็นค่าเริ่มต้น")
            
            # Tooltips สำหรับ Preset buttons
            preset_tooltips = [
                "สำหรับบทสนทนาทั่วไป (A+B)",
                "สำหรับบทบรรยาย (C)", 
                "สำหรับเกมส์อื่นนอกเหนือจาก FFXIV\nที่ต้องการแปลส่วน choice หลายตัวเลือก",
                "ตั้งค่าได้อย่างอิสระ (A,B,C)",
                "ตั้งค่าได้อย่างอิสระ (A,B,C)"
            ]
            
            for i, btn in enumerate(self.preset_buttons):
                if i < len(preset_tooltips):
                    self.create_tooltip(btn, preset_tooltips[i])
            
            # Tooltips สำหรับ CPU buttons
            if hasattr(self, 'cpu_50_btn'):
                self.create_tooltip(self.cpu_50_btn, "จำกัดการใช้ CPU ที่ 50% สำหรับการแปล")
            if hasattr(self, 'cpu_60_btn'):
                self.create_tooltip(self.cpu_60_btn, "จำกัดการใช้ CPU ที่ 60% สำหรับการแปล")
            if hasattr(self, 'cpu_80_btn'):
                self.create_tooltip(self.cpu_80_btn, "จำกัดการใช้ CPU ที่ 80% สำหรับการแปล")
                
        except Exception as e:
            logging.error(f"Error adding tooltips: {e}")

    def on_reset_button_press(self, event):
        """เริ่ม timer เมื่อกดปุ่ม Reset"""
        try:
            # เปลี่ยนสีปุ่มเป็นสีแดงเมื่อกด
            self.reset_button.configure(
                bg="#e74c3c", fg="white",
                activebackground="#c0392b", activeforeground="white"
            )
            
            # ยกเลิก timer เก่า (ถ้ามี)
            if self.reset_timer:
                self.root.after_cancel(self.reset_timer)
                self.reset_timer = None
            
            # เริ่ม timer 3 วินาที
            self.reset_timer = self.root.after(3000, self.execute_reset)
            self.show_reset_progress()
            
        except Exception as e:
            logging.error(f"Error in on_reset_button_press: {e}")

    def on_reset_button_release(self, event):
        """ยกเลิก timer เมื่อปล่อยเมาส์"""
        try:
            # คืนสีปุ่มเป็นสีเดิม (gray)
            theme_bg = self.theme.get("bg", "#1a1a1a")
            theme_text_dim = self.theme.get("text_dim", "#b2b2b2")
            theme_text = self.theme.get("text", "#ffffff")
            self.reset_button.configure(
                bg=theme_bg, fg=theme_text_dim,
                activebackground=theme_bg, activeforeground=theme_text
            )
            
            if self.reset_timer:
                self.root.after_cancel(self.reset_timer)
                self.reset_timer = None
            self.hide_reset_progress()
            
        except Exception as e:
            logging.error(f"Error in on_reset_button_release: {e}")

    def show_reset_progress(self):
        """แสดง progress indicator ขณะถือปุ่ม reset"""
        try:
            # ซ่อน progress window เก่า (ถ้ามี)
            self.hide_reset_progress()
            
            # สร้างหน้าต่าง progress
            self.reset_progress_window = tk.Toplevel(self.root)
            self.reset_progress_window.overrideredirect(True)
            self.reset_progress_window.attributes("-topmost", True)
            self.reset_progress_window.attributes("-alpha", 0.9)
            
            # สร้าง frame หลัก
            main_frame = tk.Frame(
                self.reset_progress_window,
                bg=self.theme.get("accent", "#6c5ce7"),
                padx=2, pady=2
            )
            main_frame.pack()
            
            # สร้าง frame ภายใน
            inner_frame = tk.Frame(
                main_frame,
                bg=self.theme.get("bg", "#1a1a1a"),
                padx=10, pady=8
            )
            inner_frame.pack()
            
            # ข้อความแจ้งเตือน
            warning_label = tk.Label(
                inner_frame,
                text="กดค้างไว้ 3 วินาทีเพื่อรีเซ็ต",
                font=("Nasalization Rg", 10, "bold"),
                bg=self.theme.get("bg", "#1a1a1a"),
                fg="#e74c3c"
            )
            warning_label.pack()
            
            # Progress bar frame
            progress_frame = tk.Frame(
                inner_frame,
                bg=self.theme.get("bg", "#1a1a1a")
            )
            progress_frame.pack(pady=(5, 0))
            
            # Progress bar background
            progress_bg = tk.Frame(
                progress_frame,
                bg="#333333",
                width=200, height=8
            )
            progress_bg.pack()
            progress_bg.pack_propagate(False)
            
            # Progress bar fill
            self.progress_fill = tk.Frame(
                progress_bg,
                bg="#e74c3c",
                height=8
            )
            self.progress_fill.pack(side=tk.LEFT, fill=tk.Y)
            
            # คำนวณตำแหน่ง - แสดงเหนือ Control UI
            self.reset_progress_window.update_idletasks()
            window_width = self.reset_progress_window.winfo_width()
            window_height = self.reset_progress_window.winfo_height()
            
            x = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - (window_width // 2)
            y = self.root.winfo_rooty() - window_height - 10
            
            self.reset_progress_window.geometry(f"+{x}+{y}")
            
            # เริ่ม animation
            self.animate_reset_progress(0)
            
        except Exception as e:
            logging.error(f"Error in show_reset_progress: {e}")

    def animate_reset_progress(self, progress):
        """Animation สำหรับ progress bar"""
        try:
            if not self.reset_progress_window or not self.reset_progress_window.winfo_exists():
                return
                
            # คำนวณความกว้างของ progress bar
            progress_width = int(200 * (progress / 100))
            self.progress_fill.config(width=progress_width)
            
            if progress < 100 and self.reset_timer:  # ยังมี timer อยู่
                # เพิ่ม progress และ schedule การ update ครั้งถัดไป
                self.root.after(30, lambda: self.animate_reset_progress(progress + 1))
            
        except Exception as e:
            logging.error(f"Error in animate_reset_progress: {e}")

    def hide_reset_progress(self):
        """ซ่อน progress indicator"""
        try:
            if self.reset_progress_window and self.reset_progress_window.winfo_exists():
                self.reset_progress_window.destroy()
            self.reset_progress_window = None
            
        except Exception as e:
            logging.error(f"Error in hide_reset_progress: {e}")

    def execute_reset(self):
        """ทำการรีเซ็ตจริง"""
        try:
            # ซ่อน progress window
            self.hide_reset_progress()
            
            # แสดง confirmation dialog
            result = messagebox.askyesno(
                "ยืนยันการรีเซ็ต",
                "คุณแน่ใจหรือไม่ที่จะรีเซ็ตทุก Preset กลับเป็นค่าเริ่มต้น?\n\nการกระทำนี้ไม่สามารถย้อนกลับได้",
                parent=self.root,
                icon="warning"
            )
            
            if result:
                # ทำการรีเซ็ตจริง
                self.reset_all_presets_to_defaults()
                messagebox.showinfo(
                    "รีเซ็ตสำเร็จ",
                    "รีเซ็ตทุก Preset กลับเป็นค่าเริ่มต้นแล้ว!",
                    parent=self.root
                )
            
            # Clear timer
            self.reset_timer = None
            
        except Exception as e:
            logging.error(f"Error in execute_reset: {e}")
            messagebox.showerror(
                "เกิดข้อผิดพลาด",
                f"ไม่สามารถรีเซ็ต Preset ได้: {str(e)}",
                parent=self.root
            )

    def reset_all_presets_to_defaults(self):
        """รีเซ็ตทุก preset กลับเป็นค่าเริ่มต้นที่ปลอดภัย"""
        try:
            # ค่าเริ่มต้นที่ปลอดภัยตามที่ระบุในแผน
            safe_default_coordinates = {
                "A": {
                    "start_x": 100,
                    "start_y": 100,
                    "end_x": 200,
                    "end_y": 150
                }
            }
            
            # กำหนดค่าเริ่มต้นสำหรับแต่ละ preset
            default_presets = [
                {
                    "name": "dialog",
                    "role": "dialog", 
                    "areas": "A+B",
                    "coordinates": {
                        "A": safe_default_coordinates["A"],
                        "B": {
                            "start_x": 100,
                            "start_y": 160,
                            "end_x": 200,
                            "end_y": 210
                        }
                    }
                },
                {
                    "name": "lore",
                    "role": "lore",
                    "areas": "C", 
                    "coordinates": {
                        "C": {
                            "start_x": 100,
                            "start_y": 220,
                            "end_x": 200,
                            "end_y": 270
                        }
                    }
                },
                {
                    "name": "choice",
                    "role": "choice",
                    "areas": "B",
                    "coordinates": {
                        "B": {
                            "start_x": 100,
                            "start_y": 160,
                            "end_x": 200,
                            "end_y": 210
                        }
                    }
                },
                {
                    "name": "Safe Default",
                    "role": "dialog",
                    "areas": "A",
                    "coordinates": safe_default_coordinates
                },
                {
                    "name": "Safe Default",
                    "role": "dialog", 
                    "areas": "A",
                    "coordinates": safe_default_coordinates
                }
            ]
            
            # บันทึก preset ทั้งหมด
            for i, preset_data in enumerate(default_presets):
                preset_number = i + 1
                self.settings.save_preset(
                    preset_number, 
                    preset_data["areas"], 
                    preset_data["coordinates"]
                )
                
                # ตั้งชื่อและ role สำหรับ preset
                if "name" in preset_data:
                    # สำหรับ preset 4-5 ให้เป็น custom name
                    if preset_number >= 4:
                        self.settings.set_preset_custom_name(preset_number, preset_data["name"])
                    
                # บันทึก role ถ้ามี
                if "role" in preset_data:
                    preset_settings = self.settings.get_preset(preset_number)
                    if preset_settings:
                        preset_settings["role"] = preset_data["role"]
            
            # อัพเดต presets cache
            self.presets = self.settings.get_all_presets()
            
            # เปลี่ยนไปใช้ preset 1 และโหลดค่า
            self.current_preset = 1
            self.settings.set("current_preset", self.current_preset)
            
            # อัพเดต area states ตาม preset 1
            self.area_states["A"] = True
            self.area_states["B"] = True
            self.area_states["C"] = False
            
            # โหลดพิกัดของ preset 1
            preset_1_data = self.settings.get_preset(1)
            if preset_1_data and "coordinates" in preset_1_data:
                for area, coords in preset_1_data["coordinates"].items():
                    if isinstance(coords, dict) and all(key in coords for key in ["start_x", "start_y", "end_x", "end_y"]):
                        self.settings.set_translate_area(
                            coords["start_x"],
                            coords["start_y"],
                            coords["end_x"], 
                            coords["end_y"],
                            area
                        )
            
            # อัพเดต UI ทั้งหมด
            self.update_preset_buttons()
            self.update_button_highlights()
            self.update_preset_display()
            
            # แจ้งการเปลี่ยนแปลงไปยัง MBB
            if self.switch_area_callback:
                try:
                    current_area_string = self.get_current_area_string()
                    self.switch_area_callback(current_area_string)
                except Exception as e:
                    logging.error(f"Error calling switch_area_callback after reset: {e}")
            
            # Auto-save is always active, no need to track unsaved changes
            
            logging.info("All presets have been reset to safe defaults")
            
        except Exception as e:
            logging.error(f"Error in reset_all_presets_to_defaults: {e}")
            raise

    def toggle_manual_force_mode(self, value):
        """
        สลับสถานะของ Manual Force Mode และแจ้งให้ MBB ทราบ
        
        Args:
            value (bool): สถานะใหม่ (True = เปิด, False = ปิด)
        """
        try:
            # บันทึกค่าลง settings
            self.settings.set("manual_force_mode", value)
            
            # แสดงข้อความ feedback
            mode_text = "เปิด" if value else "ปิด"
            message = f"{mode_text} Manual Force Mode"
            logging.info(message)
            
            # แจ้ง MBB ผ่าน callback (ถ้ามี)
            if self.parent_callback and hasattr(self.parent_callback, "__call__"):
                try:
                    # ส่งค่าให้ callback พร้อมระบุว่าเป็น manual_force_mode
                    self.parent_callback("manual_force_mode", value)
                except Exception as e:
                    logging.error(f"Error calling parent callback for manual force mode: {e}")
            
            # แสดง feedback บน UI
            self.show_mode_change_feedback(message)
        
        except Exception as e:
            logging.error(f"Error in toggle_manual_force_mode: {e}")
    
    def show_mode_change_feedback(self, message):
        """
        แสดงข้อความ feedback เมื่อมีการเปลี่ยน mode
        
        Args:
            message (str): ข้อความที่จะแสดง
        """
        try:
            # สร้างหน้าต่าง feedback
            feedback = tk.Toplevel(self.root)
            feedback.overrideredirect(True)
            feedback.configure(bg=self.theme.get("bg", "#1a1a1a"))
            feedback.attributes("-alpha", 0.9)
            feedback.attributes("-topmost", True)

            # สร้าง frame หลัก
            main_frame = tk.Frame(
                feedback, 
                bg=self.theme.get("bg", "#1a1a1a"), 
                padx=15, 
                pady=10
            )
            main_frame.pack()

            # สร้างข้อความ
            msg_frame = tk.Frame(main_frame, bg=self.theme.get("bg", "#1a1a1a"))
            msg_frame.pack()

            # ไอคอน (ใช้ emoji ตามความเหมาะสม)
            icon_label = tk.Label(
                msg_frame,
                text="🔄",  # สัญลักษณ์การสลับโหมด
                fg=self.theme.get("highlight", "#00FFFF"),
                bg=self.theme.get("bg", "#1a1a1a"),
                font=("Segoe UI Emoji", 14, "bold"),
            )
            icon_label.pack(side=tk.LEFT, padx=(0, 5))

            # ข้อความ
            tk.Label(
                msg_frame,
                text=message,
                fg=self.theme.get("highlight", "#00FFFF"),
                bg=self.theme.get("bg", "#1a1a1a"),
                font=("Nasalization Rg", 10, "bold"),
            ).pack(side=tk.LEFT)

            # คำนวณตำแหน่ง - ให้อยู่กลางของ Control UI
            x = self.root.winfo_rootx() + (self.root.winfo_width() // 2)
            y = self.root.winfo_rooty() + (self.root.winfo_height() // 2)
            
            # ปรับตำแหน่งให้อยู่กลาง Control UI
            feedback.update_idletasks()
            feedback_width = feedback.winfo_width()
            feedback_height = feedback.winfo_height()
            
            x = x - (feedback_width // 2)
            y = y - (feedback_height // 2)
            
            feedback.geometry(f"+{x}+{y}")

            # เอฟเฟกต์ fade-in fade-out
            feedback.attributes("-alpha", 0.0)

            def fade_in():
                for i in range(0, 10):
                    if feedback.winfo_exists():
                        feedback.attributes("-alpha", i / 10)
                        feedback.update()
                        time.sleep(0.02)

            def fade_out():
                for i in range(10, -1, -1):
                    if feedback.winfo_exists():
                        feedback.attributes("-alpha", i / 10)
                        feedback.update()
                        time.sleep(0.02)
                    if feedback.winfo_exists():
                        feedback.destroy()

            # ใช้ Thread แยกสำหรับ fade effect เพื่อไม่ให้ freeze UI
            fade_in_thread = threading.Thread(target=fade_in)
            fade_in_thread.daemon = True
            fade_in_thread.start()
            
            # ตั้งเวลาสำหรับ fade out
            feedback.after(800, lambda: threading.Thread(target=fade_out, daemon=True).start())
            
        except Exception as e:
            logging.error(f"Error showing mode change feedback: {e}")
    
    def edit_preset_name(self, event, preset_number=None):
        """แสดงหน้าต่าง dialog ให้ผู้ใช้แก้ไขชื่อของ preset

        Args:
            event: เหตุการณ์ที่เกิดขึ้น (การคลิก)
            preset_number: หมายเลข preset ที่ต้องการแก้ไขชื่อ (ถ้าไม่ระบุจะใช้ preset ปัจจุบัน)
        """
        # ถ้าไม่ระบุ preset_number ให้ใช้ preset ปัจจุบัน
        if preset_number is None:
            preset_number = self.current_preset
            
        # อนุญาตให้แก้ไขได้เฉพาะ preset 4 และ 5 เท่านั้น
        if preset_number < 4:
            # แสดงข้อความแจ้งเตือนว่าไม่สามารถแก้ไขชื่อได้
            messagebox.showinfo(
                "ไม่สามารถแก้ไขชื่อได้",
                f"Preset {preset_number} (1-3) เป็น preset ระบบ ไม่สามารถแก้ไขชื่อได้",
                parent=self.root
            )
            return
            
        try:
            # รับชื่อปัจจุบันของ preset
            current_name = self.settings.get_preset_display_name(preset_number)
            
            # สร้างหน้าต่าง dialog สำหรับป้อนชื่อใหม่
            dialog = tk.Toplevel(self.root)
            dialog.title(f"แก้ไขชื่อ Preset {preset_number}")
            dialog.configure(bg=self.theme.get("bg", "#1a1a1a"))
            dialog.resizable(False, False)
            dialog.transient(self.root)
            dialog.grab_set()
            
            # จัดตำแหน่งหน้าต่าง dialog ให้อยู่ตรงกลางของ Control UI
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 150
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 60
            dialog.geometry(f"320x150+{x}+{y}")
            
            # กำหนด padding และกรอบที่เห็นชัดเจน
            outer_frame = tk.Frame(
                dialog, 
                bg=self.theme.get("accent_light", "#8075e5"), 
                padx=2, 
                pady=2,
                highlightbackground=self.theme.get("accent", "#6c5ce7"),
                highlightthickness=1
            )
            outer_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
            
            # สร้าง UI elements
            main_frame = tk.Frame(
                outer_frame, 
                bg=self.theme.get("bg", "#1a1a1a"), 
                padx=12, 
                pady=12
            )
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # ไอคอนและหัวข้อในแถวเดียวกัน
            header_frame = tk.Frame(
                main_frame,
                bg=self.theme.get("bg", "#1a1a1a")
            )
            header_frame.pack(fill=tk.X, pady=(0, 10))
            
            # ไอคอน (ถ้ามี)
            try:
                icon = tk.Label(
                    header_frame,
                    text="✏️",  # ใช้ emoji แทนไอคอน
                    bg=self.theme.get("bg", "#1a1a1a"),
                    fg=self.theme.get("accent", "#6c5ce7"),
                    font=("Segoe UI Emoji", 14)
                )
                icon.pack(side=tk.LEFT, padx=(0, 5))
            except:
                pass  # ถ้าไม่สามารถแสดงไอคอนได้ ก็ข้ามไป
            
            # ข้อความอธิบาย
            label = tk.Label(
                header_frame, 
                text=f"ป้อนชื่อใหม่สำหรับ Preset {preset_number}:",
                bg=self.theme.get("bg", "#1a1a1a"),
                fg=self.theme.get("text", "#ffffff"),
                font=("Nasalization Rg", 10),
                anchor="w"
            )
            label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # Entry สำหรับป้อนชื่อใหม่ ปรับให้มีขอบชัดเจน
            entry_frame = tk.Frame(
                main_frame,
                bg=self.theme.get("accent_light", "#8075e5"),
                padx=1,
                pady=1
            )
            entry_frame.pack(fill=tk.X, pady=(0, 15))
            
            entry_var = tk.StringVar(value=current_name)
            entry = tk.Entry(
                entry_frame, 
                textvariable=entry_var,
                bg=self.theme.get("button_bg", "#262637"),
                fg=self.theme.get("text", "#ffffff"),
                insertbackground=self.theme.get("text", "#ffffff"),  # สีของ cursor
                font=("Nasalization Rg", 11),
                bd=0,  # ไม่มีขอบภายใน
                relief="flat",
                highlightthickness=0
            )
            entry.pack(fill=tk.X, padx=1, pady=1)
            entry.select_range(0, tk.END)  # เลือกข้อความทั้งหมด
            entry.focus_set()  # ให้ focus อยู่ที่ entry
            
            # Frame สำหรับปุ่ม
            button_frame = tk.Frame(main_frame, bg=self.theme.get("bg", "#1a1a1a"))
            button_frame.pack(fill=tk.X)
            
            # ฟังก์ชันสำหรับบันทึกชื่อใหม่
            def save_name():
                new_name = entry_var.get().strip()
                if not new_name:
                    messagebox.showwarning("ข้อผิดพลาด", "กรุณาป้อนชื่อ", parent=dialog)
                    return
                
                # บันทึกชื่อใหม่
                self.settings.set_preset_custom_name(preset_number, new_name)
                
                # อัพเดต UI
                self.update_preset_display()
                self.update_preset_buttons()
                
                # ปิดหน้าต่าง dialog
                dialog.destroy()
                
                # แสดงข้อความแจ้งเตือนว่าบันทึกสำเร็จ
                self.show_name_change_feedback(preset_number, new_name)
            
            # ฟังก์ชันสำหรับยกเลิก
            def cancel():
                dialog.destroy()
            
            # ปุ่มยกเลิก
            cancel_btn = tk.Button(
                button_frame,
                text="ยกเลิก",
                command=cancel,
                bg=self.theme.get("button_bg", "#262637"),
                fg=self.theme.get("text", "#ffffff"),
                activebackground=self.theme.get("button_bg", "#262637"),
                activeforeground=self.theme.get("text", "#ffffff"),
                font=("Nasalization Rg", 9),
                width=8,
                bd=0,
                relief="flat",
                cursor="hand2"
            )
            cancel_btn.pack(side=tk.RIGHT, padx=(5, 0))
            
            # ปุ่มบันทึก
            save_btn = tk.Button(
                button_frame,
                text="บันทึก",
                command=save_name,
                bg=self.theme.get("accent", "#6c5ce7"),
                fg=self.theme.get("text", "#ffffff"),
                activebackground=self.theme.get("accent_light"),
                activeforeground=self.theme.get("text", "#ffffff"),
                font=("Nasalization Rg", 9),
                width=8,
                bd=0,
                relief="flat",
                cursor="hand2"
            )
            save_btn.pack(side=tk.RIGHT, padx=(0, 5))
            
            # ทำให้สามารถกด Enter เพื่อบันทึกได้
            entry.bind("<Return>", lambda event: save_name())
            # ทำให้สามารถกด Escape เพื่อยกเลิกได้
            dialog.bind("<Escape>", lambda event: cancel())
            
            # ไม่ใช้ rounded corners กับหน้าต่างนี้เพื่อให้แสดงผลเต็มที่
            # self.apply_rounded_corners_to_toplevel(dialog)
            
            # ตั้งค่า protocol WM_DELETE_WINDOW เพื่อให้สามารถปิดหน้าต่างได้ด้วยปุ่ม X
            dialog.protocol("WM_DELETE_WINDOW", cancel)
            
        except Exception as e:
            logging.error(f"Error in edit_preset_name: {e}")
            import traceback
            traceback.print_exc()

    def show_name_change_feedback(self, preset_number, new_name):
        """แสดงข้อความแจ้งเตือนเมื่อเปลี่ยนชื่อ preset สำเร็จ

        Args:
            preset_number: หมายเลข preset ที่เปลี่ยนชื่อ
            new_name: ชื่อใหม่ของ preset
        """
        try:
            # สร้างหน้าต่าง feedback
            feedback = tk.Toplevel(self.root)
            feedback.overrideredirect(True)
            feedback.configure(bg=self.theme["bg"])
            feedback.attributes("-alpha", 0.9)
            feedback.attributes("-topmost", True)

            # สร้าง frame หลัก
            main_frame = tk.Frame(feedback, bg=self.theme["bg"], padx=15, pady=10)
            main_frame.pack()

            # สร้างข้อความ
            msg_frame = tk.Frame(main_frame, bg=self.theme["bg"])
            msg_frame.pack()

            # ไอคอนเช็คถูก
            check_label = tk.Label(
                msg_frame,
                text="✓",
                fg="#2ecc71",  # สีเขียว
                bg=self.theme["bg"],
                font=("Arial", 14, "bold"),
            )
            check_label.pack(side=tk.LEFT, padx=(0, 5))

            # ข้อความ
            name_text = tk.Label(
                msg_frame,
                text=f"เปลี่ยนชื่อ Preset {preset_number} เป็น",
                fg="#2ecc71",
                bg=self.theme["bg"],
                font=("Nasalization Rg", 10),
            )
            name_text.pack(side=tk.LEFT)
            
            # แสดงชื่อใหม่ในบรรทัดถัดไป
            new_name_text = tk.Label(
                main_frame,
                text=f'"{new_name}"',
                fg=self.theme["highlight"],
                bg=self.theme["bg"],
                font=("Nasalization Rg", 10, "bold"),
            )
            new_name_text.pack(pady=(5, 0))

            # คำนวณขนาดและตำแหน่ง
            feedback.update_idletasks()
            feedback_width = feedback.winfo_width()
            feedback_height = feedback.winfo_height()

            # จัดให้อยู่ตรงกลางของ control ui
            center_x = (
                self.root.winfo_rootx()
                + (self.root.winfo_width() // 2)
                - (feedback_width // 2)
            )
            center_y = (
                self.root.winfo_rooty()
                + (self.root.winfo_height() // 2)
                - (feedback_height // 2)
            )
            feedback.geometry(f"+{center_x}+{center_y}")

            # เอฟเฟกต์ fade-in fade-out
            feedback.attributes("-alpha", 0.0)

            def fade_in():
                for i in range(0, 10):
                    if feedback.winfo_exists():
                        feedback.attributes("-alpha", i / 10)
                        feedback.update()
                        feedback.after(20)

            def fade_out():
                for i in range(10, -1, -1):
                    if feedback.winfo_exists():
                        feedback.attributes("-alpha", i / 10)
                        feedback.update()
                        feedback.after(20)
                    if feedback.winfo_exists():
                        feedback.destroy()

            fade_in()
            feedback.after(1500, fade_out)  # แสดง 1.5 วินาที
        except Exception as e:
            logging.error(f"Error showing name change feedback: {e}")

    def apply_rounded_corners_to_toplevel(self, window):
        """ทำให้หน้าต่าง Toplevel มีขอบโค้งมน

        Args:
            window: หน้าต่าง Toplevel ที่ต้องการทำให้มีขอบโค้งมน
        """
        try:
            # รอให้หน้าต่างแสดงผล
            window.update_idletasks()
            
            # ดึงค่า HWND ของหน้าต่าง
            hwnd = windll.user32.GetParent(window.winfo_id())
            
            # ลบกรอบและหัวข้อ (ถ้าต้องการ)
            # style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            # style &= ~win32con.WS_CAPTION
            # style &= ~win32con.WS_THICKFRAME
            # win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
            
            # สร้างภูมิภาค (region) โค้งมน
            width = window.winfo_width()
            height = window.winfo_height()
            region = win32gui.CreateRoundRectRgn(0, 0, width, height, 10, 10)
            
            # กำหนดภูมิภาคให้กับหน้าต่าง
            win32gui.SetWindowRgn(hwnd, region, True)
            
        except Exception as e:
            logging.error(f"Error applying rounded corners to toplevel: {e}")
            import traceback
            traceback.print_exc()

    def lighten_color(self, color, factor=1.3):
        """ทำให้สีอ่อนลงตามค่า factor

        Args:
            color: สีเริ่มต้นในรูปแบบ hex (#RRGGBB)
            factor: ค่าที่ใช้ในการทำให้อ่อนลง (ค่ามากกว่า 1)

        Returns:
            str: สีที่อ่อนลงในรูปแบบ hex
        """
        if not isinstance(color, str) or not color.startswith("#"):
            return color

        try:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)

            r = min(int(r * factor), 255)
            g = min(int(g * factor), 255)
            b = min(int(b * factor), 255)

            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception as e:
            print(f"Error lightening color: {e}")
            return color

    def select_preset(self, preset_number):
        """เลือก preset ตามหมายเลข
        Args:
            preset_number (int): หมายเลข preset (1-5)
        """
        # Debug logging
        logging.info(f"select_preset called with preset_number={preset_number}")
        
        if 1 <= preset_number <= self.max_presets:
            # Auto-save is always active, no need for warning dialog
            self._complete_preset_switch(preset_number)

    def _complete_preset_switch(self, preset_number):
        """ดำเนินการเปลี่ยน preset, แจ้ง MBB, และบันทึกเวลา manual selection"""
        try:
            logging.info(f"_complete_preset_switch called with preset_number={preset_number}")
            
            if not (1 <= preset_number <= self.max_presets):
                logging.error(f"Invalid preset number requested: {preset_number}")
                return

            # Auto-save already handled by area selection, no need to save here

            previous_preset = self.current_preset
            self.current_preset = preset_number

            # ดึงชื่อที่จะแสดงของ preset
            display_name = self.settings.get_preset_display_name(preset_number)

            # --- บันทึกค่า current_preset และ เวลาที่เลือกด้วยตนเอง ลง settings ---
            current_timestamp = time.time()
            self.settings.set("current_preset", self.current_preset)
            self.settings.set("last_manual_preset_selection_time", current_timestamp)
            logging.info(f"Manual preset selection: {display_name} at {current_timestamp}")
            # --- จบการบันทึกเวลา ---

            preset_data = self.settings.get_preset(preset_number)
            logging.debug(f"Retrieved preset_data for preset {preset_number}")
            
            if not preset_data:
                logging.error(f"Cannot find preset data for {preset_number}")
                # Fallback logic... (กลับไป preset 1)
                self.current_preset = 1
                self.settings.set("current_preset", 1)
                self.settings.set("last_manual_preset_selection_time", time.time()) # บันทึกเวลา fallback ด้วย
                preset_data = self.settings.get_preset(1)
                if not preset_data: logging.error("Failed to load even Preset 1 data."); return

            area_config = preset_data.get("areas", "A")
            coordinates = preset_data.get("coordinates", {})
            
            logging.info(f"Preset {preset_number} area_config: {area_config}")

            # อัพเดตพิกัดใน Settings หลัก
            if isinstance(coordinates, dict):
                for area, coords in coordinates.items():
                    if isinstance(coords, dict) and all(k in coords for k in ["start_x", "start_y", "end_x", "end_y"]):
                        self.settings.set_translate_area(
                            coords["start_x"], coords["start_y"], coords["end_x"], coords["end_y"], area
                        )
                        logging.debug(f"Set coordinates for area {area}: {coords}")
                    else: 
                        logging.warning(f"Invalid coordinates data for area {area}")
                        logging.warning(f"Invalid coordinates for area {area}: {coords}")

            # อัพเดต area_states ภายใน Control UI
            active_areas = area_config.split("+")
            logging.info(f"Active areas for preset {preset_number}: {active_areas}")
            
            for area in ["A", "B", "C"]:
                self.area_states[area] = area in active_areas
                logging.debug(f"Area {area} state: {self.area_states[area]}")

            # อัพเดต UI ทั้งหมด
            self.update_preset_buttons()
            self.update_button_highlights() # สำคัญ: เรียกหลังสุดเพื่อจัดการ locking/save state

            # แจ้ง MBB.py (ส่ง list areas และ preset number) ผ่าน callback เดิม
            if self.switch_area_callback:
                logging.info(f"Calling switch_area_callback with active_areas={active_areas}, preset_number_override={self.current_preset}")
                self.switch_area_callback(active_areas, preset_number_override=self.current_preset)
            else:
                logging.warning(f"No switch_area_callback defined")

            # No need to track unsaved changes - auto-save is always active

            # แสดง feedback การสลับ preset (เหมือนเดิม)
            if previous_preset != self.current_preset:
                self.show_preset_switch_feedback(previous_preset, self.current_preset)

            logging.info(f"Completed switch to preset {preset_number}. Areas: {area_config}")

            # *** เพิ่มจุดนี้: เรียก Callback ใหม่เพื่อ Trigger การแสดง Area ชั่วคราว ***
            if self.trigger_temporary_area_display_callback:
                logging.info(f"Triggering temporary area display for preset {preset_number} ({area_config})")
                try:
                    # ส่ง area_config (เช่น "A+B") ไปให้ MBB.py จัดการแสดงผล
                    self.trigger_temporary_area_display_callback(area_config)
                except Exception as e:
                    logging.error(f"Error calling temporary area display callback: {e}")
            else:
                 logging.warning("Temporary area display callback is not set in Control_UI.")


        except Exception as e:
            logging.error(f"Error in _complete_preset_switch for preset {preset_number}: {e}")
            logging.error(f"Error switching to preset {preset_number}: {e}")
            import traceback
            traceback.print_exc()
            
            # Show error message to user
            try:
                error_msg = tk.Toplevel(self.root)
                error_msg.title("Error")
                error_msg.geometry("400x150")
                error_msg.configure(bg="#1a1a1a")
                
                tk.Label(
                    error_msg,
                    text=f"Failed to switch to preset {preset_number}\n\nError: {str(e)}",
                    bg="#1a1a1a",
                    fg="red",
                    font=("Arial", 10),
                    wraplength=350
                ).pack(pady=20)
                
                tk.Button(
                    error_msg,
                    text="OK",
                    command=error_msg.destroy,
                    bg="#404040",
                    fg="white"
                ).pack(pady=10)
            except:
                pass

    def update_preset_buttons(self):
        """อัพเดตสถานะและการแสดงผลของปุ่ม preset ทั้งหมด (ใช้ tk.Button)"""
        try:
            # ดึงสีจาก theme ปัจจุบัน
            active_bg = self.theme.get("accent", "#6c5ce7")
            active_fg = self.theme.get("text", "#ffffff")
            inactive_bg = self.theme.get("button_bg", "#262637")
            inactive_fg = self.theme.get("text_dim", "#b2b2b2")

            for btn in self.preset_buttons:
                if btn and btn.winfo_exists():
                    preset_num = btn.preset_num
                    is_selected = preset_num == self.current_preset
                    btn.selected = is_selected

                    # --- แก้ไขจุดนี้: ใช้ชื่อที่ต้องการแสดงโดยตรงจาก settings ---
                    display_name = self.settings.get_preset_display_name(preset_num)

                    # อัพเดต Text ของปุ่ม
                    btn.configure(text=display_name)

                    if is_selected:
                        # ปุ่มที่เลือก
                        btn.configure(bg=active_bg, fg=active_fg, relief="sunken")
                    else:
                        # ปุ่มที่ไม่ได้เลือก
                        btn.configure(bg=inactive_bg, fg=inactive_fg, relief="flat")

            # อัพเดต preset label ด้วย (ใช้ชื่อจาก settings เช่นกัน)
            if hasattr(self, "preset_label") and self.preset_label.winfo_exists():
                # *** แก้ไขจุดนี้: ใช้ชื่อที่ต้องการแสดงโดยตรงจาก settings สำหรับ label ***
                display_name = self.settings.get_preset_display_name(self.current_preset)
                # อัพเดต Text ของ label
                self.preset_label.config(text=display_name)

        except Exception as e:
            print(f"Error updating preset buttons: {e}")
            logging.error(f"Error updating preset buttons: {e}")
            import traceback
            traceback.print_exc()

    def apply_rounded_corners(self):
        """ทำให้หน้าต่างมีขอบโค้งมน"""
        try:
            # รอให้ window แสดงผล
            self.root.update_idletasks()

            # ดึงค่า HWND ของ window
            hwnd = windll.user32.GetParent(self.root.winfo_id())

            # ลบกรอบและหัวข้อ
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            style &= ~win32con.WS_CAPTION
            style &= ~win32con.WS_THICKFRAME
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

            # สร้างภูมิภาค (region) โค้งมน
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            region = win32gui.CreateRoundRectRgn(0, 0, width, height, 15, 15)

            # กำหนดภูมิภาคให้กับ window
            win32gui.SetWindowRgn(hwnd, region, True)

        except Exception as e:
            print(f"Error applying rounded corners: {e}")

    def update_theme(self, accent_color=None, highlight_color=None):
        """อัพเดท UI ของ Control Panel ตาม Theme ปัจจุบัน (ใช้ tk.Button)"""
        try:
            print("DEBUG: Control UI update_theme called")
            logging.info("Updating Control UI theme...")
            # ดึงค่าสีล่าสุดจาก appearance_manager
            theme_bg = appearance_manager.bg_color
            theme_accent = appearance_manager.get_accent_color()
            print(f"DEBUG: Control UI using colors - accent: {theme_accent}, bg: {theme_bg}")
            theme_accent_light = appearance_manager.get_theme_color("accent_light")
            theme_secondary = appearance_manager.get_theme_color("secondary")
            theme_button_bg = appearance_manager.get_theme_color("button_bg")
            theme_text = appearance_manager.get_theme_color("text")  # สีข้อความหลัก
            theme_text_dim = appearance_manager.get_theme_color(
                "text_dim"
            )  # สีข้อความรอง/จาง
            theme_highlight = appearance_manager.get_highlight_color()
            theme_error = self.theme.get("error", "#e74c3c")  # สีสำหรับ error/unsaved

            # *** เพิ่ม: กำหนดค่า active_fg และ inactive_fg ***
            active_fg = theme_text  # ปุ่ม Active ใช้สีข้อความหลัก
            inactive_fg = theme_text_dim  # ปุ่ม Inactive ใช้สีข้อความรอง

            # อัพเดทค่าสีใน self.theme ของ Control_UI ด้วย (เหมือนเดิม)
            self.theme = {
                "bg": theme_bg,
                "accent": theme_accent,
                "accent_light": theme_accent_light,
                "secondary": theme_secondary,
                "button_bg": theme_button_bg,
                "text": theme_text,
                "text_dim": theme_text_dim,
                "highlight": theme_highlight,
                "error": theme_error,
            }

            # อัพเดทพื้นหลังของหน้าต่างและ Frame หลัก (เหมือนเดิม)
            if hasattr(self, "root") and self.root.winfo_exists():
                self.root.configure(bg=theme_bg)
            if hasattr(self, "main_frame") and self.main_frame.winfo_exists():
                self.main_frame.configure(bg=theme_bg)

            # อัพเดท Header (เหมือนเดิม)
            if hasattr(self, "title_label") and self.title_label.winfo_exists():
                self.title_label.configure(bg=theme_bg, fg=theme_accent)
                if isinstance(self.title_label.master, tk.Frame):
                    self.title_label.master.configure(bg=theme_bg)
            if (
                hasattr(self, "header_separator")
                and self.header_separator.winfo_exists()
            ):
                self.header_separator.configure(bg=theme_accent_light)

            # อัพเดทพื้นหลังของ Frames ย่อยๆ (วน Loop - เหมือนเดิม)
            if hasattr(self, "main_frame") and self.main_frame.winfo_exists():
                for child in self.main_frame.winfo_children():
                    if isinstance(child, tk.Frame) and child.winfo_exists():
                        child.configure(bg=theme_bg)
                        for sub_child in child.winfo_children():
                            if (
                                isinstance(sub_child, tk.Frame)
                                and sub_child.winfo_exists()
                            ):
                                sub_child.configure(bg=theme_bg)

            # --- อัพเดทปุ่ม tk.Button ทั้งหมด ---

            # ปุ่ม Camera
            if hasattr(self, "camera_button") and self.camera_button.winfo_exists():
                # ปุ่ม Camera เป็น icon ไม่ต้องตั้ง fg, ตั้งแต่ bg และ activebackground
                self.camera_button.configure(
                    bg=theme_button_bg, activebackground=theme_accent_light
                )
            
            # ปุ่ม Reset (ใช้สีพื้นหลัง UI)
            if hasattr(self, "reset_button") and self.reset_button.winfo_exists():
                self.reset_button.configure(
                    bg=theme_bg, fg=theme_text_dim,
                    activebackground=theme_bg, activeforeground=theme_text
                )

            # ปุ่ม Area (A, B, C)
            button_map_area = {
                "A": getattr(self, "button_a", None),
                "B": getattr(self, "button_b", None),
                "C": getattr(self, "button_c", None),
            }
            for area, button in button_map_area.items():
                if button and button.winfo_exists():
                    is_active = self.area_states.get(area, False)
                    base_bg = (
                        theme_accent
                        if is_active
                        else (
                            theme_secondary if area in ["B", "C"] else theme_button_bg
                        )
                    )
                    # *** แก้ไข: ใช้ตัวแปร active_fg และ inactive_fg ที่เพิ่งกำหนด ***
                    base_fg = active_fg if is_active else inactive_fg
                    # ปุ่ม B, C ที่ inactive ใช้สีข้อความปกติแทนสีจาง เพื่อให้อ่านง่ายบนพื้นสี secondary
                    if not is_active and area in ["B", "C"]:
                        base_fg = theme_text
                    button.configure(
                        bg=base_bg,
                        fg=base_fg,
                        activebackground=theme_accent_light,  # Hover/Active ใช้สีสว่าง
                        activeforeground=active_fg,
                    )  # Active text ใช้สีหลัก

            # Save button removed - auto-save is now always active

            # ปุ่ม Force
            if hasattr(self, "force_button") and self.force_button.winfo_exists():
                self.force_button.configure(
                    bg="#000000",
                    fg=theme_text,
                    activebackground="#333333",  # ทำให้เข้มขึ้นเล็กน้อยตอนกด
                    activeforeground=theme_text,
                )

            # ปุ่ม CPU Limit
            button_map_cpu = {
                50: getattr(self, "cpu_50_btn", None),
                60: getattr(self, "cpu_60_btn", None),
                80: getattr(self, "cpu_80_btn", None),
            }
            current_cpu_limit = self.settings.get("cpu_limit", 80)
            for value, button in button_map_cpu.items():
                if button and button.winfo_exists():
                    is_active = value == current_cpu_limit
                    base_bg = theme_accent if is_active else theme_button_bg
                    # *** แก้ไข: ใช้ตัวแปร active_fg และ inactive_fg ที่เพิ่งกำหนด ***
                    # ในที่นี้ปุ่ม CPU inactive ควรใช้สีข้อความปกติ ไม่ใช่สีจาง
                    base_fg = active_fg if is_active else theme_text
                    button.configure(
                        bg=base_bg,
                        fg=base_fg,
                        activebackground=theme_accent_light,
                        activeforeground=active_fg,
                    )

            # อัพเดท Preset Display Label
            if hasattr(self, "preset_label") and self.preset_label.winfo_exists():
                # ใช้ชื่อที่ต้องการแสดงโดยตรง
                display_name = self.settings.get_preset_display_name(self.current_preset)
                self.preset_label.config(text=display_name)

            # อัพเดทปุ่ม Preset Numbers (P1-P5)
            if hasattr(self, "preset_buttons"):
                for btn in self.preset_buttons:
                    if btn and isinstance(btn, tk.Button) and btn.winfo_exists():
                        is_selected = btn.preset_num == self.current_preset
                        base_bg = theme_accent if is_selected else theme_button_bg
                        # *** แก้ไข: ใช้ตัวแปร active_fg และ inactive_fg ที่เพิ่งกำหนด ***
                        base_fg = active_fg if is_selected else inactive_fg
                        btn.configure(
                            bg=base_bg,
                            fg=base_fg,
                            activebackground=theme_accent_light,
                            activeforeground=active_fg,
                        )

            # อัพเดท CPU Limit Section Labels
            if hasattr(self, "cpu_label") and self.cpu_label.winfo_exists():
                self.cpu_label.configure(bg=theme_bg, fg=theme_text)
            if hasattr(self, "cpu_tooltip") and self.cpu_tooltip.winfo_exists():
                self.cpu_tooltip.configure(bg=theme_bg, fg=theme_accent)

            # --- ไม่จำเป็นต้องเรียกเมธอดอัพเดทเฉพาะส่วนซ้ำอีก ---
            # self.update_cpu_buttons(...)
            # self.update_preset_buttons()
            # self.update_button_highlights()

            logging.info("Control UI theme updated successfully (using tk.Button).")
            print("DEBUG: Control UI theme update completed successfully")

        except Exception as e:
            logging.error(f"Error updating Control UI theme: {e}")
            print(f"DEBUG: Error in Control UI theme update: {e}")
            import traceback

            traceback.print_exc()

    def lighten_color(self, color, factor=1.3):
        """ทำให้สีอ่อนลงตามค่า factor

        Args:
            color: สีเริ่มต้นในรูปแบบ hex (#RRGGBB)
            factor: ค่าที่ใช้ในการทำให้อ่อนลง (ค่ามากกว่า 1)

        Returns:
            str: สีที่อ่อนลงในรูปแบบ hex
        """
        if not isinstance(color, str) or not color.startswith("#"):
            return color

        try:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)

            r = min(int(r * factor), 255)
            g = min(int(g * factor), 255)
            b = min(int(b * factor), 255)

            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception as e:
            print(f"Error lightening color: {e}")
            return color

    def get_current_area_string(self):
        """รับสตริงแสดงพื้นที่ที่เลือกในปัจจุบัน"""
        active = [area for area in ["A", "B", "C"] if self.area_states[area]]
        return "+".join(active) if active else "A"

    def load_current_area_states(self):
        """โหลดสถานะพื้นที่ปัจจุบัน"""
        saved_area = self.settings.get("current_area", "A+B")
        if saved_area:
            areas = saved_area.split("+")
            for area in ["A", "B", "C"]:
                self.area_states[area] = area in areas

    def switch_speed(self, speed_mode):
        """สลับระหว่างโหมดความเร็วโดยใช้สีจากธีม"""
        self.current_speed = speed_mode

        # อัพเดตสถานะและการแสดงผลของปุ่มความเร็ว
        if speed_mode == "normal":
            # เลือก Normal
            self.normal_speed_button.selected = True
            self.high_speed_button.selected = False

            # อัพเดตสีทันทีไม่ต้องมี delay
            self.normal_speed_button.config(
                fg=self.theme["highlight"], bg=self.theme["button_bg"]
            )
            self.high_speed_button.config(
                fg=self.theme["text_dim"], bg=self.theme["button_bg"]
            )
        else:
            # เลือก High
            self.normal_speed_button.selected = False
            self.high_speed_button.selected = True

            # อัพเดตสีทันทีไม่ต้องมี delay
            self.normal_speed_button.config(
                fg=self.theme["text_dim"], bg=self.theme["button_bg"]
            )
            self.high_speed_button.config(
                fg=self.theme["highlight"], bg=self.theme["button_bg"]
            )

        # เรียก callback ถ้ามี
        if hasattr(self, "speed_callback"):
            self.speed_callback(speed_mode)

        else:
            # เลือก High
            self.normal_speed_button.selected = False
            self.high_speed_button.selected = True

            # อัพเดตสีด้วยเอฟเฟกต์
            def update_colors():
                # Normal
                self.normal_speed_button.config(
                    fg=self.theme["text_dim"], bg=self.theme["button_bg"]
                )
                # High
                self.high_speed_button.config(
                    fg=self.theme["highlight"], bg=self.theme["button_bg"]
                )

            # เพิ่มเอฟเฟกต์เล็กน้อย
            self.high_speed_button.config(bg=self.theme["accent_light"])
            self.root.after(100, update_colors)

        # เรียก callback ถ้ามี
        if hasattr(self, "speed_callback"):
            self.speed_callback(speed_mode)

    def position_below_main_ui(self):
        """จัดตำแหน่ง Control UI ให้อยู่ด้านล่างของ Main UI"""
        if hasattr(self.root.master, "winfo_x") and hasattr(
            self.root.master, "winfo_y"
        ):
            main_x = self.root.master.winfo_x()
            main_y = self.root.master.winfo_y()
            main_height = self.root.master.winfo_height()

            new_x = main_x
            new_y = main_y + main_height + 5

            self.ui_cache["position_x"] = new_x
            self.ui_cache["position_y"] = new_y

            self.root.geometry(f"+{new_x}+{new_y}")

    def show_window(self):
        """แสดงหน้าต่าง Control UI"""
        if self.root.winfo_exists():
            if self.ui_cache["position_x"] is not None:
                self.restore_cached_position()
            else:
                # เปลี่ยนจาก position_below_main_ui เป็น position_right_of_main_ui
                self.position_right_of_main_ui()
            
            # โหลดสถานะที่บันทึกไว้
            current_areas = self.ui_cache["current_area"].split("+")
            for area in ["A", "B", "C"]:
                self.area_states[area] = area in current_areas
            
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.update_button_highlights()
            self.update_preset_display()

    def restore_cached_position(self):
        """กู้คืนตำแหน่งจากแคช"""
        if (
            self.ui_cache["position_x"] is not None
            and self.ui_cache["position_y"] is not None
        ):
            self.root.geometry(
                f"+{self.ui_cache['position_x']}+{self.ui_cache['position_y']}"
            )

    def position_right_of_main_ui(self):
        """วางตำแหน่งหน้าต่าง Control UI ด้านขวาของ Main UI และจัดขอบล่างให้เท่ากัน"""
        if not hasattr(self, "parent_root"):
            # ถ้าไม่มี parent_root ให้ใช้ root ของตัวเอง (กรณี fallback)
            return
            
        # ขนาดและตำแหน่งของ Main UI
        main_x = self.parent_root.winfo_x()
        main_y = self.parent_root.winfo_y()
        main_width = self.parent_root.winfo_width()
        main_height = self.parent_root.winfo_height()
        
        # ขนาดของ Control UI
        self.root.update_idletasks()  # บังคับให้คำนวณขนาดล่าสุด
        control_width = self.root.winfo_width()
        control_height = self.root.winfo_height()
        
        # คำนวณตำแหน่งใหม่
        new_x = main_x + main_width + 20  # ด้านขวาของ Main UI + 20px
        new_y = main_y + main_height - control_height  # จัดขอบล่างให้เท่ากัน
        
        # กำหนดตำแหน่ง
        self.root.geometry(f"+{new_x}+{new_y}")
        
        # บันทึกตำแหน่งลงแคช
        self.ui_cache["position_x"] = new_x
        self.ui_cache["position_y"] = new_y
    
    def close_window(self):
        """ปิดหน้าต่าง Control UI"""
        if self.root.winfo_exists():
            if self.root.state() != "withdrawn":
                self.root.withdraw()

    def update_display(self, area_string, preset_number=None):
        """
        Updates the Control UI's display based on the state provided,
        typically called by the main application (MBB.py).

        Args:
            area_string (str): The string representing active areas (e.g., "A+B").
            preset_number (int, optional): The preset number that corresponds
                                             to this state, if known. Defaults to None.
        """
        logging.info(
            f"Control_UI received update_display request: areas='{area_string}', preset={preset_number}"
        )
        try:
            # Auto-save already handled by area selection, no need to save here

            # 1. Update internal area_states
            active_areas = area_string.split("+") if area_string else []
            for area in ["A", "B", "C"]:
                self.area_states[area] = area in active_areas

            # 2. Update current_preset if provided and different
            if preset_number is not None and self.current_preset != preset_number:
                if 1 <= preset_number <= self.max_presets:
                    self.current_preset = preset_number
                    logging.info(
                        f"Control_UI preset updated to {preset_number} by external call."
                    )
                else:
                    logging.warning(
                        f"Received invalid preset number {preset_number} in update_display."
                    )

            # 3. Refresh UI elements
            # *** แก้ไขจุดนี้: ย้ายการเรียก update_preset_display() ออกไป ให้ update_preset_buttons() จัดการ ***
            self.update_preset_buttons()  # Updates P1-P5 buttons AND the preset label
            self.update_button_highlights()  # Updates A,B,C buttons and checks unsaved status

            # Ensure the UI reflects the potentially updated 'has_unsaved_changes' status
            # (update_button_highlights ควรจะจัดการสีปุ่ม Save แล้ว แต่เราตรวจสอบอีกครั้งเพื่อความแน่ใจ)
            preset_data = self.settings.get_preset(self.current_preset)
            preset_areas_str = preset_data.get("areas", "A+B") if preset_data else "A+B"

            # Auto-save handles everything - no need to track unsaved changes
            # coords_changed is always False since auto-save immediately saves any changes
            coords_changed = False
            areas_changed = area_string != preset_areas_str

            # Keep has_unsaved_changes for compatibility but it's always False with auto-save
            self.has_unsaved_changes = False

            # อัพเดทสวิตช์ Click Translate ด้วย
            if hasattr(self, "click_translate_var"):
                click_translate_enabled = self.settings.get("enable_click_translate", False)
                self.click_translate_var.set(click_translate_enabled)
                
                # อัพเดท UI ของปุ่ม FORCE ถ้ามี
                force_button = getattr(self, "force_button", None)
                if force_button:
                    if click_translate_enabled:
                        force_button.config(bg="#e74c3c")  # สีแดงเข้ม
                        force_button.config(text="1-CLICK")
                    else:
                        force_button.config(bg=self.theme.get("accent", "#00aaff"))
                        force_button.config(text="FORCE")
            
            # Save button removed - auto-save is now always active

            logging.info(
                f"Control_UI display updated. Areas: {area_string}, Preset: {self.current_preset}, Unsaved: {self.has_unsaved_changes}"
            )

        except Exception as e:
            logging.error(f"Error in Control_UI.update_display: {e}")
            import traceback

            traceback.print_exc()

    def update_button_highlights(self):
        """Update button colors, handle role locking, and update save button state."""
        button_map = {
            "A": getattr(self, "button_a", None),
            "B": getattr(self, "button_b", None),
            "C": getattr(self, "button_c", None),
        }

        try:
            # ดึงสีและ Role ปัจจุบัน
            current_preset_role = self.settings.get_preset_role(self.current_preset)
            # แก้ไขเงื่อนไขตรงนี้: ให้ preset 4 และ 5 เป็น custom เสมอ
            is_custom_preset = current_preset_role == "custom" or self.current_preset >= 4

            active_bg = self.theme.get("accent", "#6c5ce7")
            active_fg = self.theme.get("text", "#ffffff")
            inactive_bg = self.theme.get("button_bg", "#262637")
            inactive_fg = self.theme.get("text_dim", "#b2b2b2")
            disabled_bg = "#303030" # สีสำหรับปุ่ม Area ที่ถูกล็อค
            disabled_fg = "#606060"
            theme_text_color = self.theme.get("text", "#ffffff") # สีข้อความทั่วไปสำหรับปุ่ม Save

            # --- อัพเดตสถานะปุ่ม Area A, B, C และการล็อค ---
            for area, button in button_map.items():
                if button and button.winfo_exists():
                    is_active = self.area_states.get(area, False)
                    button.selected = is_active

                    # ล็อคปุ่ม Area ถ้าไม่ใช่ Custom Preset
                    if not is_custom_preset:
                        button.configure(
                            bg=disabled_bg, fg=disabled_fg,
                            relief="flat", state=tk.DISABLED, cursor=""
                        )
                    else:
                        # ปลดล็อคปุ่ม Area ถ้าเป็น Custom Preset
                        button.configure(state=tk.NORMAL, cursor="hand2")
                        if is_active:
                            button.configure(bg=active_bg, fg=active_fg, relief="sunken")
                        else:
                            button.configure(bg=inactive_bg, fg=inactive_fg, relief="flat")

            # --- ตรวจสอบสถานะ unsaved changes ---
            # 1. เปรียบเทียบ Area String ปัจจุบันกับใน Preset
            active_areas_list = self.get_active_areas()
            current_area_str = "+".join(sorted(active_areas_list)) if active_areas_list else "A" # ใช้ A ถ้าไม่มีอะไรเลือกเลย

            preset_data = self.settings.get_preset(self.current_preset)
            preset_areas_list = []
            if preset_data and isinstance(preset_data.get("areas"), str):
                 preset_areas_list = sorted(preset_data["areas"].split("+"))
            preset_areas_str = "+".join(preset_areas_list) if preset_areas_list else ""

            areas_changed = current_area_str != preset_areas_str

            # 2. With auto-save, coordinates are always saved immediately
            # No need to check for coordinate changes
            coords_changed = False

            # 3. Keep has_unsaved_changes for compatibility but it's always False with auto-save
            self.has_unsaved_changes = False

            if areas_changed:
                 logging.debug(f"Area string difference detected ('{current_area_str}' vs '{preset_areas_str}')")
            # coords_changed is always False with auto-save, no need to check

            # Save button removed - auto-save is now always active

            logging.debug(
                f"Updated highlights. Role: '{current_preset_role}'. Areas: {current_area_str}. PresetAreas: {preset_areas_str}. Preset: {self.current_preset}. Unsaved: {self.has_unsaved_changes}"
            )

        except Exception as e:
            logging.error(f"Error in update_button_highlights: {e}")
            import traceback
            traceback.print_exc()

    def get_active_areas(self):
        """Return list of active areas in correct order"""
        return [area for area in ["A", "B", "C"] if self.area_states[area]]

    # check_coordinate_changes method removed - auto-save is always active
    
    def setup_bindings(self):
        """Setup window movement bindings and auto-hide functionality"""
        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<ButtonRelease-1>", self.stop_move)
        self.root.bind("<B1-Motion>", self.on_drag)
        
        # เพิ่ม auto-hide bindings
        self.root.bind("<FocusOut>", self.on_focus_out)
        self.root.bind("<FocusIn>", self.on_focus_in)

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        self.x = None
        self.y = None

    def on_drag(self, event):
        """จัดการการลากหน้าต่าง"""
        if self.x is not None and self.y is not None:
            deltax = event.x - self.x
            deltay = event.y - self.y
            x = self.root.winfo_x() + deltax
            y = self.root.winfo_y() + deltay
            self.root.geometry(f"+{x}+{y}")

            self.ui_cache["position_x"] = x
            self.ui_cache["position_y"] = y

    def area_button_click(self, area):
        """Toggle area on/off and update UI, then notify MBB.py
        Args:
            area (str): พื้นที่ที่ถูกคลิก (A, B, หรือ C)
        """
        # --- เพิ่มการตรวจสอบ Role ---
        current_preset_role = self.settings.get_preset_role(self.current_preset)
        # แก้ไขเงื่อนไขการตรวจสอบให้สอดคล้องกับ update_button_highlights
        if current_preset_role != "custom" and self.current_preset < 4:
            logging.info(f"Area button '{area}' click ignored. Preset role '{current_preset_role}' is locked.")
            return # ไม่ทำอะไรถ้า Preset ถูกล็อค
        # --- จบการตรวจสอบ Role ---

        try:
            # สลับสถานะของพื้นที่ที่คลิก
            new_state = not self.area_states[area]

            # ตรวจสอบว่าจะมีอย่างน้อย 1 พื้นที่เปิดอยู่เสมอ
            other_active_areas = any(
                self.area_states[a] for a in ["A", "B", "C"] if a != area
            )

            # อนุญาตให้ปิดได้ถ้ายังมีพื้นที่อื่นเปิดอยู่ หรือถ้ากำลังจะเปิดพื้นที่นี้
            if new_state or other_active_areas:
                # 1. อัพเดท State ภายใน Control_UI
                self.area_states[area] = new_state

                # 2. อัพเดท UI ของ Control_UI ทันที (จะมีการตั้ง has_unsaved_changes ข้างใน)
                self.update_button_highlights()

                # 3. รวบรวมพื้นที่ที่เปิดใช้งาน *หลังจาก* อัพเดท state แล้ว
                active_areas = self.get_active_areas() # ได้เป็น list เช่น ['A', 'B']

                # 4. แจ้งการเปลี่ยนแปลงพื้นที่ไปยัง MBB.py ผ่าน Callback
                if active_areas and self.switch_area_callback:
                    # ส่งพารามิเตอร์ preset_number_override ด้วยเพื่อป้องกันการสลับไป preset เริ่มต้น
                    self.switch_area_callback(active_areas, preset_number_override=self.current_preset)
                    
                    # FIX: เพิ่ม auto-save เมื่อเปลี่ยนพื้นที่จาก UI
                    self.auto_save_current_preset()
                    
                    # 5. กระตุ้นให้ MBB.py ทำการแปลใหม่ (ถ้า callback มีอยู่)
                    if self.previous_dialog_callback:
                        self.safe_previous_dialog()

                logging.info(
                    f"Area {area} toggled. Control UI state updated. Active areas requested: {self.get_active_areas()}"
                )
            else:
                # กรณีพยายามปิดปุ่มสุดท้าย ไม่ทำอะไร
                logging.warning(f"Cannot deactivate the last active area ({area}).")

        except Exception as e:
            logging.error(f"Error in area_button_click: {e}")
            import traceback
            traceback.print_exc()

    def capture_screen(self):
        """Capture screen function"""
        try:
            from screen_capture import ScreenCapture

            capturer = ScreenCapture()
            filepath = capturer.capture_primary_screen()
            if filepath:
                self.show_capture_feedback()
        except Exception as e:
            logging.error(f"Screen capture error: {e}")

    def show_capture_feedback(self):
        """Show capture feedback"""
        feedback = tk.Toplevel(self.root)
        feedback.overrideredirect(True)
        feedback.configure(bg="black")
        x = self.root.winfo_x() + self.camera_button.winfo_x()
        y = self.root.winfo_y() + self.camera_button.winfo_y()
        tk.Label(
            feedback,
            text="Captured!",
            fg="lime",
            bg="black",
            font=("Nasalization Rg", 8),
        ).pack(padx=10, pady=5)
        feedback.geometry(f"+{x+30}+{y}")
        feedback.after(1000, feedback.destroy)

    # === AUTO-HIDE FUNCTIONALITY ===
    
    def on_focus_out(self, event):
        """เมื่อ Control UI สูญเสีย focus - เตรียม auto-hide"""
        if self.is_closing:
            return
        
        # ตั้งค่า timer สำหรับ auto-hide (delay 200ms)
        if self.auto_hide_timer:
            self.root.after_cancel(self.auto_hide_timer)
        
        self.auto_hide_timer = self.root.after(200, self.check_and_auto_hide)
    
    def on_focus_in(self, event):
        """เมื่อ Control UI ได้รับ focus กลับมา - ยกเลิก auto-hide"""
        if self.auto_hide_timer:
            self.root.after_cancel(self.auto_hide_timer)
            self.auto_hide_timer = None
    
    def check_and_auto_hide(self):
        """ตรวจสอบและซ่อนหน้าต่าง Control UI อัตโนมัติ"""
        try:
            if self.is_closing or not self.root.winfo_exists():
                return
            
            # ตรวจสอบว่า mouse pointer อยู่ในขอบเขตของ Control UI หรือไม่
            mouse_x = self.root.winfo_pointerx()
            mouse_y = self.root.winfo_pointery()
            win_x = self.root.winfo_rootx()
            win_y = self.root.winfo_rooty()
            win_width = self.root.winfo_width()
            win_height = self.root.winfo_height()
            
            # ถ้า mouse อยู่นอกขอบเขต Control UI -> auto-hide
            if not (win_x <= mouse_x <= win_x + win_width and 
                    win_y <= mouse_y <= win_y + win_height):
                self.auto_hide()
        
        except Exception as e:
            import logging
            logging.error(f"Error in check_and_auto_hide: {e}")
        finally:
            self.auto_hide_timer = None
    
    def auto_hide(self):
        """ซ่อนหน้าต่าง Control UI และแจ้ง MBB.py ผ่าน callback"""
        if self.is_closing:
            return
        
        self.is_closing = True
        
        try:
            # แจ้ง MBB.py ผ่าน callback ก่อนปิด
            if self.on_close_callback:
                self.on_close_callback()
            
            # ซ่อนหน้าต่าง
            self.close_window()
            
        except Exception as e:
            import logging
            logging.error(f"Error in auto_hide: {e}")
        finally:
            # Reset closing flag หลัง delay เล็กน้อย
            self.root.after(100, lambda: setattr(self, 'is_closing', False))

    def update_translation_status(self, is_translating):
        """อัปเดตสถานะการแปลและปรับสภาพของปุ่ม Force"""
        self.is_translating = is_translating
        self.update_force_button_state()

    def update_force_button_state(self):
        """อัปเดตสถานะของปุ่ม Force ตามสถานะการแปล"""
        if hasattr(self, "force_button") and self.force_button.winfo_exists():
            if self.is_translating:
                # สถานะแปลเปิด - ปุ่มใช้ได้
                self.force_button.config(
                    state="normal",
                    bg=self.theme.get("button_bg", "#262637"),
                    fg=self.theme.get("fg", "white"),
                    cursor="hand2"
                )
            else:
                # สถานะแปลปิด - ปุ่มเป็นสีเทาและใช้ไม่ได้
                self.force_button.config(
                    state="disabled",
                    bg="#666666",  # สีเทา
                    fg="#999999",  # ข้อความสีเทาอ่อน
                    cursor="arrow"
                )

    def safe_previous_dialog(self):
        """
        เรียก previous dialog callback เพื่อแสดง dialog ก่อนหน้า
        """
        if callable(self.previous_dialog_callback):
            logging.info("Previous dialog triggered")
            self.previous_dialog_callback()


if __name__ == "__main__":
    root = tk.Tk()

    def dummy_previous():
        print("Previous dialog triggered")

    def dummy_switch(area):
        print(f"Switched to area {area}")

    app = Control_UI(root, dummy_previous, dummy_switch, Settings())
    root.mainloop()
