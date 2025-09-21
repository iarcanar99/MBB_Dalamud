import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
import logging
from tkinter import messagebox

logging.basicConfig(level=logging.INFO)


def create_rounded_rectangle(self, x1, y1, x2, y2, radius=25, **kwargs):
    """วาดสี่เหลี่ยมมุมโค้งบน Canvas

    Args:
        x1, y1: พิกัดมุมบนซ้าย
        x2, y2: พิกัดมุมล่างขวา
        radius: รัศมีมุมโค้ง (pixel)
        **kwargs: พารามิเตอร์อื่นๆ สำหรับ create_polygon

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


# เพิ่มเมธอดให้กับคลาส Canvas
tk.Canvas.create_rounded_rectangle = create_rounded_rectangle


class AppearanceManager:
    def __init__(self):
        self.bg_color = "#2c2c2c"
        self.fg_color = "white"
        self.highlight_color = "yellow"
        self.opacity = 0.9
        self.font_name = "Nasalization Rg"
        self.font_size = 12
        self.letter_spacing = 3
        self.button_border_width = 1
        self.button_style = {
            "bg": self.bg_color,
            "fg": self.fg_color,
            "relief": tk.FLAT,
            "bd": self.button_border_width,
            "highlightthickness": self.button_border_width,
            "highlightbackground": self.fg_color,
            "activebackground": self.bg_color,
            "activeforeground": self.fg_color,
        }
        self.custom_font = None

        # Theme registry - จะถูกโหลดจาก custom themes เท่านั้น
        # ไม่มี hard-coded themes อีกต่อไป
        self.themes = {}

        # ค่าธีมเริ่มต้น - จะใช้ Theme1 หรือธีมแรกที่มี
        self.current_theme = None  # จะถูกกำหนดใน get_default_theme()

        # เพิ่มตัวแปรสำหรับเก็บ callback
        self.theme_change_callback = None

    # ปรับปรุงเมธอด get_theme_colors ที่มีอยู่แล้ว
    def get_default_theme(self):
        """ดึงธีมเริ่มต้นแบบ dynamic
        
        Returns:
            str: Theme ID ที่จะใช้เป็น default
        """
        # 1. ลองใช้ Theme1 ก่อน
        if "Theme1" in self.themes:
            return "Theme1"
        
        # 2. ใช้ธีมแรกที่มี
        if self.themes:
            return list(self.themes.keys())[0]
        
        # 3. สร้าง default theme ใหม่
        self.create_default_theme()
        return "Theme1"
        
    def create_default_theme(self):
        """สร้างธีมเริ่มต้นกรณีไม่มีธีมใด ๆ"""
        self.themes["Theme1"] = {
            "name": "ธีมเริ่มต้น",
            "accent": "#6c5ce7",
            "accent_light": "#a29bfe",
            "highlight": "#6c5ce7",
            "secondary": "#00c2cb",
            "text": "#ffffff",
            "text_dim": "#b2b2b2",
            "button_bg": "#262637"
        }
        
    def get_theme_colors(self):
        """ดึงค่าสีทั้งหมดของธีมปัจจุบัน"""
        # กำหนด current_theme ถ้ายังเป็น None
        if self.current_theme is None:
            self.current_theme = self.get_default_theme()
            
        theme = self.themes.get(self.current_theme)
        if theme is None:
            # Fallback ไปยัง default theme
            self.current_theme = self.get_default_theme()
            theme = self.themes.get(self.current_theme)
            
        return theme

    def create_color_picker_dialog(
        self, parent, initial_color="#6c5ce7", title="เลือกสีธีม"
    ):
        """แสดงหน้าต่างเลือกสีแบบกำหนดเอง

        Args:
            parent: parent widget
            initial_color: สีเริ่มต้น
            title: หัวข้อหน้าต่าง

        Returns:
            str: สีที่เลือกในรูปแบบ hex code หรือ None ถ้ายกเลิก
        """
        from tkinter import colorchooser

        result = colorchooser.askcolor(initial_color, title=title)
        return result[1] if result[1] else None

    def create_custom_theme(self, primary_color, secondary_color, name="Custom Theme"):
        """สร้างธีมใหม่จากสีที่ผู้ใช้เลือก

        Args:
            primary_color: สีหลัก (hex code)
            secondary_color: สีรอง (hex code)
            name: ชื่อธีมใหม่

        Returns:
            str: รหัสธีมที่สร้างใหม่
        """
        # สร้าง ID ธีมใหม่
        theme_id = f"custom_{len(self.themes) + 1}"

        # คำนวณสีลูกอัตโนมัติ
        accent_light = self.lighten_color(primary_color, 1.3)

        # สร้างธีมใหม่
        self.themes[theme_id] = {
            "name": name,
            "accent": primary_color,  # สีหลัก
            "accent_light": accent_light,  # สีหลักที่อ่อนกว่า (hover)
            "highlight": primary_color,  # ใช้สีหลักเป็นสีไฮไลท์
            "secondary": secondary_color,  # สีรอง
            "text": "#ffffff",  # สีข้อความปกติ
            "text_dim": "#b2b2b2",  # สีข้อความที่อ่อนลง
            "button_bg": "#262637",  # สีพื้นหลังปุ่ม
        }

        # บันทึกธีมใหม่ลงใน settings ถ้ามี
        if hasattr(self, "settings") and self.settings:
            custom_themes = self.settings.get("custom_themes", {})
            custom_themes[theme_id] = self.themes[theme_id]
            self.settings.set("custom_themes", custom_themes)

        return theme_id

    def create_theme_manager_ui(self, parent, settings=None):
        """สร้างหน้า UI จัดการธีม

        Args:
            parent: parent widget
            settings: Settings object (optional)

        Returns:
            tk.Frame: frame หลักของหน้าจัดการธีม
        """
        self.settings = settings  # เก็บ settings เพื่อบันทึกธีมที่สร้างขึ้น

        main_frame = tk.Frame(parent, bg=self.bg_color)

        # สร้างส่วนเลือกธีมที่มีอยู่
        theme_frame = tk.Frame(main_frame, bg=self.bg_color)
        theme_frame.pack(fill=tk.X, pady=10)

        theme_label = self.create_styled_label(theme_frame, "เลือกธีม:")
        theme_label.pack(side=tk.LEFT, padx=(0, 10))

        # แสดงเฉพาะธีมที่ผู้ใช้สร้างเท่านั้น (ไม่รวมธีมเริ่มต้น)
        theme_ids = []  # เก็บ ID
        theme_names = []  # เก็บชื่อที่แสดง

        # สร้างการ mapping ระหว่างชื่อธีมและ ID
        self.theme_name_to_id = {}  # สร้าง dict ใหม่เพื่อเก็บ mapping

        # กรองเฉพาะธีมของผู้ใช้เท่านั้น (ขึ้นต้นด้วย "Theme")
        if settings and "custom_themes" in settings.settings:
            custom_themes = settings.settings["custom_themes"]
            for theme_id, theme_data in custom_themes.items():
                # เพิ่มเฉพาะธีมที่เป็นของผู้ใช้ (Theme1, Theme2, ...)
                if theme_id.startswith("Theme"):
                    theme_ids.append(theme_id)
                    theme_display_name = theme_data["name"]
                    theme_names.append(theme_display_name)
                    self.theme_name_to_id[theme_display_name] = theme_id

                    # เพิ่มธีมเข้าไปในคลังธีมด้วย (ถ้ายังไม่มี)
                    if theme_id not in self.themes:
                        self.themes[theme_id] = theme_data

        # ถ้าไม่มีธีมของผู้ใช้เลย ให้สร้างธีมเริ่มต้น
        if not theme_names:
            # สร้างธีมเริ่มต้น 1 ธีม
            default_themes = [
                {"name": "ธีมสีแดง", "accent": "#C62828", "secondary": "#FF5252"}
            ]

            for i, theme_data in enumerate(default_themes):
                theme_id = f"Theme{i+1}"
                theme_display_name = theme_data["name"]

                # สร้างธีมใหม่
                accent_light = self.lighten_color(theme_data["accent"], 1.3)
                new_theme = {
                    "name": theme_display_name,
                    "accent": theme_data["accent"],
                    "accent_light": accent_light,
                    "highlight": theme_data["accent"],
                    "secondary": theme_data["secondary"],
                    "text": "#ffffff",
                    "text_dim": "#b2b2b2",
                    "button_bg": "#262637",
                }

                # เพิ่มธีมใหม่ลงในคลังธีม
                self.themes[theme_id] = new_theme

                # เพิ่มลงใน list แสดงผล
                theme_ids.append(theme_id)
                theme_names.append(theme_display_name)
                self.theme_name_to_id[theme_display_name] = theme_id

                # บันทึกลง settings ถ้ามี
                if settings:
                    custom_themes = settings.get("custom_themes", {})
                    custom_themes[theme_id] = new_theme
                    settings.set("custom_themes", custom_themes)

            # บันทึกการเปลี่ยนแปลง
            if settings:
                settings.save_settings()

        # ตั้งค่าตัวแปรเริ่มต้นเป็นชื่อของธีมปัจจุบัน
        if self.current_theme in self.themes:
            current_theme_name = self.themes[self.current_theme]["name"]
        else:
            current_theme_name = theme_names[0] if theme_names else "ธีมสีม่วง"

        theme_var = tk.StringVar(value=current_theme_name)

        # สร้าง combobox ที่แสดงชื่อธีม
        theme_combo = ttk.Combobox(
            theme_frame, textvariable=theme_var, values=theme_names, width=15
        )
        theme_combo.pack(side=tk.LEFT)

        # โค้ดอัพเดตธีมเมื่อเลือก combobox
        def update_theme_display(*args):
            selected_name = theme_var.get()

            # หา ID จากชื่อธีมที่เลือก
            if selected_name in self.theme_name_to_id:
                theme_id = self.theme_name_to_id[selected_name]

                # อัพเดตการแสดงผล
                theme_display.config(text=f"ธีมปัจจุบัน: {selected_name}")

                # อัพเดตแถบสีตัวอย่าง
                primary_preview.config(bg=self.themes[theme_id]["accent"])
                secondary_preview.config(bg=self.themes[theme_id]["secondary"])

                # อัพเดตชื่อธีมในช่องข้อความอัตโนมัติ
                theme_name_var.set(selected_name)

        theme_var.trace("w", update_theme_display)

        # ฟังก์ชันสำหรับบันทึกและใช้ธีมที่เลือกในคราวเดียวกัน
        def apply_theme():
            # รับค่าชื่อใหม่จากช่องข้อความ
            new_name = theme_name_var.get().strip()

            # หากไม่มีชื่อ ใช้ชื่อเริ่มต้นที่ไม่ซ้ำ
            if not new_name:
                new_name = f"ธีมที่ {len(theme_names) + 1}"
                theme_name_var.set(new_name)

            # รับค่าสีที่เลือก
            primary = primary_preview.cget("bg")
            secondary = secondary_preview.cget("bg")

            # หา theme_id จากชื่อที่เลือกใน combobox
            selected_name = theme_var.get()
            theme_id = self.theme_name_to_id.get(selected_name, None)

            if not theme_id:
                # แจ้งเตือน
                status_label.config(
                    text="❌ ไม่พบธีมที่เลือก กรุณาเลือกธีมก่อน",
                    fg="#F44336",  # สีแดง
                )
                main_frame.after(3000, lambda: status_label.config(text=""))
                return

            # ถ้าชื่อถูกเปลี่ยน ต้องอัพเดต mapping
            old_name = self.themes[theme_id]["name"]
            if new_name != old_name:
                # ตรวจสอบว่าชื่อใหม่ซ้ำกับชื่อธีมอื่นหรือไม่
                if (
                    new_name in self.theme_name_to_id
                    and self.theme_name_to_id[new_name] != theme_id
                ):
                    # ถ้าชื่อซ้ำ เพิ่มเลขต่อท้าย
                    count = 1
                    base_name = new_name
                    while (
                        new_name in self.theme_name_to_id
                        and self.theme_name_to_id[new_name] != theme_id
                    ):
                        new_name = f"{base_name} ({count})"
                        count += 1
                    # อัพเดตชื่อในช่องข้อความ
                    theme_name_var.set(new_name)

                # ลบ mapping เก่า
                if old_name in self.theme_name_to_id:
                    del self.theme_name_to_id[old_name]

                # เพิ่ม mapping ใหม่
                self.theme_name_to_id[new_name] = theme_id

                # อัพเดตค่าใน combobox
                theme_names = list(theme_combo["values"])
                index = theme_names.index(old_name) if old_name in theme_names else -1
                if index >= 0:
                    theme_names[index] = new_name
                    theme_combo["values"] = theme_names
                    theme_var.set(new_name)

            # บันทึกและใช้ธีมที่อัพเดตแล้ว
            success = self._update_theme(theme_id, new_name, primary, secondary)

            # แสดงข้อความแจ้งเตือน
            if success:
                status_label.config(
                    text=f"✓ บันทึกและใช้ธีม '{new_name}' เรียบร้อย!",
                    fg="#4CAF50",  # สีเขียว
                )
            else:
                status_label.config(
                    text="❌ เกิดข้อผิดพลาดในการบันทึกธีม",
                    fg="#F44336",  # สีแดง
                )

            # รีเซ็ตข้อความหลัง 3 วินาที
            main_frame.after(3000, lambda: status_label.config(text=""))

        # ปุ่ม APPLY (ใช้งานและบันทึกในคราวเดียว)
        apply_button = tk.Button(
            theme_frame,
            text="APPLY",
            command=apply_theme,
            bg=self.get_accent_color(),  # ใช้สีหลักของธีม
            fg="white",
            activebackground=self.get_theme_color("accent_light"),  # สีเมื่อกด
            activeforeground="white",
            font=("Nasalization Rg", 11, "bold"),
            padx=15,
            pady=5,
            bd=0,
            relief=tk.RAISED,
            cursor="hand2",
        )
        apply_button.pack(side=tk.RIGHT, padx=10)

        # เพิ่ม hover effect
        def on_apply_enter(e):
            apply_button.config(bg=self.get_theme_color("accent_light"))

        def on_apply_leave(e):
            apply_button.config(bg=self.get_accent_color())

        apply_button.bind("<Enter>", on_apply_enter)
        apply_button.bind("<Leave>", on_apply_leave)

        # แสดงชื่อธีมปัจจุบัน
        theme_display = self.create_styled_label(
            main_frame, f"ธีมปัจจุบัน: {current_theme_name}"
        )
        theme_display.pack(anchor="w", pady=5)

        # สร้างส่วนปรับแต่งธีม
        separator = ttk.Separator(main_frame, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, pady=15)

        custom_label = self.create_styled_label(
            main_frame, "ปรับแต่งธีม:", font=("Nasalization Rg", 12, "bold")
        )
        custom_label.pack(anchor="w", pady=5)

        # ส่วนเลือกสีหลัก
        primary_frame = tk.Frame(main_frame, bg=self.bg_color)
        primary_frame.pack(fill=tk.X, pady=5)

        primary_label = self.create_styled_label(primary_frame, "สีหลัก:")
        primary_label.pack(side=tk.LEFT)

        # ปรับปรุงกล่องสีให้คลิกได้โดยตรง
        primary_preview = tk.Frame(
            primary_frame,
            bg=(
                self.themes[self.current_theme]["accent"]
                if self.current_theme in self.themes
                else "#6c5ce7"
            ),
            width=60,  # ปรับให้ใหญ่ขึ้น
            height=30,  # ปรับให้ใหญ่ขึ้น
            cursor="hand2",  # เปลี่ยนเคอร์เซอร์เป็นรูปมือ
            relief=tk.RAISED,  # เพิ่มขอบนูน
            bd=1,  # ขนาดขอบ
        )
        primary_preview.pack(side=tk.RIGHT, padx=15)
        primary_preview.pack_propagate(False)

        # เพิ่ม binding เพื่อให้คลิกที่กล่องสีได้โดยตรง
        primary_preview.bind(
            "<Button-1>", lambda e: self._select_theme_color(primary_preview)
        )

        # ส่วนเลือกสีรอง
        secondary_frame = tk.Frame(main_frame, bg=self.bg_color)
        secondary_frame.pack(fill=tk.X, pady=5)

        secondary_label = self.create_styled_label(secondary_frame, "สีรอง:")
        secondary_label.pack(side=tk.LEFT)

        # ปรับปรุงกล่องสีให้คลิกได้โดยตรง
        secondary_preview = tk.Frame(
            secondary_frame,
            bg=(
                self.themes[self.current_theme]["secondary"]
                if self.current_theme in self.themes
                else "#00c2cb"
            ),
            width=60,  # ปรับให้ใหญ่ขึ้น
            height=30,  # ปรับให้ใหญ่ขึ้น
            cursor="hand2",  # เปลี่ยนเคอร์เซอร์เป็นรูปมือ
            relief=tk.RAISED,  # เพิ่มขอบนูน
            bd=1,  # ขนาดขอบ
        )
        secondary_preview.pack(side=tk.RIGHT, padx=15)
        secondary_preview.pack_propagate(False)

        # เพิ่ม binding เพื่อให้คลิกที่กล่องสีได้โดยตรง
        secondary_preview.bind(
            "<Button-1>", lambda e: self._select_theme_color(secondary_preview)
        )

        # เพิ่มคำแนะนำ (เป็น Label เดียวที่ใช้ร่วมกัน)
        hint_label = tk.Label(
            main_frame,
            text="* คลิกที่กล่องสีเพื่อเปลี่ยนสี",
            bg=self.bg_color,
            fg="#888888",
            font=("IBM Plex Sans Thai Medium", 8),
        )
        hint_label.pack(anchor="e", pady=(0, 5))

        # ส่วนชื่อธีม
        name_frame = tk.Frame(main_frame, bg=self.bg_color)
        name_frame.pack(fill=tk.X, pady=10)

        name_label = self.create_styled_label(name_frame, "ชื่อธีม:")
        name_label.pack(side=tk.LEFT)

        theme_name_var = tk.StringVar(value=current_theme_name)
        name_entry = self.create_styled_entry(name_frame, textvariable=theme_name_var)
        name_entry.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # เพิ่ม focus highlight ที่ช่องชื่อธีม - เลือกข้อความทั้งหมดเมื่อคลิก
        def highlight_text(event):
            name_entry.select_range(0, "end")  # เลือกข้อความทั้งหมด
            name_entry.icursor("end")  # วาง cursor ที่จุดสิ้นสุด

        name_entry.bind("<FocusIn>", highlight_text)

        # ผูก Enter key เพื่อบันทึกธีม
        name_entry.bind("<Return>", lambda event: (apply_theme(), "break"))

        # สร้าง Label สำหรับแสดงข้อความแจ้งเตือน
        status_frame = tk.Frame(main_frame, bg=self.bg_color)
        status_frame.pack(fill=tk.X, pady=5)
        status_label = tk.Label(
            status_frame,
            text="",
            bg=self.bg_color,
            fg="#4CAF50",  # สีเขียว
            font=("IBM Plex Sans Thai Medium", 9),
        )
        status_label.pack(fill=tk.X)

        # อัพเดตการแสดงผลครั้งแรก
        update_theme_display()

        return main_frame

    def _update_theme(self, theme_id, name, primary, secondary):
        """อัพเดตธีมที่มีอยู่ด้วยค่าใหม่

        Args:
            theme_id: รหัสของธีม
            name: ชื่อธีมใหม่
            primary: สีหลัก (hex code)
            secondary: สีรอง (hex code)

        Returns:
            bool: สถานะการอัพเดต (สำเร็จหรือไม่)
        """
        try:
            if not theme_id or theme_id not in self.themes:
                print(f"Theme ID '{theme_id}' not found in themes")
                return False

            # ตรวจสอบว่าเป็นชื่อที่ถูกต้อง
            if not name or not isinstance(name, str) or len(name.strip()) == 0:
                print("Invalid theme name")
                return False

            # ตรวจสอบค่าสี
            if not primary.startswith("#") or not secondary.startswith("#"):
                print("Invalid color format, must be #RRGGBB")
                return False

            # คำนวณสีลูกอัตโนมัติ
            try:
                accent_light = self.lighten_color(primary, 1.3)
            except Exception as e:
                print(f"Error calculating accent_light: {e}")
                accent_light = primary  # ใช้สีเดิมถ้าคำนวณไม่ได้

            # อัพเดตธีมที่มีอยู่แล้ว
            self.themes[theme_id].update(
                {
                    "name": name,
                    "accent": primary,
                    "accent_light": accent_light,
                    "highlight": primary,
                    "secondary": secondary,
                    # คงค่าอื่นๆ ไว้
                    "text": self.themes[theme_id].get("text", "#ffffff"),
                    "text_dim": self.themes[theme_id].get("text_dim", "#b2b2b2"),
                    "button_bg": self.themes[theme_id].get("button_bg", "#262637"),
                }
            )

            # บันทึกลง settings ถ้ามี
            if hasattr(self, "settings") and self.settings:
                try:
                    custom_themes = self.settings.get("custom_themes", {})
                    custom_themes[theme_id] = self.themes[theme_id]
                    self.settings.set("custom_themes", custom_themes)
                    self.settings.save_settings()  # บันทึกการเปลี่ยนแปลงทันที
                except Exception as e:
                    print(f"Error saving theme to settings: {e}")
                    # ไม่ return False เพราะธีมได้อัพเดตในโปรแกรมแล้ว

            # สลับไปใช้ธีมที่อัพเดตแล้วและบันทึกว่าเป็นธีมปัจจุบัน
            print(f"DEBUG: Applying theme {theme_id} with colors primary={primary}, secondary={secondary}")
            self.set_theme(theme_id)

            # Force refresh callback if it exists
            if hasattr(self, "theme_change_callback") and self.theme_change_callback:
                try:
                    print("DEBUG: Forcing theme callback execution...")
                    self.theme_change_callback()
                    print("DEBUG: Theme callback executed successfully")
                except Exception as e:
                    print(f"DEBUG: Error in forced theme callback: {e}")

            return True

        except Exception as e:
            print(f"Error updating theme: {e}")
            return False

    def _select_theme_color(self, preview_widget):
        """แสดงหน้าต่างเลือกสีและอัพเดทสีของ preview widget

        Args:
            preview_widget: widget ที่ใช้แสดงตัวอย่างสี
        """
        current_color = preview_widget.cget("bg")
        new_color = self.create_color_picker_dialog(preview_widget, current_color)
        if new_color:
            preview_widget.config(bg=new_color)

    def set_theme(self, theme_name):
        """ตั้งค่าธีมปัจจุบัน"""
        # ตรวจสอบว่าเป็น ID ที่มีอยู่ในคลังธีม
        if theme_name in self.themes:
            self.current_theme = theme_name

            # บันทึกการเปลี่ยนแปลงลง settings ถ้ามี
            if hasattr(self, "settings") and self.settings:
                self.settings.set("theme", theme_name)
                self.settings.save_settings()
                print(f"บันทึกธีม {theme_name} ลงในไฟล์ settings.json แล้ว")
            else:
                print("ไม่พบ settings object ในการบันทึกธีม")

            # เรียก callback ถ้ามี
            if hasattr(self, "theme_change_callback") and self.theme_change_callback:
                try:
                    print(f"DEBUG: Executing theme_change_callback for theme {theme_name}")
                    self.theme_change_callback()
                    print(f"DEBUG: theme_change_callback completed successfully")
                except Exception as e:
                    print(f"Error in theme_change_callback: {e}")
            else:
                print(f"DEBUG: No theme_change_callback found or callback is None")

            return True
        elif (
            theme_name.startswith("Theme")
            and hasattr(self, "settings")
            and self.settings
        ):
            # กรณีเป็น Theme ID ที่มีในผู้ใช้แต่ไม่มีในคลังธีม
            custom_themes = self.settings.get("custom_themes", {})
            if theme_name in custom_themes:
                # โหลดธีมจาก settings เข้าคลังธีม
                self.themes[theme_name] = custom_themes[theme_name]
                self.current_theme = theme_name

                # บันทึกลง settings
                self.settings.set("theme", theme_name)
                self.settings.save_settings()
                print(f"บันทึกธีมที่นำเข้า {theme_name} ลงในไฟล์ settings.json แล้ว")

                # เรียก callback
                if (
                    hasattr(self, "theme_change_callback")
                    and self.theme_change_callback
                ):
                    try:
                        self.theme_change_callback()
                    except Exception as e:
                        print(f"Error in theme_change_callback: {e}")

                return True

        # กรณีไม่พบธีม ใช้ default theme แบบ dynamic
        print(f"Theme '{theme_name}' not found, using default")
        self.current_theme = self.get_default_theme()
        return False

    def set_theme_change_callback(self, callback):
        """ตั้งค่า callback ที่จะเรียกเมื่อธีมเปลี่ยน

        Args:
            callback: ฟังก์ชันที่จะเรียกเมื่อธีมเปลี่ยน
        """
        self.theme_change_callback = callback

    def load_custom_themes(self, settings):
        """โหลดธีมที่ผู้ใช้สร้างเองจาก settings

        Args:
            settings: Settings object
        """
        if settings:
            try:
                self.settings = settings
                custom_themes = settings.get("custom_themes", {})

                # จัดการกรณีไม่มีธีมผู้ใช้หรือมีน้อยกว่า 5 ธีม
                if not custom_themes or len(custom_themes) < 5:
                    # สร้างธีมเริ่มต้นสำหรับส่วนที่ขาด
                    default_themes = [
                        {
                            "name": "ธีมเริ่มต้น",
                            "accent": "#6c5ce7",
                            "secondary": "#00c2cb",
                        },
                        {"name": "ธีมฟ้า", "accent": "#1E88E5", "secondary": "#03A9F4"},
                        {"name": "ธีมเขียว", "accent": "#2E7D32", "secondary": "#00BFA5"},
                        {"name": "ธีมแดง", "accent": "#C62828", "secondary": "#FF5252"},
                        {"name": "ธีมดำ", "accent": "#333333", "secondary": "#888888"},
                    ]

                    # สร้างเฉพาะธีมที่ขาด
                    existing_numbers = set()
                    for theme_id in custom_themes:
                        if theme_id.startswith("Theme"):
                            try:
                                num = int(theme_id[5:])
                                existing_numbers.add(num)
                            except ValueError:
                                pass

                    # เติมธีมที่ขาด
                    for i in range(1, 6):
                        if i not in existing_numbers and len(custom_themes) < 5:
                            theme_id = f"Theme{i}"
                            theme_data = default_themes[i - 1]

                            # สร้างธีมใหม่
                            accent_light = self.lighten_color(theme_data["accent"], 1.3)
                            new_theme = {
                                "name": theme_data["name"],
                                "accent": theme_data["accent"],
                                "accent_light": accent_light,
                                "highlight": theme_data["accent"],
                                "secondary": theme_data["secondary"],
                                "text": "#ffffff",
                                "text_dim": "#b2b2b2",
                                "button_bg": "#262637",
                            }

                            # เพิ่มธีมใหม่ลงในคลังธีม
                            custom_themes[theme_id] = new_theme

                    # บันทึกการเปลี่ยนแปลง
                    settings.set("custom_themes", custom_themes)
                    settings.save_settings()

                # โหลดธีมผู้ใช้ทั้งหมดเข้าคลังธีม
                for theme_id, theme_data in custom_themes.items():
                    self.themes[theme_id] = theme_data

                # ดูว่าควรใช้ธีมไหนเป็นธีมปัจจุบัน
                current_theme = settings.get("theme", "Theme1")
                if current_theme in self.themes:
                    self.current_theme = current_theme
                elif current_theme in custom_themes:
                    self.current_theme = current_theme
                else:
                    self.current_theme = self.get_default_theme()  # ใช้ Theme1 หรือธีมแรกเป็นค่าเริ่มต้น

            except Exception as e:
                print(f"Error loading custom themes: {e}")
                self.current_theme = self.get_default_theme()  # ใช้ Theme1 หรือธีมแรกเป็นค่าเริ่มต้น

    def apply_theme_to_button(self, button, is_active=False, is_accent=False):
        """ประยุกต์ใช้ธีมกับปุ่มแบบเต็มรูปแบบ

        Args:
            button: ปุ่มที่ต้องการปรับสี
            is_active: True ถ้าปุ่มกำลังถูกเลือก/active
            is_accent: True ถ้าต้องการใช้สีหลักแทนสี button_bg
        """
        theme = self.get_theme_colors()

        # เลือกสีตามประเภทของปุ่ม
        if is_active:  # ปุ่มที่กำลังถูกเลือก
            bg_color = "#404060"  # สีเข้มสำหรับปุ่มที่เลือก
            text_color = theme.get("highlight", "#00FFFF")
            hover_color = theme.get("accent_light", "#a29bfe")
        elif is_accent:  # ปุ่มหลัก (เช่น Start Translation)
            bg_color = theme.get("accent", "#6c5ce7")
            text_color = "#ffffff"
            hover_color = theme.get("accent_light", "#a29bfe")
        else:  # ปุ่มปกติ
            bg_color = theme.get("button_bg", "#262637")
            text_color = "#ffffff"
            hover_color = theme.get("accent", "#6c5ce7")

        # ปรับตามประเภทของ button
        if hasattr(button, "itemconfig") and hasattr(button, "button_bg"):
            # สำหรับปุ่มที่สร้างด้วย Canvas
            button.itemconfig(button.button_bg, fill=bg_color)
            if hasattr(button, "button_text"):
                button.itemconfig(button.button_text, fill=text_color)
            button.original_bg = bg_color
            button.hover_bg = hover_color
            button.selected = is_active
        else:
            # สำหรับปุ่มธรรมดา
            button.configure(bg=bg_color, fg=text_color)
            button.configure(activebackground=hover_color)

    def get_current_theme(self):
        """ดึงชื่อธีมปัจจุบัน"""
        return self.current_theme

    def get_theme_color(self, color_name, default=None):  # เพิ่ม default=None
        """ดึงค่าสีเฉพาะจากธีมปัจจุบัน

        Args:
            color_name: ชื่อของสีที่ต้องการ (accent, highlight, secondary, text, text_dim, button_bg, etc.)
            default: ค่า default ที่จะคืนหากไม่พบสีในธีม (optional)

        Returns:
            str: ค่าสีในรูปแบบ hex code
        """
        # กำหนด current_theme ถ้ายังเป็น None
        if self.current_theme is None:
            self.current_theme = self.get_default_theme()
            
        theme = self.themes.get(self.current_theme)
        if theme is None:
            # Fallback ไปยัง default theme
            self.current_theme = self.get_default_theme()
            theme = self.themes.get(self.current_theme, {})

        # กำหนดค่าเริ่มต้นภายใน หากไม่พบใน theme หรือ default ที่ส่งมา
        default_colors = {
            "accent": "#6c5ce7",
            "accent_light": "#a29bfe",
            "highlight": "#6c5ce7",
            "secondary": "#00c2cb",
            "text": "#ffffff",
            "text_dim": "#b2b2b2",
            "button_bg": "#262637",
            "error": "#e74c3c",  # เพิ่ม error ด้วย
            # เพิ่มสีอื่นๆ ที่อาจจำเป็น
        }

        # 1. ลองดึงจาก theme ปัจจุบัน
        color_value = theme.get(color_name)

        # 2. ถ้าไม่เจอใน theme, ลองใช้ default ที่ส่งมา
        if color_value is None and default is not None:
            color_value = default

        # 3. ถ้ายังไม่มี ให้ใช้ default จาก default_colors
        if color_value is None:
            color_value = default_colors.get(
                color_name, self.fg_color
            )  # ใช้ fg_color เป็น fallback สุดท้าย

        return color_value

    def get_accent_color(self):
        """ดึงสีหลักของธีมปัจจุบัน"""
        return self.get_theme_color("accent")

    def get_highlight_color(self):
        """ดึงสีไฮไลท์ของธีมปัจจุบัน"""
        return self.get_theme_color("highlight")

    def get_available_themes(self):
        """ดึงรายชื่อธีมที่มีทั้งหมด"""
        return [(theme_id, data["name"]) for theme_id, data in self.themes.items()]

    def cycle_theme(self):
        """เปลี่ยนไปยังธีมถัดไป"""
        theme_keys = list(self.themes.keys())
        current_index = theme_keys.index(self.current_theme)
        next_index = (current_index + 1) % len(theme_keys)
        self.current_theme = theme_keys[next_index]
        return self.current_theme, self.themes[self.current_theme]["name"]

    def update_bg_color(self, new_color):
        """Update background color and related styles"""
        self.bg_color = new_color
        self.button_style.update({"bg": new_color, "activebackground": new_color})

    def apply_bg_color(self, widget):
        """Apply current background color to widget"""
        widget.configure(bg=self.bg_color)

    def load_custom_font(self, root):
        try:
            self.custom_font = tkfont.Font(family=self.font_name, size=self.font_size)
            logging.info(f"Font loaded successfully: {self.font_name}")
            return self.custom_font
        except Exception as e:
            logging.warning(f"Failed to load font: {e}. Using system default.")
            self.custom_font = tkfont.Font(family="TkDefaultFont", size=self.font_size)
            return self.custom_font

    def apply_style(self, window):
        window.configure(bg=self.bg_color)
        window.attributes("-alpha", self.opacity)
        self.custom_font = self.load_custom_font(window)
        self.button_style["font"] = self.custom_font

        style = ttk.Style()
        style.configure(
            "Switch.TCheckbutton",
            background=self.bg_color,
            foreground=self.fg_color,
            font=self.custom_font,
        )
        style.map(
            "Switch.TCheckbutton",
            background=[("active", self.bg_color)],
            foreground=[("active", self.fg_color)],
        )

        return self.custom_font

    def create_styled_button(self, parent, text, command=None, hover_bg=None):
        text = text.upper()
        spaced_text = " ".join(text)
        button = tk.Button(
            parent, text=spaced_text, command=command, **self.button_style
        )
        original_bg = self.button_style["bg"]
        hover_bg = hover_bg if hover_bg else original_bg
        button.bind("<Enter>", lambda e: button.config(bg=hover_bg))
        button.bind("<Leave>", lambda e: button.config(bg=original_bg))
        return button

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
        corner_radius=10,
    ):
        """สร้างปุ่มโมเดิร์นด้วย Canvas"""
        # ใช้สีจากธีมปัจจุบันถ้าไม่ได้ระบุ
        if bg is None:
            bg = self.get_theme_color("button_bg")
        if hover_bg is None:
            hover_bg = self.get_accent_color()

        # สร้าง canvas สำหรับวาดปุ่ม
        canvas = tk.Canvas(
            parent,
            width=width,
            height=height,
            bg=self.bg_color,
            highlightthickness=0,
            bd=0,
        )

        # วาดพื้นหลังปุ่มด้วยสี่เหลี่ยมมุมโค้ง
        button_bg = canvas.create_rounded_rectangle(
            0, 0, width, height, radius=corner_radius, fill=bg, outline=""
        )

        # สร้างข้อความบนปุ่ม
        button_text = canvas.create_text(
            width // 2, height // 2, text=text, fill=fg, font=font
        )

        # ผูกคำสั่งเมื่อคลิก
        if command:
            canvas.bind("<Button-1>", lambda event: command())

        # เพิ่ม metadata สำหรับการใช้งานภายหลัง
        canvas.selected = False
        canvas.original_bg = bg
        canvas.hover_bg = hover_bg
        canvas.button_bg = button_bg
        canvas.button_text = button_text
        canvas._is_hovering = False

        # สร้าง hover effect - ใช้ itemconfig ไม่ใช้ config เพื่อปรับแต่งรูปร่าง
        def on_enter(event):
            if hasattr(canvas, "selected") and canvas.selected:
                return
            canvas._is_hovering = True
            canvas.itemconfig(button_bg, fill=hover_bg)

        def on_leave(event):
            canvas._is_hovering = False
            if not hasattr(canvas, "selected") or not canvas.selected:
                canvas.itemconfig(button_bg, fill=canvas.original_bg)

        canvas.bind("<Enter>", on_enter)
        canvas.bind("<Leave>", on_leave)

        # ใช้ method itemconfig แทน config เพื่อปรับแต่งรูปร่าง
        def custom_config(**kwargs):
            try:
                if "text" in kwargs and canvas.winfo_exists():
                    canvas.itemconfig(button_text, text=kwargs["text"])
                if "fg" in kwargs and canvas.winfo_exists():
                    canvas.itemconfig(button_text, fill=kwargs["fg"])
                if "bg" in kwargs and canvas.winfo_exists():
                    # อัพเดตเฉพาะถ้าไม่ได้อยู่ในสถานะ hover
                    if not canvas._is_hovering:
                        canvas.itemconfig(button_bg, fill=kwargs["bg"])

                    # อัพเดตสีเดิมเสมอ เพื่อให้เมื่อออกจาก hover จะใช้สีนี้
                    canvas.original_bg = kwargs["bg"]
            except Exception as e:
                print(f"Error in button custom_config (appearance.py): {e}")

        # เก็บ method custom_config ไว้สำหรับใช้งาน
        canvas.custom_config = custom_config

        return canvas

    def create_styled_entry(self, parent, **kwargs):
        entry = tk.Entry(
            parent,
            bg=self.bg_color,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            font=self.custom_font,
            **kwargs,
        )
        return entry

    def create_styled_label(self, parent, text, **kwargs):
        # ดึง font จาก kwargs ถ้ามี หรือใช้ค่าเริ่มต้น
        font = kwargs.pop("font", self.custom_font)

        label = tk.Label(
            parent,
            text=text,
            bg=self.bg_color,
            fg=self.fg_color,
            font=font,
            **kwargs,
        )
        return label

    def create_styled_text(self, parent, **kwargs):
        text_widget = tk.Text(
            parent,
            bg=self.bg_color,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            font=self.custom_font,
            **kwargs,
        )
        text_widget.tag_configure("highlight", background=self.highlight_color)
        return text_widget

    def create_styled_scale(self, parent, **kwargs):
        """
        สร้าง scale widget พร้อม frame และ value label

        Returns:
            tuple: (frame, scale) โดย
                  frame คือ container ที่มี scale และ label
                  scale คือ ttk.Scale widget ที่ใช้ควบคุมค่า
        """
        frame = tk.Frame(parent, bg=self.bg_color)
        digits = kwargs.pop("digits", 0)

        style = ttk.Style()
        style.configure(
            "Custom.Horizontal.TScale",
            background=self.bg_color,
            troughcolor=self.lighten_color(self.bg_color),
        )

        scale = ttk.Scale(frame, style="Custom.Horizontal.TScale", **kwargs)
        scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

        value_var = tk.StringVar()
        value_label = tk.Label(
            frame, textvariable=value_var, bg=self.bg_color, fg=self.fg_color, width=5
        )
        value_label.pack(side=tk.RIGHT, padx=(5, 0))

        def update_value(event=None):
            value = scale.get()
            value_var.set(f"{value:.{digits}f}")

        scale.bind("<Motion>", update_value)
        scale.bind("<ButtonRelease-1>", update_value)
        update_value()

        return (frame, scale)

    def create_advance_ui_frame(self, parent):
        frame = tk.Frame(parent, bg=self.bg_color)
        return frame

    def create_api_parameter_form(self, parent):
        form_frame = tk.Frame(parent, bg=self.bg_color)

        model_frame = tk.Frame(form_frame, bg=self.bg_color)
        model_frame.pack(fill=tk.X, pady=5)
        model_label = self.create_styled_label(model_frame, "Model:")
        model_label.pack(side=tk.LEFT)
        model_combo = self.create_styled_combobox(
            model_frame, values=["gemini-2.0-flash"]
        )
        model_combo.pack(side=tk.RIGHT, expand=True, fill=tk.X)

        max_tokens_frame = tk.Frame(form_frame, bg=self.bg_color)
        max_tokens_frame.pack(fill=tk.X, pady=5)
        max_tokens_label = self.create_styled_label(max_tokens_frame, "Max Tokens:")
        max_tokens_label.pack(side=tk.LEFT)
        max_tokens_tuple = self.create_styled_scale(
            max_tokens_frame, from_=100, to=1000, orient=tk.HORIZONTAL
        )
        max_tokens_tuple[0].pack(side=tk.RIGHT, expand=True, fill=tk.X)

        temp_frame = tk.Frame(form_frame, bg=self.bg_color)
        temp_frame.pack(fill=tk.X, pady=5)
        temp_label = self.create_styled_label(temp_frame, "Temperature:")
        temp_label.pack(side=tk.LEFT)
        temp_tuple = self.create_styled_scale(
            temp_frame, from_=0.5, to=0.9, orient=tk.HORIZONTAL, digits=2
        )
        temp_tuple[0].pack(side=tk.RIGHT, expand=True, fill=tk.X)

        top_p_frame = tk.Frame(form_frame, bg=self.bg_color)
        top_p_frame.pack(fill=tk.X, pady=5)
        top_p_label = self.create_styled_label(top_p_frame, "Top P:")
        top_p_label.pack(side=tk.LEFT)
        top_p_tuple = self.create_styled_scale(
            top_p_frame, from_=0.5, to=0.9, orient=tk.HORIZONTAL, digits=2
        )
        top_p_tuple[0].pack(side=tk.RIGHT, expand=True, fill=tk.X)

        # Store references
        form_frame.model_combo = model_combo
        form_frame.max_tokens_scale = max_tokens_tuple[1]
        form_frame.temp_scale = temp_tuple[1]
        form_frame.top_p_scale = top_p_tuple[1]

        # Hide top_p for Claude
        def on_model_change(event):
            is_claude = model_combo.get() == "claude-3-haiku"
            if is_claude:
                top_p_frame.pack_forget()
            else:
                top_p_frame.pack(fill=tk.X, pady=5)

        model_combo.bind("<<ComboboxSelected>>", on_model_change)
        return form_frame

    def create_save_button(self, parent, command):
        return self.create_styled_button(parent, "Save", command)

    def create_parameter_description(self, parent):
        desc_frame = tk.Frame(parent, bg=self.bg_color)

        descriptions = {
            "Model": "โมเดล AI ที่ใช้ในการแปลภาษา",
            "Max Tokens": "จำนวนโทเค็นสูงสุดที่ใช้ในการแปล (100-1000)",
            "Temperature": "ความสร้างสรรค์ในการแปล (0.5-0.9)",
            "Top P": "ความหลากหลายของคำศัพท์ (0.5-0.9)",
        }

        for i, (param, desc) in enumerate(descriptions.items()):
            label = self.create_styled_label(desc_frame, f"{param}: {desc}")
            label.pack(anchor="w", pady=2)

        return desc_frame

    def lighten_color(self, color, factor=1.3):
        """เพิ่มความสว่างของสี

        Args:
            color: สี hex code เช่น #RRGGBB
            factor: ค่า factor ที่ใช้ปรับความสว่าง (>1 = สว่างขึ้น)

        Returns:
            str: สีใหม่ในรูปแบบ hex code
        """
        from colorsys import rgb_to_hls, hls_to_rgb
        import re

        # แปลง hex เป็น RGB
        hex_pattern = r"#?([\da-fA-F]{2})([\da-fA-F]{2})([\da-fA-F]{2})"
        if re.match(hex_pattern, color):
            # แยก hex ออกมา
            hex_color = color.lstrip("#")
            r, g, b = [int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
            h, l, s = rgb_to_hls(r, g, b)
            l = min(1.0, l * factor)  # ป้องกันค่าเกิน 1.0
            r, g, b = hls_to_rgb(h, l, s)
            return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
        return color

    def darken_color(self, color, factor=0.7):
        """ลดความสว่างของสี (ทำให้มืดลง)

        Args:
            color: สี hex code เช่น #RRGGBB
            factor: ค่า factor ที่ใช้ปรับความสว่าง (<1 = มืดลง)

        Returns:
            str: สีใหม่ในรูปแบบ hex code
        """
        from colorsys import rgb_to_hls, hls_to_rgb
        import re

        # แปลง hex เป็น RGB
        hex_pattern = r"#?([\da-fA-F]{2})([\da-fA-F]{2})([\da-fA-F]{2})"
        if re.match(hex_pattern, color):
            # แยก hex ออกมา
            hex_color = color.lstrip("#")
            r, g, b = [int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
            h, l, s = rgb_to_hls(r, g, b)
            l = max(0.0, l * factor)  # ป้องกันค่าต่ำกว่า 0.0
            r, g, b = hls_to_rgb(h, l, s)
            return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
        return color

    def create_styled_combobox(self, parent, **kwargs):
        combo = ttk.Combobox(parent, **kwargs)
        combo.configure(style="Custom.TCombobox")
        return combo


appearance_manager = AppearanceManager()
