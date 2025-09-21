import logging
import tkinter as tk
from PIL import Image, ImageTk
from appearance import appearance_manager


class MiniUI:
    def __init__(self, root, show_main_ui_callback):
        self.root = root
        self.show_main_ui_callback = show_main_ui_callback
        self.blink_interval = 500
        self.blink_timer = None
        self.mini_ui = None
        self.blink_icon = None
        self.black_icon = None
        self.mini_ui_blink_label = None
        self.mini_loading_label = None  # <-- เพิ่มบรรทัดนี้
        self.mini_ui_blinking = False
        self.is_translating = False
        self.toggle_translation_callback = None  # สำหรับเก็บ callback จาก main UI
        self.load_icons()
        self.create_mini_ui()

    def load_icons(self):
        # เพิ่มขนาดไอคอนจาก 10x10 เป็น 15x15
        icon_size = (15, 15)
        self.blink_icon = ImageTk.PhotoImage(
            Image.open("assets/red_icon.png").resize(icon_size)
        )
        self.black_icon = ImageTk.PhotoImage(
            Image.open("assets/black_icon.png").resize(icon_size)
        )
        # เพิ่มไอคอน expand สำหรับปุ่ม toggle (ขนาดใหญ่ขึ้น 2 เท่า)
        toggle_icon_size = (32, 32)
        self.expand_icon = ImageTk.PhotoImage(
            Image.open("assets/expand.png").resize(toggle_icon_size)
        )

    def create_mini_ui(self):
        if (
            self.mini_ui and self.mini_ui.winfo_exists()
        ):  # Check if exists before destroying
            self.mini_ui.destroy()

        self.mini_ui = tk.Toplevel(self.root)
        # เพิ่มขนาดจากเดิมเป็น 180x40 เพื่อให้มีพื้นที่เพียงพอสำหรับทุกองค์ประกอบ
        self.mini_ui.geometry("200x48")  # อาจต้องปรับขนาดอีกครั้งถ้า loading label ทำให้แน่นไป
        self.mini_ui.overrideredirect(True)
        self.mini_ui.attributes("-topmost", True)
        # ตรวจสอบว่า appearance_manager.bg_color มีค่าหรือไม่
        bg_c = getattr(
            appearance_manager, "bg_color", "#1a1a1a"
        )  # ใช้ #1a1a1a เป็น default
        self.mini_ui.configure(bg=bg_c)
        self.mini_ui.withdraw()

        # สร้าง frame หลักพร้อมขอบบาง
        main_frame = tk.Frame(
            self.mini_ui,
            bg=bg_c,
            highlightthickness=1,
            highlightbackground="#333333",
        )
        main_frame.pack(expand=True, fill=tk.BOTH, padx=1, pady=1)

        # ปุ่ม toggle ใช้ไอคอน expand แทนข้อความ
        toggle_button = tk.Button(
            main_frame,
            image=self.expand_icon,
            command=self.show_main_ui_callback,
            bg=bg_c,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        toggle_button.pack(side=tk.LEFT, padx=(6, 0))  # เพิ่ม padding ด้านซ้าย

        # ปุ่ม Start/Stop ที่ปรับปรุงแล้ว
        self.start_button = tk.Button(
            main_frame,
            text="Start",
            command=self._handle_toggle_translation,
            bg=bg_c,
            fg="white",
            bd=0,
            highlightthickness=0,
            font=("FC Minimal", 12, "bold"),  # เพิ่มขนาดฟอนต์จาก 10 เป็น 12
            activebackground="#404040",
            activeforeground="white",
            width=10,  # เพิ่มความกว้างจาก 8 เป็น 10
            cursor="hand2",
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        # *** เพิ่ม Label สำหรับ Loading Indicator ***
        self.mini_loading_label = tk.Label(
            main_frame,
            text="",  # เริ่มต้นด้วยข้อความว่าง
            bg=bg_c,
            fg="#FFA500",  # สีส้มสำหรับ loading
            font=("Arial", 10, "bold"),
        )
        self.mini_loading_label.pack(side=tk.LEFT, padx=(0, 5))  # วางไว้ทางซ้ายของไฟสถานะ
        # *** จบส่วนที่เพิ่ม ***

        # สร้าง frame เฉพาะสำหรับไฟสถานะเพื่อให้แสดงผลแน่นอน
        status_frame = tk.Frame(
            main_frame,
            bg=bg_c,
            width=25,  # กำหนดความกว้างชัดเจน
            height=25,  # กำหนดความสูงชัดเจน
        )
        # ใช้ pack แทน place เพื่อให้จัดเรียงง่ายขึ้นเมื่อมี loading label เพิ่มมา
        status_frame.pack(side=tk.RIGHT, padx=(0, 10))  # ลด padx ขวาลงเล็กน้อย
        status_frame.pack_propagate(False)  # ป้องกันไม่ให้ขนาดเปลี่ยน

        # ไฟสถานะการแปล - ใส่ใน status_frame แทน
        self.mini_ui_blink_label = tk.Label(
            status_frame, image=self.black_icon, bg=bg_c
        )
        # ใช้ pack แทน place เพื่อให้ง่ายขึ้น
        self.mini_ui_blink_label.pack(expand=True, fill=tk.BOTH)

        # Hover effects สำหรับปุ่ม Start/Stop
        def on_enter(e):
            if not self.is_translating:
                self.start_button.config(bg="#666666")
            else:
                # อาจจะทำให้เข้มขึ้นเล็กน้อยเมื่อ stop
                self.start_button.config(bg="#404040")

        def on_leave(e):
            # กลับไปใช้สีพื้นหลังหลักเสมอ
            current_bg_color = getattr(appearance_manager, "bg_color", "#1a1a1a")
            self.start_button.config(bg=current_bg_color)

        # Hover effects สำหรับปุ่ม toggle
        def on_toggle_enter(e):
            toggle_button.config(bg="#666666")

        def on_toggle_leave(e):
            current_bg_color = getattr(appearance_manager, "bg_color", "#1a1a1a")
            toggle_button.config(bg=current_bg_color)

        self.start_button.bind("<Enter>", on_enter)
        self.start_button.bind("<Leave>", on_leave)
        toggle_button.bind("<Enter>", on_toggle_enter)
        toggle_button.bind("<Leave>", on_toggle_leave)

        # Event bindings
        self.mini_ui.bind("<Button-1>", self.start_move_mini_ui)
        self.mini_ui.bind("<B1-Motion>", self.do_move_mini_ui)
        self.mini_ui.bind("<Double-Button-1>", lambda e: self.show_main_ui_from_mini())

        # ทำให้ขอบมน
        self.mini_ui.after(100, lambda: self.apply_rounded_corners())

    def apply_rounded_corners(self):
        """ทำให้หน้าต่าง Mini UI มีขอบโค้งมน"""
        try:
            import win32gui
            import win32con
            import win32api
            from ctypes import windll, byref, sizeof, c_int

            # รอให้หน้าต่างสร้างเสร็จ
            self.mini_ui.update_idletasks()

            # ดึง window handle
            hwnd = windll.user32.GetParent(self.mini_ui.winfo_id())

            # ลบ caption และ thick frame
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            style &= ~win32con.WS_CAPTION
            style &= ~win32con.WS_THICKFRAME
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

            # สร้างรูปร่างสี่เหลี่ยมขอบมน
            rgnw = self.mini_ui.winfo_width()
            rgnh = self.mini_ui.winfo_height()
            region = win32gui.CreateRoundRectRgn(0, 0, rgnw, rgnh, 12, 12)
            win32gui.SetWindowRgn(hwnd, region, True)
        except Exception as e:
            print(f"Error applying rounded corners: {e}")

    def show_loading(self):
        """แสดง loading indicator ใน Mini UI"""
        try:
            if hasattr(self, "mini_loading_label") and self.mini_loading_label:
                # ตรวจสอบว่า widget ยังมีอยู่
                if self.mini_loading_label.winfo_exists():
                    self.mini_loading_label.config(text="...")  # หรือใช้สัญลักษณ์อื่น เช่น ⏳
        except tk.TclError:
            # Widget ถูกทำลายแล้ว - ไม่ต้องทำอะไร
            pass
        except Exception as e:
            print(f"Error in show_loading: {e}")

    def hide_loading(self):
        """ซ่อน loading indicator ใน Mini UI"""
        try:
            if hasattr(self, "mini_loading_label") and self.mini_loading_label:
                # ตรวจสอบว่า widget ยังมีอยู่
                if self.mini_loading_label.winfo_exists():
                    self.mini_loading_label.config(text="")
        except tk.TclError:
            # Widget ถูกทำลายแล้ว - ไม่ต้องทำอะไร
            pass
        except Exception as e:
            print(f"Error in hide_loading: {e}")

    # เมธอด lighten_color ควรมีอยู่ในคลาส MiniUI ด้วย ถ้ายังไม่มี
    def lighten_color(self, color, factor=1.3):
        """ทำให้สีอ่อนลงตามค่า factor (เหมือนใน control_ui)"""
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

    def add_highlight_border(self):
        """เพิ่มเอฟเฟกต์ขอบสีฟ้าเมื่อ Mini UI ปรากฏ"""
        try:
            # หา main frame (frame แรกใน mini_ui)
            main_frame = None
            for child in self.mini_ui.winfo_children():
                if isinstance(child, tk.Frame):
                    main_frame = child
                    break

            if main_frame:
                # เก็บสีขอบเดิม
                original_color = main_frame.cget("highlightbackground")
                original_thickness = main_frame.cget("highlightthickness")

                # เปลี่ยนเป็นขอบสีฟ้าหนาขึ้น - เพิ่มความหนาเป็น 3 (จากเดิม 2)
                main_frame.configure(
                    highlightthickness=3, highlightbackground="#00FFFF"
                )

                # ตั้งเวลาเปลี่ยนกลับหลังจาก 1.5 วินาที (เพิ่มจาก 1 วินาที)
                self.mini_ui.after(
                    1500,
                    lambda: main_frame.configure(
                        highlightthickness=original_thickness,
                        highlightbackground=original_color,
                    ),
                )
        except Exception as e:
            print(f"Error adding highlight effect: {e}")

    def update_theme(self, accent_color=None, highlight_color=None):
        """อัพเดท UI ของ MiniUI ด้วยสีธีมใหม่"""
        try:
            # ดึงค่าสีล่าสุดจาก appearance_manager ถ้าไม่ได้ส่งมา
            if accent_color is None:
                accent_color = appearance_manager.get_accent_color()
            if highlight_color is None:
                highlight_color = appearance_manager.get_highlight_color()
            bg_c = appearance_manager.bg_color  # สีพื้นหลังหลัก

            if not self.mini_ui or not self.mini_ui.winfo_exists():
                return

            # อัพเดทพื้นหลังหน้าต่างและ Frame หลัก
            self.mini_ui.configure(bg=bg_c)
            main_frame = None
            for child in self.mini_ui.winfo_children():
                if isinstance(child, tk.Frame):
                    main_frame = child
                    main_frame.configure(bg=bg_c)
                    # อาจจะต้องอัพเดทขอบด้วย ถ้าใช้ highlightbackground
                    # main_frame.configure(highlightbackground="#333333") # หรือสีขอบตามธีม
                    break

            if main_frame:
                toggle_button = None
                status_frame = None
                # ค้นหา Widgets ภายใน main_frame
                for widget in main_frame.winfo_children():
                    if isinstance(widget, tk.Button) and widget.cget("text") == "⇄":
                        toggle_button = widget
                        widget.configure(
                            fg=highlight_color, bg=bg_c, activebackground=bg_c
                        )  # ตั้งค่าพื้นหลังปุ่มด้วย
                    elif isinstance(widget, tk.Button) and widget == getattr(
                        self, "start_button", None
                    ):
                        widget.configure(
                            bg=bg_c, activebackground=accent_color
                        )  # ตั้งค่าพื้นหลังปุ่มด้วย
                    elif isinstance(widget, tk.Label) and widget == getattr(
                        self, "mini_loading_label", None
                    ):
                        widget.configure(bg=bg_c)  # ตั้งค่าพื้นหลัง label loading
                    elif (
                        isinstance(widget, tk.Frame)
                        and len(widget.winfo_children()) > 0
                        and isinstance(widget.winfo_children()[0], tk.Label)
                        and hasattr(widget.winfo_children()[0], "image")
                    ):
                        # สมมติว่า frame นี้คือ status_frame ที่มี blink_label อยู่ข้างใน
                        status_frame = widget
                        widget.configure(bg=bg_c)
                        if (
                            hasattr(self, "mini_ui_blink_label")
                            and self.mini_ui_blink_label
                        ):
                            self.mini_ui_blink_label.configure(bg=bg_c)

                # --- อัพเดท Hover Effects ---
                # ต้องนิยาม function ใหม่ภายในเพื่อให้ใช้ค่าสีล่าสุด
                toggle_fg_color = highlight_color  # สีปกติของปุ่ม toggle
                toggle_hover_fg = self.lighten_color(
                    toggle_fg_color, 1.5
                )  # ทำให้สีฟ้าสว่างขึ้น

                def on_enter(e):
                    if not self.is_translating:
                        self.start_button.config(bg="#666666")
                    else:
                        self.start_button.config(bg="#404040")  # สีเข้มขึ้นเมื่อกด Stop

                def on_leave(e):
                    current_bg_color = appearance_manager.bg_color  # ดึงสีล่าสุด
                    self.start_button.config(bg=current_bg_color)

                def on_toggle_enter(e):
                    if toggle_button:  # ตรวจสอบว่าหาปุ่มเจอ
                        toggle_button.config(bg="#666666", fg=toggle_hover_fg)

                def on_toggle_leave(e):
                    current_bg_color = appearance_manager.bg_color  # ดึงสีล่าสุด
                    if toggle_button:  # ตรวจสอบว่าหาปุ่มเจอ
                        toggle_button.config(bg=current_bg_color, fg=toggle_fg_color)

                # Re-bind hover effects ให้ใช้ function ใหม่ที่รู้ค่าสีล่าสุด
                if hasattr(self, "start_button"):
                    self.start_button.unbind("<Enter>")
                    self.start_button.unbind("<Leave>")
                    self.start_button.bind("<Enter>", on_enter)
                    self.start_button.bind("<Leave>", on_leave)

                if toggle_button:
                    toggle_button.unbind("<Enter>")
                    toggle_button.unbind("<Leave>")
                    toggle_button.bind("<Enter>", on_toggle_enter)
                    toggle_button.bind("<Leave>", on_toggle_leave)

            logging.info("MiniUI theme updated.")

        except Exception as e:
            print(f"Error updating mini UI theme: {e}")
            logging.error(f"Error updating mini UI theme: {e}")

    def _handle_toggle_translation(self):
        """จัดการการกดปุ่ม Start/Stop โดยเรียกใช้ callback จาก main UI"""
        if self.toggle_translation_callback:
            self.toggle_translation_callback()

    def update_translation_status(self, is_translating):
        """อัพเดทสถานะการแปลและ UI"""
        try:
            self.is_translating = is_translating
            self.mini_ui_blinking = is_translating

            if is_translating:
                self.start_button.config(text="Stop", bg=appearance_manager.bg_color)
                # ตรวจสอบว่า mini_ui_blink_label มีอยู่จริงก่อนเริ่ม blink
                try:
                    if (
                        hasattr(self, "mini_ui_blink_label")
                        and self.mini_ui_blink_label.winfo_exists()
                    ):
                        self.start_blinking()
                except tk.TclError:
                    pass  # Widget ถูกทำลายแล้ว
            else:
                self.start_button.config(text="Start", bg=appearance_manager.bg_color)
                self.stop_blinking()

            # เพิ่มการรีเฟรช mini UI เพื่อให้การเปลี่ยนแปลงแสดงผลทันที
            try:
                if hasattr(self, "mini_ui") and self.mini_ui.winfo_exists():
                    self.mini_ui.update_idletasks()
            except tk.TclError:
                pass  # Widget ถูกทำลายแล้ว
        except tk.TclError:
            # หากเกิดข้อผิดพลาดใดๆ ในการเข้าถึง widget
            pass
        except Exception as e:
            print(f"Error in update_translation_status: {e}")

    def set_toggle_translation_callback(self, callback):
        """ตั้งค่า callback สำหรับการ toggle การแปล"""
        self.toggle_translation_callback = callback

    def start_blinking(self):
        """แสดงไฟแดงนิ่งๆ แทนการกระพริบ เมื่อกำลังแปล"""
        try:
            # หยุดการกระพริบที่อาจค้างอยู่ก่อน
            self.stop_blinking()

            # ตั้งค่าสถานะว่ากำลังทำงาน แต่ไม่ได้กระพริบแล้ว
            self.mini_ui_blinking = True

            # ตรวจสอบว่า mini_ui_blink_label มีอยู่จริง
            if (
                hasattr(self, "mini_ui_blink_label")
                and self.mini_ui_blink_label.winfo_exists()
            ):
                # แสดงไฟแดงนิ่งๆ เมื่อเริ่มการแปล
                self.mini_ui_blink_label.config(image=self.blink_icon)
        except tk.TclError:
            # Widget ถูกทำลายแล้ว
            pass
        except Exception as e:
            print(f"Error in start_blinking: {e}")

    def stop_blinking(self):
        """หยุดการทำงานและเปลี่ยนไฟกลับเป็นสีดำ"""
        try:
            self.mini_ui_blinking = False

            # ยกเลิกการกระพริบที่อาจกำลังทำงานอยู่ (สำหรับความเข้ากันได้กับโค้ดเดิม)
            if hasattr(self, "blink_timer_id") and self.blink_timer_id:
                try:
                    if (
                        hasattr(self, "mini_ui")
                        and self.mini_ui
                        and self.mini_ui.winfo_exists()
                    ):
                        self.mini_ui.after_cancel(self.blink_timer_id)
                except tk.TclError:
                    pass  # Widget ถูกทำลายแล้ว
                except Exception:
                    pass  # ถ้ายกเลิกไม่ได้ ก็ไม่เป็นไร
                self.blink_timer_id = None

            # รีเซ็ตรูปภาพกลับเป็นสีดำ
            if (
                hasattr(self, "mini_ui_blink_label")
                and self.mini_ui_blink_label.winfo_exists()
            ):
                self.mini_ui_blink_label.config(image=self.black_icon)
        except tk.TclError:
            # Widget ถูกทำลายแล้ว
            pass
        except Exception as e:
            print(f"Error in stop_blinking: {e}")

    def start_move_mini_ui(self, event):
        """เริ่มการเคลื่อนย้ายหน้าต่าง"""
        self.mini_x = event.x_root - self.mini_ui.winfo_x()
        self.mini_y = event.y_root - self.mini_ui.winfo_y()

    def do_move_mini_ui(self, event):
        """ทำการเคลื่อนย้ายหน้าต่าง"""
        x = event.x_root - self.mini_x
        y = event.y_root - self.mini_y
        self.mini_ui.geometry(f"+{x}+{y}")

    def show_main_ui_from_mini(self):
        """สลับกลับไปแสดง main UI"""
        if hasattr(self, "mini_ui"):
            # บันทึกตำแหน่ง mini UI ก่อนซ่อน
            self.mini_ui.withdraw()
        self.show_main_ui_callback()

    def position_at_center_of_main(self, main_x, main_y, main_width, main_height):
        """จัดตำแหน่ง mini UI ให้อยู่ตรงตำแหน่งเดียวกับ main UI"""
        # ใช้ตำแหน่งเดียวกันกับ main UI แทนการอยู่ตรงกลาง
        self.mini_ui.geometry(f"+{main_x}+{main_y}")

        # เพิ่มเอฟเฟกต์ขอบไฮไลท์
        self.add_highlight_border()

    def blink_mini_ui(self):
        """จัดการการกระพริบของไฟสถานะ"""
        if (
            self.mini_ui_blinking
            and hasattr(self, "mini_ui")
            and self.mini_ui
            and self.mini_ui.winfo_exists()
        ):
            if (
                hasattr(self, "mini_ui_blink_label")
                and self.mini_ui_blink_label.winfo_exists()
            ):
                try:
                    current_image = self.mini_ui_blink_label.cget("image")
                    # กรณีการเปรียบเทียบ image failed ให้ใช้วิธีสลับไปมา
                    new_image = (
                        self.black_icon
                        if self.blink_timer % 2 == 0
                        else self.blink_icon
                    )
                    self.mini_ui_blink_label.config(image=new_image)
                    # เพิ่มการเก็บค่ารอบการกระพริบ
                    self.blink_timer = (
                        0 if not hasattr(self, "blink_timer") else self.blink_timer + 1
                    )

                    # กำหนดการกระพริบรอบถัดไป
                    self.blink_timer_id = self.mini_ui.after(
                        self.blink_interval, self.blink_mini_ui
                    )
                except Exception as e:
                    print(f"Error in blink animation: {e}")
                    # ถ้ามีข้อผิดพลาด ให้หยุดการกระพริบ
                    self.stop_blinking()
            else:
                self.stop_blinking()
        else:
            self.stop_blinking()
