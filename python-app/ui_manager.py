"""
UI Manager Module

Module นี้เป็นระบบรวมศูนย์สำหรับการจัดการ UI และเอฟเฟกต์ทั้งหมดของแอพพลิเคชัน
รวมการทำงานที่เกี่ยวข้องกับการแสดงผลและธีมไว้ในที่เดียว เพื่อความเป็นระเบียบและการดูแลรักษาโค้ดที่ง่ายขึ้น
"""

import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
import os
import json
import logging
from PIL import Image, ImageTk, ImageDraw, ImageEnhance, ImageFilter

# นำเข้า Windows API สำหรับการทำหน้าต่างขอบโค้งมน (ถ้ามี)
try:
    import win32gui
    import win32con
    from ctypes import windll, byref, sizeof, c_int

    HAS_WIN32_SUPPORT = True
except ImportError:
    HAS_WIN32_SUPPORT = False
    logging.warning("win32gui not found. Rounded corners will not be available.")


class UIManager:
    """
    ระบบจัดการ UI แบบรวมศูนย์สำหรับ MagicBabel
    รวมการจัดการธีม เอฟเฟกต์ และคอมโพเนนท์ UI ต่างๆ
    """

    # ค่าเริ่มต้นของธีม
    DEFAULT_THEMES = {
        "default": {
            "name": "Default",
            "bg_color": "#1a1a1a",
            "accent_color": "#6c5ce7",
            "highlight_color": "#00FFFF",
            "secondary_color": "#a29bfe",
            "button_bg": "#262637",
            "accent_light": "#8F7FF8",
            "text_color": "#ffffff",
            "text_dim": "#b2b2b2",
            "error_color": "#e74c3c",
        },
        "purple": {
            "name": "Purple Dream",
            "bg_color": "#1a1a1a",
            "accent_color": "#6c5ce7",
            "highlight_color": "#00FFFF",
            "secondary_color": "#a29bfe",
            "button_bg": "#262637",
            "accent_light": "#8F7FF8",
            "text_color": "#ffffff",
            "text_dim": "#b2b2b2",
            "error_color": "#e74c3c",
        },
        "blue": {
            "name": "Ocean Blue",
            "bg_color": "#1a1a1a",
            "accent_color": "#3498db",
            "highlight_color": "#00FFFF",
            "secondary_color": "#74b9ff",
            "button_bg": "#262637",
            "accent_light": "#5DADE2",
            "text_color": "#ffffff",
            "text_dim": "#b2b2b2",
            "error_color": "#e74c3c",
        },
        "green": {
            "name": "Emerald",
            "bg_color": "#1a1a1a",
            "accent_color": "#2ecc71",
            "highlight_color": "#00FFFF",
            "secondary_color": "#55efc4",
            "button_bg": "#262637",
            "accent_light": "#58D68D",
            "text_color": "#ffffff",
            "text_dim": "#b2b2b2",
            "error_color": "#e74c3c",
        },
        "neon": {
            "name": "Cyber Neon",
            "bg_color": "#0f0f0f",
            "accent_color": "#ff00ff",
            "highlight_color": "#00ffcc",
            "secondary_color": "#00ccff",
            "button_bg": "#1f1f1f",
            "accent_light": "#ff66ff",
            "text_color": "#ffffff",
            "text_dim": "#b2b2b2",
            "error_color": "#ff3333",
        },
    }

    def __init__(self, settings=None):
        """
        สร้าง UI Manager

        Args:
            settings: settings object สำหรับบันทึกการตั้งค่า (optional)
        """
        # ตั้งค่าเริ่มต้น
        self.settings = settings
        self.current_theme = "default"
        self.theme_change_callback = None

        # โหลดธีมที่ผู้ใช้สร้างเอง
        self.custom_themes = {}
        self.load_custom_themes()

        # ค่าสีที่ใช้บ่อย
        self.bg_color = self.get_theme_color("bg_color")
        self.fg_color = self.get_theme_color("text_color")

        # สร้างเมธอด create_rounded_rectangle สำหรับ tk.Canvas
        if not hasattr(tk.Canvas, "create_rounded_rectangle"):
            tk.Canvas.create_rounded_rectangle = self._create_rounded_rectangle_method()

        # เก็บ cache ของรูปภาพ
        self.image_cache = {}

        # ทำให้หน้าต่างปัจจุบันถูกเรียกเข้ามาอีกครั้ง
        self.root = None
        self.active_effects = []

        # บันทึก log
        logging.info("UIManager initialized")

        # โหลดธีมจาก settings ถ้ามี
        if settings and settings.get("theme"):
            theme_name = settings.get("theme")
            if theme_name in self.DEFAULT_THEMES or theme_name in self.custom_themes:
                self.current_theme = theme_name
                logging.info(f"Loaded theme from settings: {theme_name}")

    def _create_rounded_rectangle_method(self):
        """
        สร้างเมธอด create_rounded_rectangle สำหรับ tk.Canvas

        Returns:
            function: เมธอดสำหรับวาดสี่เหลี่ยมมุมโค้ง
        """

        def create_rounded_rectangle(self, x1, y1, x2, y2, radius=25, **kwargs):
            """
            วาดสี่เหลี่ยมมุมโค้งบน Canvas

            Args:
                x1, y1: พิกัดมุมบนซ้าย
                x2, y2: พิกัดมุมล่างขวา
                radius: รัศมีมุมโค้ง
                **kwargs: พารามิเตอร์อื่นๆ เช่น fill, outline

            Returns:
                int: ID ของรูปที่วาด
            """
            points = [
                x1 + radius,
                y1,
                x2 - radius,
                y1,
                x2,
                y1,
                x2,
                y1 + radius,
                x2,
                y2 - radius,
                x2,
                y2,
                x2 - radius,
                y2,
                x1 + radius,
                y2,
                x1,
                y2,
                x1,
                y2 - radius,
                x1,
                y1 + radius,
                x1,
                y1,
            ]

            return self.create_polygon(points, **kwargs, smooth=True)

        return create_rounded_rectangle

    # =============================================================================
    # ส่วนการจัดการธีม (Theme Management)
    # =============================================================================

    def load_custom_themes(self):
        """โหลดธีมที่ผู้ใช้สร้างเอง"""
        try:
            # ถ้ามี settings object ให้โหลดจาก settings
            if self.settings:
                custom_themes = self.settings.get("custom_themes", {})
                if custom_themes:
                    self.custom_themes = custom_themes
                    return

            # ถ้าไม่มี settings ให้โหลดจากไฟล์
            if os.path.exists("custom_themes.json"):
                with open("custom_themes.json", "r") as f:
                    self.custom_themes = json.load(f)
                logging.info(
                    f"Loaded {len(self.custom_themes)} custom themes from file"
                )
        except Exception as e:
            logging.error(f"Error loading custom themes: {e}")

    def save_custom_themes(self):
        """บันทึกธีมที่ผู้ใช้สร้างเอง"""
        try:
            # ถ้ามี settings object ให้บันทึกลง settings
            if self.settings:
                self.settings.set("custom_themes", self.custom_themes)
                self.settings.save_settings()

            # บันทึกลงไฟล์ด้วย
            with open("custom_themes.json", "w") as f:
                json.dump(self.custom_themes, f, indent=4)

            # แจ้งเตือนการบันทึกสำเร็จ
            current_theme_name = ""
            if self.current_theme in self.DEFAULT_THEMES:
                current_theme_name = self.DEFAULT_THEMES[self.current_theme]["name"]
            elif self.current_theme in self.custom_themes:
                current_theme_name = self.custom_themes[self.current_theme]["name"]
            else:
                current_theme_name = self.current_theme

            logging.info(f"บันทึกธีม {current_theme_name} ลงในไฟล์ settings.json แล้ว")
            print(f"บันทึกธีม {current_theme_name} ลงในไฟล์ settings.json แล้ว")

            logging.info(f"Saved {len(self.custom_themes)} custom themes")
            return True
        except Exception as e:
            logging.error(f"Error saving custom themes: {e}")
            return False

    def get_theme_color(self, color_name):
        """
        รับสีจากธีมปัจจุบัน

        Args:
            color_name: ชื่อของสีที่ต้องการ (bg_color, accent_color, ...)

        Returns:
            str: รหัสสี (hex)
        """
        # ตรวจสอบว่าเป็นธีมที่ผู้ใช้สร้างเองหรือไม่
        if self.current_theme in self.custom_themes:
            theme = self.custom_themes[self.current_theme]
        else:
            theme = self.DEFAULT_THEMES.get(
                self.current_theme, self.DEFAULT_THEMES["default"]
            )

        # รับสีจากธีม
        return theme.get(color_name, self.DEFAULT_THEMES["default"][color_name])

    def get_accent_color(self):
        """รับสีหลักของธีมปัจจุบัน"""
        return self.get_theme_color("accent_color")

    def get_highlight_color(self):
        """รับสีไฮไลท์ของธีมปัจจุบัน"""
        return self.get_theme_color("highlight_color")

    def get_current_theme(self):
        """รับชื่อธีมปัจจุบัน"""
        return self.current_theme

    def get_all_themes(self):
        """
        รับรายการธีมทั้งหมด

        Returns:
            dict: รายการของธีมทั้งหมด (default + custom)
        """
        all_themes = {}
        # เพิ่มธีมเริ่มต้น
        for name, theme in self.DEFAULT_THEMES.items():
            all_themes[name] = theme

        # เพิ่มธีมที่ผู้ใช้สร้างเอง
        for name, theme in self.custom_themes.items():
            all_themes[name] = theme

        return all_themes

    def set_theme(self, theme_name):
        """
        เปลี่ยนธีมไปใช้ธีมที่ระบุ

        Args:
            theme_name: ชื่อของธีมที่ต้องการใช้

        Returns:
            bool: True ถ้าเปลี่ยนธีมสำเร็จ, False ถ้าไม่พบธีม
        """
        # ตรวจสอบว่ามีธีมที่ระบุหรือไม่
        if theme_name in self.DEFAULT_THEMES or theme_name in self.custom_themes:
            old_theme = self.current_theme
            self.current_theme = theme_name

            # อัพเดตสีพื้นฐาน
            self.bg_color = self.get_theme_color("bg_color")
            self.fg_color = self.get_theme_color("text_color")

            # บันทึกธีมลง settings
            if self.settings:
                self.settings.set("theme", theme_name)
                self.settings.save_settings()

            # เรียกใช้ callback ถ้ามี
            if self.theme_change_callback:
                self.theme_change_callback()

            logging.info(f"Theme changed from '{old_theme}' to '{theme_name}'")
            return True

        logging.warning(f"Theme '{theme_name}' not found")
        return False

    def set_theme_change_callback(self, callback):
        """
        ตั้งค่า callback function ที่จะถูกเรียกเมื่อมีการเปลี่ยนธีม

        Args:
            callback: ฟังก์ชันที่จะถูกเรียกเมื่อมีการเปลี่ยนธีม
        """
        self.theme_change_callback = callback

    def create_theme(self, name, colors):
        """
        สร้างธีมใหม่

        Args:
            name: ชื่อของธีมใหม่
            colors: dictionary ของสีต่างๆ ในธีม

        Returns:
            bool: True ถ้าสร้างธีมสำเร็จ, False ถ้าไม่สำเร็จ
        """
        try:
            # ตรวจสอบว่ามีสีพื้นฐานครบหรือไม่
            required_colors = ["bg_color", "accent_color", "highlight_color"]
            for color in required_colors:
                if color not in colors:
                    logging.warning(f"Missing required color '{color}' in new theme")
                    return False

            # เพิ่มสีที่ไม่ได้ระบุโดยใช้ค่าเริ่มต้น
            for color, value in self.DEFAULT_THEMES["default"].items():
                if color not in colors and color != "name":
                    colors[color] = value

            # เพิ่มธีมใหม่
            colors["name"] = name
            self.custom_themes[name] = colors

            # บันทึกธีม
            self.save_custom_themes()

            logging.info(f"Created new theme: '{name}'")
            return True
        except Exception as e:
            logging.error(f"Error creating theme: {e}")
            return False

    def delete_theme(self, name):
        """
        ลบธีมที่ระบุ

        Args:
            name: ชื่อของธีมที่ต้องการลบ

        Returns:
            bool: True ถ้าลบธีมสำเร็จ, False ถ้าไม่พบธีม
        """
        if name in self.custom_themes:
            # ถ้ากำลังใช้ธีมที่กำลังจะลบ ให้เปลี่ยนไปใช้ธีมเริ่มต้น
            if self.current_theme == name:
                self.set_theme("default")

            # ลบธีม
            del self.custom_themes[name]

            # บันทึกธีม
            self.save_custom_themes()

            logging.info(f"Deleted theme: '{name}'")
            return True

        # ห้ามลบธีมเริ่มต้น
        if name in self.DEFAULT_THEMES:
            logging.warning(f"Cannot delete default theme: '{name}'")
            return False

        logging.warning(f"Theme '{name}' not found")
        return False

    def update_theme_color(self, color_name, color_value):
        """
        อัพเดตสีในธีมปัจจุบัน

        Args:
            color_name: ชื่อของสีที่ต้องการอัพเดต
            color_value: ค่าสีใหม่

        Returns:
            str: ชื่อธีมที่ถูกอัพเดต หรือสร้างใหม่
        """
        # ตรวจสอบว่าเป็นธีมที่ผู้ใช้สร้างเองหรือไม่
        if self.current_theme in self.DEFAULT_THEMES:
            # ถ้าเป็นธีมเริ่มต้น ให้สร้างธีมใหม่
            custom_theme_name = f"Custom {self.current_theme}"

            # คัดลอกสีจากธีมเดิม
            if self.current_theme in self.DEFAULT_THEMES:
                colors = self.DEFAULT_THEMES[self.current_theme].copy()
            else:
                colors = self.custom_themes[self.current_theme].copy()

            # อัพเดตสีที่เลือก
            colors[color_name] = color_value

            # สร้างธีมใหม่
            self.create_theme(custom_theme_name, colors)

            # เปลี่ยนไปใช้ธีมใหม่
            self.set_theme(custom_theme_name)

            return custom_theme_name
        else:
            # ถ้าเป็นธีมที่ผู้ใช้สร้างเอง ให้อัพเดตสีโดยตรง
            self.custom_themes[self.current_theme][color_name] = color_value

            # อัพเดตธีม
            self.set_theme(self.current_theme)

            # บันทึกธีม
            self.save_custom_themes()

            return self.current_theme

    def lighten_color(self, color, factor=1.3):
        """
        ทำให้สีอ่อนลงตามค่า factor

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
            logging.error(f"Error lightening color: {e}")
            return color

    def darken_color(self, color, factor=0.7):
        """
        ทำให้สีเข้มขึ้นตามค่า factor

        Args:
            color: สีเริ่มต้นในรูปแบบ hex (#RRGGBB)
            factor: ค่าที่ใช้ในการทำให้เข้มขึ้น (ค่าน้อยกว่า 1)

        Returns:
            str: สีที่เข้มขึ้นในรูปแบบ hex
        """
        if not isinstance(color, str) or not color.startswith("#"):
            return color

        try:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)

            r = max(int(r * factor), 0)
            g = max(int(g * factor), 0)
            b = max(int(b * factor), 0)

            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception as e:
            logging.error(f"Error darkening color: {e}")
            return color

    def apply_style(self, widget):
        """
        ใช้สไตล์ของธีมกับวิดเจ็ต

        Args:
            widget: วิดเจ็ตที่ต้องการใช้สไตล์

        Returns:
            ttk.Style: สไตล์ที่สร้างขึ้น
        """
        if isinstance(widget, tk.Tk) or isinstance(widget, tk.Toplevel):
            # ตั้งค่าสีพื้นหลังของหน้าต่าง
            widget.configure(bg=self.bg_color)
            self.root = widget

        # สำหรับการสร้าง ttk style
        style = ttk.Style()

        # กำหนดสีให้วิดเจ็ตต่างๆ
        style.configure(
            "TButton", foreground=self.fg_color, background=self.get_accent_color()
        )
        style.configure("TLabel", foreground=self.fg_color, background=self.bg_color)
        style.configure("TFrame", background=self.bg_color)

        # สร้างสไตล์สำหรับ Switch
        style.configure(
            "Switch.TCheckbutton",
            background=self.bg_color,
            foreground=self.fg_color,
            indicatorsize=20,
            indicatoron=True,
        )

        # สร้างสไตล์เพิ่มเติม
        style.configure(
            "Accent.TButton",
            foreground="white",
            background=self.get_accent_color(),
            padx=8,
            pady=4,
            font=("Nasalization Rg", 10, "bold"),
        )

        style.configure(
            "Secondary.TButton",
            foreground="white",
            background=self.get_theme_color("secondary_color"),
            padx=8,
            pady=4,
            font=("Nasalization Rg", 10),
        )

        # กำหนดสีเมื่อ active
        style.map(
            "Accent.TButton",
            background=[("active", self.lighten_color(self.get_accent_color()))],
        )

        style.map(
            "Secondary.TButton",
            background=[
                ("active", self.lighten_color(self.get_theme_color("secondary_color")))
            ],
        )

        return style

    # =============================================================================
    # ส่วนสร้าง UI Components (UI Component Creation)
    # =============================================================================

    def create_modern_button(
        self,
        parent,
        text,
        command,
        width=95,
        height=30,
        fg=None,
        bg=None,
        hover_bg=None,
        font=None,
        corner_radius=15,
    ):
        """
        สร้างปุ่มโมเดิร์นด้วย Canvas

        Args:
            parent: parent widget
            text: ข้อความบนปุ่ม
            command: ฟังก์ชันที่จะเรียกเมื่อกดปุ่ม
            width: ความกว้างของปุ่ม
            height: ความสูงของปุ่ม
            fg: สีข้อความ (ถ้าไม่ระบุจะใช้สีจากธีม)
            bg: สีพื้นหลัง (ถ้าไม่ระบุจะใช้สีจากธีม)
            hover_bg: สีเมื่อ hover (ถ้าไม่ระบุจะใช้สีจากธีม)
            font: ฟอนต์ (ถ้าไม่ระบุจะใช้ค่าเริ่มต้น)
            corner_radius: รัศมีมุมโค้ง

        Returns:
            tk.Canvas: ปุ่มที่สร้างขึ้น
        """
        # กำหนดค่าสีเริ่มต้นจากธีมปัจจุบัน
        if fg is None:
            fg = self.get_theme_color("text_color")
        if bg is None:
            bg = self.get_theme_color("button_bg")
        if hover_bg is None:
            hover_bg = self.get_accent_color()
        if font is None:
            font = ("Nasalization Rg", 10)

        # สร้าง canvas สำหรับวาดปุ่ม
        canvas = tk.Canvas(
            parent,
            width=width,
            height=height,
            bg=bg,
            highlightthickness=0,
            bd=0,
        )

        # วาดรูปทรงปุ่ม
        button_bg = canvas.create_rounded_rectangle(
            0, 0, width, height, radius=corner_radius, fill=bg, outline=""
        )

        # สร้างข้อความบนปุ่ม
        button_text = canvas.create_text(
            width // 2, height // 2, text=text, fill=fg, font=font
        )

        # ผูกคำสั่งเมื่อคลิก
        canvas.bind("<Button-1>", lambda event: command())

        # เพิ่ม tag สำหรับระบุสถานะ hover
        canvas._is_hovering = False

        # สร้าง hover effect
        def on_enter(event):
            if hasattr(canvas, "selected") and canvas.selected:
                return

            # เก็บสถานะว่ากำลัง hover
            canvas._is_hovering = True

            # อัพเดตสีปุ่ม
            canvas.itemconfig(button_bg, fill=hover_bg)

        def on_leave(event):
            # ยกเลิกสถานะ hover
            canvas._is_hovering = False

            if not hasattr(canvas, "selected") or not canvas.selected:
                # ใช้สีเดิมของปุ่ม
                canvas.itemconfig(button_bg, fill=bg)

        canvas.bind("<Enter>", on_enter)
        canvas.bind("<Leave>", on_leave)

        # เพิ่ม metadata สำหรับการใช้งานภายหลัง
        canvas.selected = False
        canvas.original_bg = bg
        canvas.hover_bg = hover_bg
        canvas.button_bg = button_bg
        canvas.button_text = button_text

        # สร้างฟังก์ชันที่ใช้ itemconfig แทน config
        def update_button(text=None, fg=None, bg=None):
            try:
                if text is not None and canvas.winfo_exists():
                    canvas.itemconfig(button_text, text=text)
                if fg is not None and canvas.winfo_exists():
                    canvas.itemconfig(button_text, fill=fg)
                if bg is not None and canvas.winfo_exists():
                    # ถ้าไม่ได้อยู่ในสถานะ hover ให้อัพเดตเฉพาะรูปทรง
                    if not canvas._is_hovering:
                        canvas.itemconfig(button_bg, fill=bg)
                    # อัพเดตสีเดิมเสมอ
                    canvas.original_bg = bg
            except Exception as e:
                logging.error(f"Error in button update: {e}")

        # เพิ่มเมธอดให้กับปุ่ม
        canvas.update_button = update_button

        return canvas

    def create_circle_button(
        self,
        parent,
        text,
        command,
        radius=18,
        fg=None,
        bg=None,
        hover_bg=None,
        font=None,
        image=None,
    ):
        """
        สร้างปุ่มทรงกลม

        Args:
            parent: parent widget
            text: ข้อความบนปุ่ม (ใช้เมื่อไม่มี image)
            command: ฟังก์ชันที่จะเรียกเมื่อกดปุ่ม
            radius: รัศมีของปุ่ม
            fg: สีข้อความ
            bg: สีพื้นหลัง
            hover_bg: สีเมื่อ hover
            font: ฟอนต์
            image: รูปภาพบนปุ่ม (optional)

        Returns:
            tk.Canvas: ปุ่มที่สร้างขึ้น
        """
        # กำหนดค่าสีเริ่มต้นจากธีม
        if fg is None:
            fg = self.get_theme_color("text_color")
        if bg is None:
            bg = self.get_theme_color("button_bg")
        if hover_bg is None:
            hover_bg = self.get_accent_color()
        if font is None:
            font = ("Nasalization Rg", 10)

        # กำหนดขนาดของ canvas (เส้นผ่านศูนย์กลาง)
        diameter = radius * 2

        # สร้าง canvas
        canvas = tk.Canvas(
            parent,
            width=diameter,
            height=diameter,
            bg=self.bg_color,
            highlightthickness=0,
            bd=0,
        )

        # วาดวงกลม
        circle = canvas.create_oval(0, 0, diameter, diameter, fill=bg, outline="")

        # เพิ่มข้อความหรือรูปภาพ
        if image:
            if isinstance(image, str):  # ถ้าเป็น path ของไฟล์
                try:
                    img = Image.open(image).resize(
                        (int(radius * 1.5), int(radius * 1.5))
                    )
                    photo = ImageTk.PhotoImage(img)
                    # เก็บ reference ของรูปภาพ
                    canvas.image = photo
                    canvas.img_obj = canvas.create_image(radius, radius, image=photo)
                except Exception as e:
                    logging.error(f"Error loading image: {e}")
                    # ใช้ข้อความแทนถ้าโหลดรูปภาพไม่สำเร็จ
                    canvas.text_obj = canvas.create_text(
                        radius, radius, text=text, fill=fg, font=font
                    )
            else:  # ถ้าเป็น ImageTk.PhotoImage หรือ Object อื่นๆ
                try:
                    canvas.image = image
                    canvas.img_obj = canvas.create_image(radius, radius, image=image)
                except Exception as e:
                    logging.error(f"Error using provided image: {e}")
                    canvas.text_obj = canvas.create_text(
                        radius, radius, text=text, fill=fg, font=font
                    )
        else:
            # สร้างข้อความถ้าไม่มีรูปภาพ
            canvas.text_obj = canvas.create_text(
                radius, radius, text=text, fill=fg, font=font
            )

        # ผูกคำสั่งเมื่อคลิก
        canvas.bind("<Button-1>", lambda event: command())

        # สร้าง hover effect
        def on_enter(event):
            canvas.itemconfig(circle, fill=hover_bg)
            if hasattr(canvas, "text_obj"):
                canvas.itemconfig(canvas.text_obj, fill="white")

        def on_leave(event):
            canvas.itemconfig(circle, fill=bg)
            if hasattr(canvas, "text_obj"):
                canvas.itemconfig(canvas.text_obj, fill=fg)

        canvas.bind("<Enter>", on_enter)
        canvas.bind("<Leave>", on_leave)

        # เพิ่ม metadata
        canvas.circle = circle
        canvas.original_bg = bg
        canvas.hover_bg = hover_bg

        return canvas

    def create_toggle_switch(
        self, parent, text, variable, width=40, height=20, callback=None
    ):
        """
        สร้าง Toggle Switch สำหรับเปิด/ปิดการทำงาน

        Args:
            parent: parent widget
            text: ข้อความอธิบาย
            variable: BooleanVar สำหรับเก็บสถานะ
            width: ความกว้างของสวิตช์
            height: ความสูงของสวิตช์
            callback: ฟังก์ชันที่จะเรียกเมื่อสวิตช์เปลี่ยนสถานะ

        Returns:
            tuple: (container, switch_bg, indicator)
        """
        # สร้าง Frame หลักสำหรับ container
        container = tk.Frame(parent, bg=self.bg_color)
        container.pack(fill=tk.X, pady=2)

        # สร้าง label ที่คลิกได้
        label = tk.Label(
            container,
            text=text,
            bg=self.bg_color,
            fg=self.fg_color,
            font=("IBM Plex Sans Thai Medium", 10),
            cursor="hand2",
        )
        label.pack(side=tk.LEFT, fill=tk.X, expand=True, anchor="w")

        # สร้าง Frame สำหรับ switch ที่มีขนาดที่แน่นอน
        switch_frame = tk.Frame(
            container,
            bg=self.bg_color,
            width=width,
            height=height,
        )
        switch_frame.pack(side=tk.RIGHT, padx=5)
        switch_frame.pack_propagate(False)

        # สร้าง bg switch
        bg_color = "#4CAF50" if variable.get() else "#555555"
        switch_bg = tk.Label(
            switch_frame,
            bg=bg_color,
            relief=tk.RIDGE,  # ใช้ relief=RIDGE เพื่อให้ขอบมนขึ้น
            borderwidth=1,
        )
        switch_bg.place(
            relx=0.5,
            rely=0.5,
            anchor="center",
            width=width - 4,
            height=height - 8,
        )

        # สร้าง indicator (ตัวเลื่อน)
        indicator_size = 14
        x_on = width - indicator_size - 5
        x_off = 5

        indicator = tk.Label(
            switch_frame,
            bg="white",
            bd=1,
            relief=tk.RAISED,  # ใช้ relief=RAISED เพื่อให้มีเงา
        )
        indicator.place(
            x=x_on if variable.get() else x_off,
            y=(height - indicator_size) // 2,
            width=indicator_size,
            height=indicator_size,
        )

        # ฟังก์ชันสำหรับ toggle สถานะ
        def toggle_switch():
            current_value = variable.get()
            variable.set(not current_value)

            # อัพเดต UI
            if variable.get():  # เปิด
                indicator.place(x=x_on)
                switch_bg.config(bg="#4CAF50")  # สีเขียว
            else:  # ปิด
                indicator.place(x=x_off)
                switch_bg.config(bg="#555555")  # สีเทา

            # เรียกใช้ callback ถ้ามี
            if callback:
                callback(variable.get())

        # เพิ่ม bindings
        for widget in [switch_bg, indicator, label]:
            widget.bind("<Button-1>", lambda e: toggle_switch())

        return container, switch_bg, indicator

    def create_styled_slider(
        self,
        parent,
        from_=0,
        to=100,
        orient=tk.HORIZONTAL,
        length=200,
        value=None,
        command=None,
        show_value=True,
    ):
        """
        สร้าง Slider ที่มีสไตล์ตามธีม

        Args:
            parent: parent widget
            from_: ค่าต่ำสุด
            to: ค่าสูงสุด
            orient: แนวของ slider (tk.HORIZONTAL หรือ tk.VERTICAL)
            length: ความยาวของ slider
            value: ค่าเริ่มต้น
            command: ฟังก์ชันที่จะเรียกเมื่อค่าเปลี่ยน
            show_value: แสดงค่าหรือไม่

        Returns:
            tuple: (frame, scale, value_label) หรือ (frame, scale) ถ้าไม่แสดงค่า
        """
        # สร้าง frame สำหรับ slider
        frame = tk.Frame(parent, bg=self.bg_color)

        # สร้าง ttk.Scale
        scale = ttk.Scale(
            frame, from_=from_, to=to, orient=orient, length=length, command=command
        )

        if orient == tk.HORIZONTAL:
            scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        else:
            scale.pack(side=tk.TOP, fill=tk.Y, expand=True)

        # ตั้งค่าเริ่มต้น
        if value is not None:
            scale.set(value)

        # สร้าง label สำหรับแสดงค่า
        if show_value:
            value_label = tk.Label(
                frame,
                text=str(int(scale.get())),
                bg=self.bg_color,
                fg=self.fg_color,
                width=3,
                font=("IBM Plex Sans Thai Medium", 10),
            )
            value_label.pack(side=tk.RIGHT, padx=5)

            # อัพเดตค่าเมื่อ slider เปลี่ยน
            def update_value(*args):
                value_label.config(text=str(int(scale.get())))
                if command:
                    command(scale.get())

            scale.config(command=update_value)

            return frame, scale, value_label
        else:
            return frame, scale

    def create_styled_combobox(
        self, parent, values, textvariable=None, width=20, state="readonly"
    ):
        """
        สร้าง Combobox ที่มีสไตล์ตามธีม

        Args:
            parent: parent widget
            values: รายการค่าที่เลือกได้
            textvariable: StringVar สำหรับเก็บค่าที่เลือก
            width: ความกว้าง
            state: สถานะ ("readonly", "normal")

        Returns:
            ttk.Combobox: combobox ที่สร้างขึ้น
        """
        # สร้าง StringVar ถ้าไม่มี
        if textvariable is None:
            textvariable = tk.StringVar()

        # สร้าง combobox
        combo = ttk.Combobox(
            parent, values=values, textvariable=textvariable, width=width, state=state
        )

        # เลือกค่าแรกถ้าไม่มีค่าที่เลือกแล้ว
        if not textvariable.get() and values:
            textvariable.set(values[0])

        return combo

    def create_color_picker(self, parent, color, callback=None, label_text=None):
        """
        สร้างปุ่มเลือกสี

        Args:
            parent: parent widget
            color: สีเริ่มต้น
            callback: ฟังก์ชันที่จะเรียกเมื่อเลือกสี
            label_text: ข้อความอธิบาย (optional)

        Returns:
            tuple: (frame, button) หรือ (frame, button, label)
        """
        # สร้าง frame
        frame = tk.Frame(parent, bg=self.bg_color)

        # สร้าง label ถ้าต้องการ
        if label_text:
            label = tk.Label(
                frame,
                text=label_text,
                bg=self.bg_color,
                fg=self.fg_color,
                font=("IBM Plex Sans Thai Medium", 10),
            )
            label.pack(side=tk.LEFT, padx=(0, 5))

        # สร้างปุ่มเลือกสี
        button = tk.Button(frame, bg=color, width=3, height=1, relief=tk.RAISED, bd=2)
        button.pack(side=tk.LEFT)

        # ฟังก์ชันเปิด color chooser
        def choose_color():
            new_color = colorchooser.askcolor(color=color)
            if new_color[1]:  # ถ้าเลือกสี
                button.config(bg=new_color[1])
                if callback:
                    callback(new_color[1])

        button.config(command=choose_color)

        if label_text:
            return frame, button, label
        else:
            return frame, button

    # =============================================================================
    # ส่วนของเอฟเฟกต์ต่างๆ (Effects)
    # =============================================================================

    def create_tooltip(self, widget, text):
        """
        สร้าง tooltip สำหรับ widget

        Args:
            widget: widget ที่ต้องการสร้าง tooltip
            text: ข้อความที่จะแสดง
        """
        tooltip = None

        def enter(event):
            nonlocal tooltip

            # คำนวณตำแหน่ง
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25

            # สร้าง Toplevel window
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.geometry(f"+{x}+{y}")
            tooltip.wm_attributes("-topmost", True)

            # สีจากธีม
            bg_color = self.get_accent_color()
            fg_color = "white"

            # สร้าง frame
            frame = tk.Frame(tooltip, bg=bg_color, bd=1, relief=tk.SOLID)
            frame.pack(fill="both", expand=True)

            # สร้าง label
            label = tk.Label(
                frame,
                text=text,
                bg=bg_color,
                fg=fg_color,
                padx=5,
                pady=3,
                wraplength=300,
                justify="left",
                font=("IBM Plex Sans Thai Medium", 9),
            )
            label.pack()

            # เพิ่มเอฟเฟกต์ fade in
            tooltip.attributes("-alpha", 0.0)
            for i in range(11):
                tooltip.attributes("-alpha", i / 10)
                tooltip.update()
                tooltip.after(20)

        def leave(event):
            nonlocal tooltip
            if tooltip:
                # เพิ่มเอฟเฟกต์ fade out
                for i in range(10, -1, -1):
                    try:
                        if tooltip:
                            tooltip.attributes("-alpha", i / 10)
                            tooltip.update()
                            tooltip.after(20)
                    except Exception:
                        pass
                # ทำลาย tooltip
                try:
                    if tooltip:
                        tooltip.destroy()
                        tooltip = None
                except Exception:
                    pass

        # ผูก events
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def create_breathing_effect(
        self,
        widget,
        color_property="bg",
        interval=30,
        min_alpha=0.3,
        max_alpha=1.0,
        stop_event=None,
    ):
        """
        สร้าง breathing effect สำหรับ widget

        Args:
            widget: widget ที่ต้องการใส่เอฟเฟกต์
            color_property: property ของสีที่จะเปลี่ยน ("bg", "fg", ...)
            interval: ความเร็วในการเปลี่ยนสี (ms)
            min_alpha: ค่าความโปร่งใสต่ำสุด
            max_alpha: ค่าความโปร่งใสสูงสุด
            stop_event: threading.Event สำหรับหยุดเอฟเฟกต์

        Returns:
            dict: ข้อมูลของเอฟเฟกต์ที่กำลังทำงาน
        """
        # เก็บข้อมูลของเอฟเฟกต์
        effect_data = {
            "widget": widget,
            "color_property": color_property,
            "interval": interval,
            "min_alpha": min_alpha,
            "max_alpha": max_alpha,
            "current_alpha": min_alpha,
            "direction": 1,  # 1 = เพิ่มค่า, -1 = ลดค่า
            "active": True,
            "after_id": None,
            "stop_event": stop_event,
        }

        # ดึงสีเดิม
        if color_property == "bg":
            original_color = widget.cget("bg")
        elif color_property == "fg":
            original_color = widget.cget("fg")
        else:
            original_color = widget.cget(color_property)

        effect_data["original_color"] = original_color

        # แปลงสีเป็น RGB
        try:
            # สำหรับสีที่เป็น hex code
            if original_color.startswith("#"):
                r = int(original_color[1:3], 16)
                g = int(original_color[3:5], 16)
                b = int(original_color[5:7], 16)
            # สำหรับสีที่เป็นชื่อ
            else:
                rgb = widget.winfo_rgb(original_color)
                r = rgb[0] // 256
                g = rgb[1] // 256
                b = rgb[2] // 256

            effect_data["rgb"] = (r, g, b)
        except Exception as e:
            logging.error(f"Error parsing color: {e}")
            return None

        # ฟังก์ชันสร้าง breathing effect
        def breathe():
            if not effect_data["active"]:
                return

            # ตรวจสอบ stop_event
            if effect_data["stop_event"] and effect_data["stop_event"].is_set():
                effect_data["active"] = False
                return

            # ตรวจสอบว่า widget ยังมีอยู่หรือไม่
            try:
                if not widget.winfo_exists():
                    effect_data["active"] = False
                    return
            except Exception:
                effect_data["active"] = False
                return

            # คำนวณค่า alpha ใหม่
            effect_data["current_alpha"] += 0.05 * effect_data["direction"]

            # เช็คขอบเขตและเปลี่ยนทิศทาง
            if effect_data["current_alpha"] >= effect_data["max_alpha"]:
                effect_data["current_alpha"] = effect_data["max_alpha"]
                effect_data["direction"] = -1
            elif effect_data["current_alpha"] <= effect_data["min_alpha"]:
                effect_data["current_alpha"] = effect_data["min_alpha"]
                effect_data["direction"] = 1

            # คำนวณสีใหม่
            r, g, b = effect_data["rgb"]
            alpha = effect_data["current_alpha"]

            # คำนวณสีที่ผสมกับพื้นหลัง (สีดำ)
            new_r = int(r * alpha)
            new_g = int(g * alpha)
            new_b = int(b * alpha)

            new_color = f"#{new_r:02x}{new_g:02x}{new_b:02x}"

            # อัพเดตสี
            if color_property == "bg":
                widget.config(bg=new_color)
            elif color_property == "fg":
                widget.config(fg=new_color)
            else:
                widget.config(**{color_property: new_color})

            # กำหนดให้เรียกตัวเองอีกครั้ง
            effect_data["after_id"] = widget.after(interval, breathe)

        # เริ่ม effect
        breathe()

        # เก็บ reference
        self.active_effects.append(effect_data)

        return effect_data

    def stop_breathing_effect(self, effect_data):
        """
        หยุด breathing effect

        Args:
            effect_data: ข้อมูลของเอฟเฟกต์ที่ต้องการหยุด
        """
        if effect_data in self.active_effects:
            effect_data["active"] = False

            # ยกเลิก after
            if effect_data["after_id"]:
                try:
                    effect_data["widget"].after_cancel(effect_data["after_id"])
                except Exception:
                    pass

            # คืนค่าสีเดิม
            try:
                color_property = effect_data["color_property"]
                if color_property == "bg":
                    effect_data["widget"].config(bg=effect_data["original_color"])
                elif color_property == "fg":
                    effect_data["widget"].config(fg=effect_data["original_color"])
                else:
                    effect_data["widget"].config(
                        **{color_property: effect_data["original_color"]}
                    )
            except Exception:
                pass

            # ลบออกจากรายการ
            self.active_effects.remove(effect_data)

    def stop_all_effects(self):
        """หยุดเอฟเฟกต์ทั้งหมด"""
        for effect in list(self.active_effects):
            self.stop_breathing_effect(effect)

    def enlarge_button_hitbox(self, button, padding=5):
        """
        เพิ่มพื้นที่การตรวจจับเมาส์สำหรับปุ่มให้ใหญ่กว่าขนาดที่มองเห็น

        Args:
            button: ปุ่มที่ต้องการเพิ่มพื้นที่การตรวจจับ
            padding: จำนวนพิกเซลที่จะเพิ่มรอบๆ ปุ่ม (default: 5px)
        """
        if not button.winfo_exists():
            return

        # สร้าง transparent frame ที่ใหญ่กว่าปุ่ม
        if not hasattr(button, "_hitbox_frame"):
            hitbox = tk.Frame(button.master, bg="")
            hitbox.place(
                in_=button,
                x=-padding,
                y=-padding,
                width=button.winfo_width() + 2 * padding,
                height=button.winfo_height() + 2 * padding,
            )
            button._hitbox_frame = hitbox

            # ส่งต่อ events จาก hitbox ไปยังปุ่ม
            def forward_event(event, event_name):
                # สร้าง event ใหม่และส่งไปยังปุ่ม
                new_event = type("Event", (), {})()
                new_event.x = event.x - padding  # ปรับตำแหน่ง x
                new_event.y = event.y - padding  # ปรับตำแหน่ง y
                new_event.x_root = event.x_root
                new_event.y_root = event.y_root
                button.event_generate(event_name)
                return "break"  # หยุดการแพร่กระจาย event

            # ผูก events
            hitbox.bind("<Enter>", lambda e: forward_event(e, "<Enter>"), add="+")
            hitbox.bind("<Leave>", lambda e: forward_event(e, "<Leave>"), add="+")
            hitbox.bind("<Motion>", lambda e: forward_event(e, "<Motion>"), add="+")
            hitbox.bind("<Button-1>", lambda e: forward_event(e, "<Button-1>"), add="+")

            # ตรวจสอบการลบปุ่ม
            def on_button_destroy(event):
                if (
                    hasattr(button, "_hitbox_frame")
                    and button._hitbox_frame.winfo_exists()
                ):
                    button._hitbox_frame.destroy()

            button.bind("<Destroy>", on_button_destroy, add="+")

    # =============================================================================
    # ส่วนจัดการหน้าต่าง (Window Management)
    # =============================================================================

    def make_draggable(self, window, handle=None):
        """
        ทำให้หน้าต่างลากด้วยเมาส์ได้

        Args:
            window: หน้าต่างที่ต้องการให้ลากได้
            handle: widget ที่ใช้ในการลาก (ถ้าไม่ระบุจะใช้ทั้งหน้าต่าง)
        """
        handle = handle or window

        # ตัวแปรสำหรับการลาก
        x, y = 0, 0

        def start_move(event):
            nonlocal x, y
            x = event.x
            y = event.y

        def on_drag(event):
            nonlocal x, y
            deltax = event.x - x
            deltay = event.y - y
            window_x = window.winfo_x() + deltax
            window_y = window.winfo_y() + deltay
            window.geometry(f"+{window_x}+{window_y}")

        def stop_move(event):
            nonlocal x, y
            x = 0
            y = 0

        # ผูก events
        handle.bind("<Button-1>", start_move)
        handle.bind("<ButtonRelease-1>", stop_move)
        handle.bind("<B1-Motion>", on_drag)

    def apply_rounded_corners(self, window, radius=15):
        """
        ทำให้หน้าต่างมีขอบโค้งมน (Windows เท่านั้น)

        Args:
            window: หน้าต่างที่ต้องการทำให้มีขอบโค้งมน
            radius: รัศมีของมุมโค้ง

        Returns:
            bool: True ถ้าสำเร็จ, False ถ้าไม่สำเร็จ
        """
        if not HAS_WIN32_SUPPORT:
            logging.warning("win32gui not available, cannot apply rounded corners")
            return False

        try:
            # รอให้หน้าต่างแสดงผลเสร็จ
            window.update_idletasks()

            # ดึงค่า HWND ของหน้าต่าง
            hwnd = windll.user32.GetParent(window.winfo_id())

            # ลบกรอบและหัวข้อ
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            style &= ~win32con.WS_CAPTION
            style &= ~win32con.WS_THICKFRAME
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

            # สร้างภูมิภาค (region) โค้งมน
            width = window.winfo_width()
            height = window.winfo_height()
            region = win32gui.CreateRoundRectRgn(
                0, 0, width + 1, height + 1, radius, radius
            )

            # กำหนดภูมิภาคให้กับหน้าต่าง
            win32gui.SetWindowRgn(hwnd, region, True)

            return True
        except Exception as e:
            logging.error(f"Error applying rounded corners: {e}")
            return False

    def create_theme_manager_ui(self, parent, settings=None):
        """
        สร้างหน้าต่างจัดการธีม

        Args:
            parent: parent widget
            settings: settings object สำหรับบันทึกการตั้งค่า (optional)

        Returns:
            tk.Frame: frame ของหน้าต่างจัดการธีม
        """
        # สร้าง frame หลัก
        main_frame = tk.Frame(parent, bg=self.bg_color)

        # ส่วนหัวของหน้าต่าง
        header_frame = tk.Frame(main_frame, bg=self.bg_color)
        header_frame.pack(fill=tk.X, pady=(5, 10))

        # หัวข้อ
        tk.Label(
            header_frame,
            text="Theme Manager",
            font=("Nasalization Rg", 14, "bold"),
            bg=self.bg_color,
            fg=self.get_accent_color(),
        ).pack(pady=5)

        # ส่วนเลือกธีม
        theme_frame = tk.Frame(main_frame, bg=self.bg_color)
        theme_frame.pack(fill=tk.X, padx=10, pady=5)

        # label
        tk.Label(
            theme_frame,
            text="Select Theme:",
            bg=self.bg_color,
            fg=self.fg_color,
            font=("IBM Plex Sans Thai Medium", 10),
        ).pack(side=tk.LEFT)

        # สร้าง combobox สำหรับเลือกธีม
        all_themes = self.get_all_themes()
        theme_names = [theme["name"] for name, theme in all_themes.items()]
        theme_ids = list(all_themes.keys())

        theme_var = tk.StringVar()
        theme_combo = ttk.Combobox(
            theme_frame,
            values=theme_names,
            textvariable=theme_var,
            state="readonly",
            width=15,
        )
        theme_combo.pack(side=tk.LEFT, padx=5)

        # ตั้งค่าธีมปัจจุบัน
        current_theme_index = (
            theme_ids.index(self.current_theme)
            if self.current_theme in theme_ids
            else 0
        )
        theme_combo.current(current_theme_index)

        # ฟังก์ชันเมื่อเลือกธีม
        def on_theme_selected(event):
            selected_index = theme_combo.current()
            if 0 <= selected_index < len(theme_ids):
                selected_theme = theme_ids[selected_index]
                self.set_theme(selected_theme)

                # อัพเดตสี
                update_color_buttons()

                # บันทึกลง settings
                if settings:
                    settings.set("theme", selected_theme)
                    settings.save_settings()

        theme_combo.bind("<<ComboboxSelected>>", on_theme_selected)

        # ส่วนปรับแต่งสี
        color_frame = tk.Frame(main_frame, bg=self.bg_color)
        color_frame.pack(fill=tk.X, padx=10, pady=10)

        # สร้างส่วนย่อยสำหรับแต่ละสี
        color_sections = [
            ("Background", "bg_color"),
            ("Accent", "accent_color"),
            ("Highlight", "highlight_color"),
            ("Button", "button_bg"),
        ]

        color_buttons = {}

        # อัพเดตสีบนปุ่ม
        def update_color_buttons():
            for label, color_name in color_sections:
                color_value = self.get_theme_color(color_name)
                if color_name in color_buttons:
                    color_buttons[color_name].config(bg=color_value)

        # สร้างแต่ละส่วน
        for i, (label, color_name) in enumerate(color_sections):
            # สร้าง frame สำหรับแต่ละสี
            section_frame = tk.Frame(color_frame, bg=self.bg_color)
            section_frame.pack(fill=tk.X, pady=2)

            # label
            tk.Label(
                section_frame,
                text=f"{label} Color:",
                bg=self.bg_color,
                fg=self.fg_color,
                font=("IBM Plex Sans Thai Medium", 10),
                width=12,
                anchor="w",
            ).pack(side=tk.LEFT)

            # ปุ่มเลือกสี
            color_value = self.get_theme_color(color_name)
            color_button = tk.Button(
                section_frame, bg=color_value, width=6, height=1, relief=tk.RAISED, bd=2
            )
            color_button.pack(side=tk.LEFT, padx=5)
            color_buttons[color_name] = color_button

            # ฟังก์ชันเลือกสี
            def choose_color(color_name=color_name):
                current_color = self.get_theme_color(color_name)
                new_color = colorchooser.askcolor(color=current_color)
                if new_color[1]:  # ถ้าเลือกสี
                    # อัพเดตสีในธีม
                    updated_theme = self.update_theme_color(color_name, new_color[1])

                    # อัพเดตปุ่ม
                    color_buttons[color_name].config(bg=new_color[1])

                    # อัพเดตชื่อธีมใน combobox ถ้าสร้างธีมใหม่
                    if updated_theme != self.current_theme:
                        # อัพเดตรายการธีม
                        all_themes = self.get_all_themes()
                        theme_names = [
                            theme["name"] for name, theme in all_themes.items()
                        ]
                        theme_ids = list(all_themes.keys())

                        theme_combo.config(values=theme_names)

                        # เลือกธีมที่เพิ่งสร้าง
                        new_index = (
                            theme_ids.index(updated_theme)
                            if updated_theme in theme_ids
                            else 0
                        )
                        theme_combo.current(new_index)

            color_button.config(command=choose_color)

        # ส่วนปุ่มด้านล่าง
        button_frame = tk.Frame(main_frame, bg=self.bg_color)
        button_frame.pack(pady=10)

        # ปุ่ม Reset
        reset_button = tk.Button(
            button_frame,
            text="Reset to Default",
            command=lambda: self.set_theme("default"),
            bg="#404040",
            fg="white",
            font=("Nasalization Rg", 10),
            padx=10,
        )
        reset_button.pack(side=tk.LEFT, padx=5)

        # ปุ่ม Save
        save_button = tk.Button(
            button_frame,
            text="Save Theme",
            command=lambda: self.save_custom_themes(),
            bg=self.get_accent_color(),
            fg="white",
            font=("Nasalization Rg", 10, "bold"),
            padx=10,
        )
        save_button.pack(side=tk.LEFT, padx=5)

        # เพิ่ม hover effect
        for button in [reset_button, save_button]:
            original_bg = button.cget("bg")
            button.bind(
                "<Enter>",
                lambda e, b=button, c=original_bg: b.config(bg=self.lighten_color(c)),
            )
            button.bind("<Leave>", lambda e, b=button, c=original_bg: b.config(bg=c))

        # ทำให้หน้าต่างลากได้
        self.make_draggable(parent, header_frame)

        return main_frame

    # =============================================================================
    # Helper Methods
    # =============================================================================

    def load_image(self, path, size=None, cache=True):
        """
        โหลดรูปภาพและปรับขนาด

        Args:
            path: path ของรูปภาพ
            size: tuple ของขนาด (width, height)
            cache: เก็บรูปภาพในแคชหรือไม่

        Returns:
            ImageTk.PhotoImage: รูปภาพที่โหลด
        """
        # สร้าง cache key
        cache_key = f"{path}_{size}"

        # ตรวจสอบในแคช
        if cache and cache_key in self.image_cache:
            return self.image_cache[cache_key]

        try:
            img = Image.open(path)

            # ปรับขนาด
            if size:
                img = img.resize(size, Image.Resampling.LANCZOS)

            # แปลงเป็น PhotoImage
            photo = ImageTk.PhotoImage(img)

            # เก็บในแคช
            if cache:
                self.image_cache[cache_key] = photo

            return photo

        except Exception as e:
            logging.error(f"Error loading image {path}: {e}")
            return None

    def create_styled_button(self, parent, text, command, **kwargs):
        """
        สร้างปุ่มที่มีสไตล์ตามธีม

        Args:
            parent: parent widget
            text: ข้อความบนปุ่ม
            command: ฟังก์ชันที่จะเรียกเมื่อกดปุ่ม
            **kwargs: พารามิเตอร์ที่ส่งไปให้ Button

        Returns:
            tk.Button: ปุ่มที่สร้างขึ้น
        """
        # กำหนดค่าเริ่มต้น
        button_config = {
            "text": text,
            "command": command,
            "bg": self.get_accent_color(),
            "fg": "white",
            "font": ("Nasalization Rg", 10),
            "padx": 10,
            "pady": 5,
            "bd": 0,
            "relief": tk.RAISED,
        }

        # อัพเดตด้วย kwargs
        button_config.update(kwargs)

        # สร้างปุ่ม
        button = tk.Button(parent, **button_config)

        # เพิ่ม hover effect
        original_bg = button_config["bg"]
        hover_bg = self.lighten_color(original_bg)

        button.bind("<Enter>", lambda e: button.config(bg=hover_bg))
        button.bind("<Leave>", lambda e: button.config(bg=original_bg))

        return button

    def create_styled_label(self, parent, text, **kwargs):
        """
        สร้าง label ที่มีสไตล์ตามธีม

        Args:
            parent: parent widget
            text: ข้อความบน label
            **kwargs: พารามิเตอร์ที่ส่งไปให้ Label

        Returns:
            tk.Label: label ที่สร้างขึ้น
        """
        # กำหนดค่าเริ่มต้น
        label_config = {
            "text": text,
            "bg": self.bg_color,
            "fg": self.fg_color,
            "font": ("IBM Plex Sans Thai Medium", 10),
            "padx": 5,
            "pady": 2,
        }

        # อัพเดตด้วย kwargs
        label_config.update(kwargs)

        # สร้าง label
        label = tk.Label(parent, **label_config)

        return label

    def validate_color(self, color):
        """
        ตรวจสอบว่าเป็นรหัสสีที่ถูกต้องหรือไม่

        Args:
            color: รหัสสีที่ต้องการตรวจสอบ

        Returns:
            bool: True ถ้าเป็นรหัสสีที่ถูกต้อง, False ถ้าไม่ถูกต้อง
        """
        try:
            # ถ้าเป็น hex code
            if isinstance(color, str) and color.startswith("#"):
                # ตรวจสอบความยาว
                if len(color) != 7:
                    return False

                # ตรวจสอบว่าเป็น hex หรือไม่
                int(color[1:], 16)
                return True

            # ถ้าเป็นชื่อสี
            if isinstance(color, str):
                # สร้าง dummy canvas เพื่อทดสอบสี
                canvas = tk.Canvas(tk.Toplevel())
                canvas.config(bg=color)
                canvas.master.destroy()
                return True

            return False
        except Exception:
            return False

    def cleanup(self):
        """
        ทำความสะอาดทรัพยากรที่ใช้ทั้งหมด
        """
        # หยุดเอฟเฟกต์ทั้งหมด
        self.stop_all_effects()

        # ล้าง cache
        self.image_cache.clear()

        logging.info("UIManager cleanup complete")
