import os
import logging
from resource_utils import resource_path
import tkinter as tk
import tkinter.font as tkFont
import shutil
import json
from tkinter import filedialog
from tkinter import ttk
from tkinter import messagebox
from typing import List, Dict, Optional, Tuple, Any, Set
import platform
import ctypes
from ctypes import wintypes

# Import สำหรับ metadata extraction และ font validation
try:
    from fontTools.ttLib import TTFont

    FONTTOOLS_AVAILABLE = True
except ImportError:
    FONTTOOLS_AVAILABLE = False
    logging.warning("ไม่พบโมดูล fontTools จะไม่สามารถดึงข้อมูล metadata ของฟอนต์ได้")

try:
    from PIL import Image, ImageDraw, ImageFont

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("ไม่พบโมดูล Pillow จะไม่สามารถตรวจสอบการแสดงผลฟอนต์ได้")

# ตรวจสอบว่ามีโมดูล TkinterDnD2 หรือไม่
try:
    TKDND_AVAILABLE = True
except ImportError:
    TKDND_AVAILABLE = False


class FontObserver:
    """
    Observer interface สำหรับรับการแจ้งเตือนเมื่อมีการเปลี่ยนแปลงฟอนต์
    คลาสอื่นๆ สามารถรับการแจ้งเตือนโดยการ inherit คลาสนี้
    """

    def on_font_changed(self, font_name: str, font_size: int) -> None:
        """
        รับการแจ้งเตือนเมื่อมีการเปลี่ยนแปลงฟอนต์

        Args:
            font_name: ชื่อฟอนต์ใหม่
            font_size: ขนาดฟอนต์ใหม่
        """
        pass


class FontSettings:
    """
    จัดการการตั้งค่าฟอนต์และแจ้งเตือนเมื่อมีการเปลี่ยนแปลง
    ใช้ Observer pattern เพื่อให้คอมโพเนนต์อื่นๆ รับทราบเมื่อมีการเปลี่ยนแปลง
    """

    def __init__(self, settings_manager=None):
        """
        เริ่มต้นการตั้งค่าฟอนต์

        Args:
            settings_manager: ตัวจัดการการตั้งค่าหลัก (ถ้ามี)
        """
        self.observers = []
        self.settings_manager = settings_manager

        # ค่าเริ่มต้น
        self.font_name = "IBM Plex Sans Thai Medium"
        self.font_size = 24

        # โหลดการตั้งค่าจาก settings_manager ถ้ามี
        if settings_manager:
            self.font_name = settings_manager.get("font", self.font_name)
            self.font_size = settings_manager.get("font_size", self.font_size)
        else:
            self.load_settings()

    def add_observer(self, observer):
        """เพิ่ม observer เพื่อรับการแจ้งเตือนเมื่อมีการเปลี่ยนแปลง"""
        if observer not in self.observers:
            self.observers.append(observer)

    def remove_observer(self, observer):
        """ลบ observer ออกจากรายการ"""
        if observer in self.observers:
            self.observers.remove(observer)

    def notify_observers(self):
        """แจ้งเตือน observers ทั้งหมดเมื่อมีการเปลี่ยนแปลง"""
        for observer in self.observers:
            if hasattr(observer, "on_font_changed"):
                observer.on_font_changed(self.font_name, self.font_size)

    def apply_font(self, font_name, font_size):
        """ตั้งค่าฟอนต์ใหม่และแจ้งเตือน observers"""
        try:
            if not font_name or not isinstance(font_size, int):
                return False

            self.font_name = font_name
            self.font_size = font_size

            if self.settings_manager:
                self.settings_manager.set("font", font_name)
                self.settings_manager.set("font_size", font_size)
            else:
                self.save_settings()

            self.notify_observers()
            return True
        except Exception as e:
            logging.error(f"เกิดข้อผิดพลาดในการเปลี่ยนฟอนต์: {e}")
            return False

    def load_settings(self):
        """โหลดการตั้งค่าฟอนต์จากไฟล์"""
        try:
            with open("font_settings.json", "r") as f:
                settings = json.load(f)
                self.font_name = settings.get("font_name", self.font_name)
                self.font_size = settings.get("font_size", self.font_size)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_settings(self):
        """บันทึกการตั้งค่าฟอนต์ลงไฟล์"""
        try:
            settings = {"font_name": self.font_name, "font_size": self.font_size}
            with open("font_settings.json", "w") as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            logging.error(f"เกิดข้อผิดพลาดในการบันทึกการตั้งค่าฟอนต์: {e}")


class FontManager:
    """จัดการฟอนต์ภายในโปรแกรม"""

    def __init__(self, project_dir: Optional[str] = None):
        """สร้าง FontManager"""
        self.project_dir = project_dir or os.getcwd()
        self.fonts_dir = os.path.join(self.project_dir, "fonts")
        self.registered_fonts = set()

        # เพิ่ม font_mapping กลับไปเพื่อความเข้ากันได้กับโค้ดเดิม
        self.font_mapping = {
            "BaiJamjuree-Light": "Bai Jamjuree Light",
            "Bai Jamjuree Light": "Bai Jamjuree Light",
            "FCMinimal": "FC Minimal",
            "NotoSansThaiLooped": "Noto Sans Thai Looped",
            "IBMPlexSansThaiMedium": "IBM Plex Sans Thai Medium",
            "IBM Plex Sans Thai Medium": "IBM Plex Sans Thai Medium",
            "JetBrainsMonoNLLight": "JetBrains Mono NL Light",
            "JetBrains Mono NL Light": "JetBrains Mono NL Light",
            "MaliThin": "MaliThin",
            "Sarabun": "Sarabun",
            "NasalizationRg": "Nasalization Rg",
            "Nasalization Rg": "Nasalization Rg",
            "SegouUILight": "Segou UI Light",
            "segoeuil": "Segou UI Light",
            "anuphan": "Anuphan",
        }

        # สร้างไดเร็กทอรีสำหรับเก็บภาพตัวอย่าง
        self.font_samples_dir = os.path.join(self.fonts_dir, "samples")
        if not os.path.exists(self.font_samples_dir):
            try:
                os.makedirs(self.font_samples_dir)
            except Exception as e:
                logging.error(f"ไม่สามารถสร้างโฟลเดอร์ {self.font_samples_dir}: {e}")

        # สร้างโฟลเดอร์เก็บฟอนต์ถ้ายังไม่มี
        self.ensure_fonts_dir()
        self.move_existing_fonts()
        self.load_and_register_fonts()

        # เก็บฟอนต์ที่โหลดแล้ว
        self.loaded_fonts_info = {}
        self.installed_fonts = set()
        self.project_fonts = set()

    def ensure_fonts_dir(self) -> None:
        """สร้างโฟลเดอร์ fonts ถ้ายังไม่มี"""
        if not os.path.exists(self.fonts_dir):
            try:
                os.makedirs(self.fonts_dir)
                logging.info(f"สร้างโฟลเดอร์ {self.fonts_dir} สำเร็จ")
            except Exception as e:
                logging.error(f"ไม่สามารถสร้างโฟลเดอร์ {self.fonts_dir}: {e}")

    def move_existing_fonts(self) -> None:
        """ย้ายไฟล์ฟอนต์ที่มีอยู่ในโฟลเดอร์หลักไปยังโฟลเดอร์ fonts"""
        try:
            font_files = [
                f
                for f in os.listdir(self.project_dir)
                if f.lower().endswith((".ttf", ".otf"))
                and os.path.isfile(os.path.join(self.project_dir, f))
            ]

            for font_file in font_files:
                src_path = os.path.join(self.project_dir, font_file)
                dst_path = os.path.join(self.fonts_dir, font_file)

                if not os.path.exists(dst_path):
                    shutil.copy2(src_path, dst_path)
                    logging.info(f"คัดลอกไฟล์ {font_file} ไปยังโฟลเดอร์ fonts สำเร็จ")
        except Exception as e:
            logging.error(f"เกิดข้อผิดพลาดในการย้ายไฟล์ฟอนต์: {e}")

    def load_and_register_fonts(self) -> None:
        """โหลดและลงทะเบียนฟอนต์จากโฟลเดอร์ fonts"""
        try:
            if not os.path.exists(self.fonts_dir):
                logging.warning(f"ไม่พบโฟลเดอร์ {self.fonts_dir}")
                return

            font_files = [
                f
                for f in os.listdir(self.fonts_dir)
                if f.lower().endswith((".ttf", ".otf"))
            ]

            # โหลด metadata จาก JSON
            font_db_path = os.path.join(self.fonts_dir, "font_metadata.json")
            font_db = {}
            try:
                with open(font_db_path, "r", encoding="utf-8") as f:
                    font_db = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                font_db = {}

            files_to_rename = []

            for font_file in font_files:
                try:
                    font_path = os.path.join(self.fonts_dir, font_file)

                    if font_file in font_db:
                        metadata = font_db[font_file]
                    else:
                        metadata = self.extract_font_metadata(font_path)
                        font_db[font_file] = metadata

                    needs_rename = False
                    new_font_file = font_file

                    if (
                        metadata
                        and "family_name" in metadata
                        and metadata["family_name"]
                    ):
                        base_name, ext = os.path.splitext(font_file)

                        if base_name != metadata["family_name"]:
                            new_base_name = metadata["family_name"]
                            invalid_chars = [
                                "/",
                                "\\",
                                ":",
                                "*",
                                "?",
                                '"',
                                "<",
                                ">",
                                "|",
                            ]
                            for char in invalid_chars:
                                new_base_name = new_base_name.replace(char, "_")

                            new_font_file = f"{new_base_name}{ext}"

                            counter = 1
                            original_new_font_file = new_font_file
                            while (
                                os.path.exists(
                                    os.path.join(self.fonts_dir, new_font_file)
                                )
                                and new_font_file != font_file
                            ):
                                base, ext = os.path.splitext(original_new_font_file)
                                new_font_file = f"{base}_{counter}{ext}"
                                counter += 1

                            if new_font_file != font_file:
                                files_to_rename.append(
                                    (font_file, new_font_file, metadata)
                                )
                                needs_rename = True

                    if not needs_rename:
                        base_name = os.path.splitext(font_file)[0]

                        if (
                            metadata
                            and "family_name" in metadata
                            and metadata["family_name"]
                        ):
                            real_name = metadata["family_name"]
                            self.font_mapping[base_name] = real_name
                            display_name = real_name
                        else:
                            display_name = self.font_mapping.get(base_name, base_name)

                        self.registered_fonts.add(display_name)
                        logging.info(f"ลงทะเบียนฟอนต์ {display_name} สำเร็จ")

                except Exception as e:
                    logging.error(f"ไม่สามารถลงทะเบียนฟอนต์ {font_file}: {e}")

            # บันทึก metadata
            with open(font_db_path, "w", encoding="utf-8") as f:
                json.dump(font_db, f, ensure_ascii=False, indent=2)

            # เปลี่ยนชื่อไฟล์ฟอนต์และลงทะเบียนใหม่
            for old_file, new_file, metadata in files_to_rename:
                try:
                    old_path = os.path.join(self.fonts_dir, old_file)
                    new_path = os.path.join(self.fonts_dir, new_file)

                    shutil.copy2(old_path, new_path)
                    os.remove(old_path)

                    font_db.pop(old_file, None)
                    font_db[new_file] = metadata

                    base_name = os.path.splitext(new_file)[0]

                    if (
                        metadata
                        and "family_name" in metadata
                        and metadata["family_name"]
                    ):
                        real_name = metadata["family_name"]
                        self.font_mapping[base_name] = real_name
                        display_name = real_name
                    else:
                        display_name = self.font_mapping.get(base_name, base_name)

                    self.registered_fonts.add(display_name)
                    logging.info(
                        f"เปลี่ยนชื่อฟอนต์จาก {old_file} เป็น {new_file} และลงทะเบียนเป็น {display_name} สำเร็จ"
                    )

                except Exception as e:
                    logging.error(
                        f"ไม่สามารถเปลี่ยนชื่อฟอนต์จาก {old_file} เป็น {new_file}: {e}"
                    )

            if files_to_rename:
                with open(font_db_path, "w", encoding="utf-8") as f:
                    json.dump(font_db, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logging.error(f"เกิดข้อผิดพลาดในการโหลดฟอนต์: {e}")

    def get_available_fonts(self) -> List[str]:
        """รับรายชื่อฟอนต์ที่มีในระบบ"""
        try:
            basic_fonts = [
                "Bai Jamjuree Light",
                "FC Minimal",
                "IBM Plex Sans Thai Medium",
                "Noto Sans Thai Looped",
                "JetBrains Mono NL Light",
                "MaliThin",
                "Sarabun",
                "Nasalization Rg",
                "Arial",
                "Helvetica",
                "TkDefaultFont",
            ]

            available_fonts = list(self.registered_fonts) + basic_fonts
            available_fonts = list(set(available_fonts))
            return sorted(available_fonts)
        except Exception as e:
            logging.error(f"เกิดข้อผิดพลาดในการดึงรายชื่อฟอนต์: {e}")
            return ["Arial"]

    # Remove font functionality removed per user request

    def add_font(self, font_path: str) -> bool:
        """เพิ่มฟอนต์ใหม่เข้าระบบ"""
        try:
            if not os.path.exists(font_path):
                logging.error(f"ไม่พบไฟล์ฟอนต์ {font_path}")
                return False

            if not font_path.lower().endswith((".ttf", ".otf")):
                logging.error(f"ไฟล์ {font_path} ไม่ใช่ไฟล์ฟอนต์ที่รองรับ (ttf, otf)")
                return False

            font_file = os.path.basename(font_path)
            metadata = self.extract_font_metadata(font_path)

            if metadata and "family_name" in metadata and metadata["family_name"]:
                base_name, ext = os.path.splitext(font_file)

                if base_name != metadata["family_name"]:
                    new_base_name = metadata["family_name"]
                    invalid_chars = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
                    for char in invalid_chars:
                        new_base_name = new_base_name.replace(char, "_")

                    new_font_file = f"{new_base_name}{ext}"
                    logging.info(
                        f"เปลี่ยนชื่อไฟล์ฟอนต์จาก {font_file} เป็น {new_font_file} ตามตระกูลฟอนต์"
                    )
                    font_file = new_font_file

            dst_path = os.path.join(self.fonts_dir, font_file)

            if os.path.exists(dst_path):
                base_name, ext = os.path.splitext(font_file)
                font_file = f"{base_name}_copy{ext}"
                dst_path = os.path.join(self.fonts_dir, font_file)

            shutil.copy2(font_path, dst_path)

            if not metadata:
                metadata = self.extract_font_metadata(dst_path)

            # เก็บข้อมูลลงใน JSON
            font_db_path = os.path.join(self.fonts_dir, "font_metadata.json")
            try:
                with open(font_db_path, "r", encoding="utf-8") as f:
                    font_db = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                font_db = {}

            font_db[font_file] = metadata

            with open(font_db_path, "w", encoding="utf-8") as f:
                json.dump(font_db, f, ensure_ascii=False, indent=2)

            base_name = os.path.splitext(font_file)[0]

            if metadata and "family_name" in metadata and metadata["family_name"]:
                real_name = metadata["family_name"]
                self.font_mapping[base_name] = real_name
                display_name = real_name
            else:
                display_name = self.font_mapping.get(base_name, base_name)

            self.registered_fonts.add(display_name)

            logging.info(f"เพิ่มฟอนต์ {display_name} สำเร็จ")
            return True

        except Exception as e:
            logging.error(f"เกิดข้อผิดพลาดในการเพิ่มฟอนต์: {e}")
            return False

    def extract_font_metadata(self, font_path: str) -> Dict[str, Any]:
        """ดึงข้อมูล metadata จากไฟล์ฟอนต์"""
        if not FONTTOOLS_AVAILABLE:
            return {
                "error": "ไม่พบโมดูล fontTools",
                "file_name": os.path.basename(font_path),
            }

        try:
            font = TTFont(font_path)

            names = {}
            for record in font["name"].names:
                nameID = record.nameID
                if record.isUnicode():
                    try:
                        text = record.string.decode("utf-16-be")
                    except UnicodeDecodeError:
                        text = record.string.decode("latin-1")
                else:
                    try:
                        text = record.string.decode("latin-1")
                    except UnicodeDecodeError:
                        continue

                if nameID in (1, 2, 4, 6):
                    names[nameID] = text

            supported_scripts = []
            if "cmap" in font:
                cmap = font.getBestCmap()
                has_thai = any(0x0E00 <= char <= 0x0E7F for char in cmap.keys())
                has_latin = any(0x0041 <= char <= 0x007A for char in cmap.keys())

                if has_thai:
                    supported_scripts.append("Thai")
                if has_latin:
                    supported_scripts.append("Latin")

            result = {
                "family_name": names.get(1, ""),
                "subfamily": names.get(2, ""),
                "full_name": names.get(4, ""),
                "postscript_name": names.get(6, ""),
                "file_name": os.path.basename(font_path),
                "supported_scripts": supported_scripts,
            }

            return result
        except Exception as e:
            return {"error": str(e), "file_name": os.path.basename(font_path)}

    def get_font_path(self, font_name: str) -> Optional[str]:
        """ค้นหาที่อยู่ไฟล์ฟอนต์จากชื่อฟอนต์"""
        try:
            reverse_mapping = {v: k for k, v in self.font_mapping.items()}
            file_basename = reverse_mapping.get(font_name, font_name)

            for f in os.listdir(self.fonts_dir):
                if f.lower().endswith((".ttf", ".otf")):
                    base_name = os.path.splitext(f)[0]
                    if (
                        base_name == file_basename
                        or self.font_mapping.get(base_name) == font_name
                    ):
                        return os.path.join(self.fonts_dir, f)

            return None
        except Exception as e:
            logging.error(f"ไม่สามารถหาที่อยู่ไฟล์ฟอนต์ {font_name}: {e}")
            return None

    def validate_font_rendering(
        self, font_name: str, font_size: int = 12
    ) -> Dict[str, Any]:
        """ตรวจสอบว่าฟอนต์แสดงผลได้ถูกต้องหรือไม่"""
        if not PIL_AVAILABLE:
            return {
                "status": "error",
                "message": "ไม่พบโมดูล Pillow ไม่สามารถตรวจสอบการแสดงผลฟอนต์ได้",
            }

        try:
            test_text = "การทดสอบภาษาไทย สวัสดี ABCdef 123 !@#"
            img = Image.new("RGB", (500, 150), color=(255, 255, 255))
            draw = ImageDraw.Draw(img)

            font_path = self.get_font_path(font_name)
            if not font_path:
                return {"status": "error", "message": f"ไม่พบไฟล์ฟอนต์ {font_name}"}

            try:
                font = ImageFont.truetype(font_path, font_size)
            except Exception as e:
                return {"status": "error", "message": f"ไม่สามารถโหลดฟอนต์ได้: {str(e)}"}

            draw.text((10, 10), test_text, font=font, fill=(0, 0, 0))
            draw.text(
                (10, 50), "ทดสอบภาษาไทย: กขคงจฉชฌญฏฐฑฒณดตถ", font=font, fill=(0, 0, 0)
            )
            draw.text(
                (10, 90),
                "English Test: ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                font=font,
                fill=(0, 0, 0),
            )

            metadata = self.extract_font_metadata(font_path)
            metadata_text = f"Font Info: {metadata.get('family_name', 'Unknown')} ({metadata.get('subfamily', '')})"
            draw.text(
                (10, 130),
                metadata_text,
                font=ImageFont.truetype(font_path, 10),
                fill=(100, 100, 100),
            )

            font_basename = os.path.basename(font_path)
            temp_file = os.path.join(self.font_samples_dir, f"test_{font_basename}.png")
            img.save(temp_file)

            has_thai_support = True
            if "supported_scripts" in metadata:
                has_thai_support = "Thai" in metadata["supported_scripts"]

            result = {
                "status": "success",
                "test_image": temp_file,
                "font_name": font_name,
                "real_name": metadata.get("family_name", ""),
                "has_thai_support": has_thai_support,
                "metadata": metadata,
            }

            return result
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_project_fonts(self) -> List[Dict[str, Any]]:
        """รับรายการฟอนต์ในโฟลเดอร์โปรเจค พร้อมข้อมูลและสถานะการติดตั้ง"""
        project_fonts = []
        installed_fonts = set(self.get_system_installed_fonts())

        for font_file in os.listdir(self.fonts_dir):
            if font_file.lower().endswith((".ttf", ".otf")):
                font_path = os.path.join(self.fonts_dir, font_file)

                try:
                    font_info = self.extract_font_metadata(font_path)
                    font_name = font_info.get(
                        "family_name", os.path.splitext(font_file)[0]
                    )
                    is_installed = font_name in installed_fonts

                    font_data = {
                        "file_name": font_file,
                        "file_path": font_path,
                        "font_name": font_name,
                        "installed": is_installed,
                        "metadata": font_info,
                    }

                    project_fonts.append(font_data)

                except Exception as e:
                    logging.error(f"ไม่สามารถอ่านข้อมูลฟอนต์ {font_file}: {e}")

        return project_fonts

    def get_system_installed_fonts(self) -> List[str]:
        """รับรายการฟอนต์ที่ติดตั้งในระบบ"""
        import tkinter.font as tkFont

        root = tk.Tk()
        root.withdraw()
        font_list = tkFont.families()
        root.destroy()

        return list(font_list)

    def install_font(self, font_path: str) -> bool:
        """ติดตั้งฟอนต์ลงในระบบ"""
        try:
            if not os.path.exists(font_path):
                logging.error(f"ไม่พบไฟล์ฟอนต์: {font_path}")
                return False

            import platform

            system = platform.system()
            success = False

            if system == "Windows":
                import ctypes
                from ctypes import wintypes

                class SHFILEOPSTRUCT(ctypes.Structure):
                    _fields_ = [
                        ("hwnd", wintypes.HWND),
                        ("wFunc", ctypes.c_uint),
                        ("pFrom", ctypes.c_char_p),
                        ("pTo", ctypes.c_char_p),
                        ("fFlags", ctypes.c_ushort),
                        ("fAnyOperationsAborted", ctypes.c_bool),
                        ("hNameMappings", ctypes.c_void_p),
                        ("lpszProgressTitle", ctypes.c_char_p),
                    ]

                FO_COPY = 2
                FOF_NOCONFIRMATION = 16
                FOF_NOCONFIRMMKDIR = 512
                FOF_SILENT = 4

                dst_path = os.path.join(os.environ["WINDIR"], "Fonts")
                file_name = os.path.basename(font_path)

                pFrom = (font_path + "\0").encode("utf-8")
                pTo = (dst_path + "\0").encode("utf-8")

                file_op = SHFILEOPSTRUCT()
                file_op.wFunc = FO_COPY
                file_op.pFrom = pFrom
                file_op.pTo = pTo
                file_op.fFlags = FOF_NOCONFIRMATION | FOF_NOCONFIRMMKDIR | FOF_SILENT

                shell32 = ctypes.windll.shell32
                result = shell32.SHFileOperationA(ctypes.byref(file_op))

                if result == 0:
                    try:
                        import winreg

                        with winreg.OpenKey(
                            winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts",
                            0,
                            winreg.KEY_WRITE,
                        ) as key:
                            font_name = self.extract_font_metadata(font_path).get(
                                "full_name", os.path.splitext(file_name)[0]
                            )
                            winreg.SetValueEx(
                                key,
                                f"{font_name} (TrueType)",
                                0,
                                winreg.REG_SZ,
                                file_name,
                            )
                    except Exception as e:
                        logging.warning(f"ไม่สามารถเพิ่มค่าในรีจิสตรี: {e}")

                    success = True

            elif system == "Darwin":  # macOS
                import shutil

                font_dir = os.path.expanduser("~/Library/Fonts")
                target_path = os.path.join(font_dir, os.path.basename(font_path))
                shutil.copy2(font_path, target_path)
                success = True
            elif system == "Linux":
                import shutil

                font_dir = os.path.expanduser("~/.fonts")
                if not os.path.exists(font_dir):
                    os.makedirs(font_dir)
                target_path = os.path.join(font_dir, os.path.basename(font_path))
                shutil.copy2(font_path, target_path)
                os.system("fc-cache -f")
                success = True

            if success:
                logging.info(f"ติดตั้งฟอนต์ {os.path.basename(font_path)} สำเร็จ")
                return True
            else:
                logging.error(f"ไม่สามารถติดตั้งฟอนต์ {os.path.basename(font_path)}")
                return False

        except Exception as e:
            logging.error(f"เกิดข้อผิดพลาดในการติดตั้งฟอนต์: {e}")
            return False

    def install_all_fonts(self) -> Dict[str, bool]:
        """ติดตั้งฟอนต์ทั้งหมดในโฟลเดอร์โปรเจค"""
        results = {}

        project_fonts = self.get_project_fonts()
        for font_data in project_fonts:
            if not font_data["installed"]:
                result = self.install_font(font_data["file_path"])
                results[font_data["file_name"]] = result

        return results


class FontUI:
    """สร้าง UI สำหรับจัดการฟอนต์"""

    def __init__(
        self, parent, font_manager: FontManager, settings=None, apply_callback=None
    ):
        """สร้าง UI สำหรับจัดการฟอนต์"""
        self.parent = parent
        self.font_window = None
        self.font_manager = font_manager
        self.settings = settings
        self.apply_callback = apply_callback

        # ตัวแปรสำหรับเก็บค่าในหน้าจอ
        self.selected_font = tk.StringVar()
        self.font_size = tk.IntVar()
        self.target_mode = tk.StringVar()  # << เพิ่มบรรทัดนี้
        self.sample_text = "ทดสอบฟอนต์ภาษาไทย Aa Bb Cc 123"
        self.notification_label = None
        self.notification_timer = None

        # ค่าเริ่มต้น
        self.font_size.set(settings.get("font_size", 16) if settings else 16)
        # โหลดค่า target mode จาก settings หรือใช้ค่าเริ่มต้น
        saved_target = settings.get("font_target_mode", "translated_ui") if settings else "translated_ui"
        self.target_mode.set(saved_target)

        # ตัวแปรเก็บ reference ของ listbox
        self.font_listbox = None

        # ใช้งาน FontSettings ถ้ามี
        if hasattr(font_manager, "font_settings"):
            self.font_settings = font_manager.font_settings
        else:
            self.font_settings = FontSettings(settings)

        # ตรวจสอบฟอนต์ในโปรเจค
        self.project_fonts = []
        # ปิดการตรวจสอบฟอนต์และการติดตั้งฟอนต์ - ใช้เฉพาะฟอนต์ที่มีอยู่
        self.should_show_install_dialog = False
        # self.check_project_fonts()  # ปิดการตรวจสอบฟอนต์

    def check_project_fonts(self):
        """ตรวจสอบฟอนต์ในโปรเจคและดูว่าควรแสดงหน้าติดตั้งหรือไม่"""
        try:
            self.project_fonts = self.font_manager.get_project_fonts()
            uninstalled_fonts = [f for f in self.project_fonts if not f["installed"]]

            if uninstalled_fonts:
                self.should_show_install_dialog = True
                logging.info(f"พบฟอนต์ที่ยังไม่ได้ติดตั้ง {len(uninstalled_fonts)} รายการ")
            else:
                self.should_show_install_dialog = False
                logging.info("ฟอนต์ทั้งหมดในโปรเจคติดตั้งแล้ว")

        except Exception as e:
            logging.error(f"เกิดข้อผิดพลาดในการตรวจสอบฟอนต์: {e}")
            self.should_show_install_dialog = False

    def _ensure_canvas_background(self):
        """ตรวจสอบและสร้างพื้นหลังให้ canvas ให้แน่ใจว่ามีพื้นหลังเสมอ"""
        try:
            if hasattr(self, "preview_canvas") and self.preview_canvas:
                # ตรวจสอบว่า canvas มี items หรือไม่
                items = self.preview_canvas.find_all()
                if not items:
                    # ถ้าไม่มี items ให้สร้างพื้นหลัง
                    self._create_initial_canvas_background()
                else:
                    # ตรวจสอบว่ามี background tag หรือไม่
                    has_background = False
                    for item in items:
                        tags = self.preview_canvas.gettags(item)
                        if "background" in tags:
                            has_background = True
                            break

                    if not has_background:
                        # ถ้าไม่มี background ให้สร้างใหม่
                        self._create_initial_canvas_background()

                # อัปเดต preview ด้วยฟอนต์ปัจจุบัน
                current_font = (
                    self.selected_font.get()
                    or self.settings.get("font", "IBM Plex Sans Thai Medium")
                    if self.settings
                    else "IBM Plex Sans Thai Medium"
                )
                if current_font:
                    self.update_font_preview(current_font)

        except Exception as e:
            logging.error(f"ไม่สามารถสร้างพื้นหลังให้ canvas: {e}")

    def _create_initial_canvas_background(self):
        """สร้างพื้นหลังเริ่มต้นให้ canvas เพื่อป้องกันการทะลุเห็นพื้นหลัง"""
        try:
            if hasattr(self, "preview_canvas") and self.preview_canvas:
                # ล้าง canvas ก่อน
                self.preview_canvas.delete("all")

                # รอให้ canvas มีขนาดจริง
                self.preview_canvas.update_idletasks()

                # ใช้ winfo_width/height เพื่อให้ได้ขนาดจริง หรือใช้ค่า default ถ้ายังไม่มีขนาด
                canvas_width = self.preview_canvas.winfo_width()
                canvas_height = self.preview_canvas.winfo_height()

                # ถ้าได้ขนาด 1 แสดงว่ายังไม่ได้วาด ให้ใช้ขนาดเริ่มต้น
                if canvas_width <= 1:
                    canvas_width = 500
                if canvas_height <= 1:
                    canvas_height = 220

                # สร้างสี่เหลี่ยมพื้นหลังเต็มขนาด canvas พร้อมขอบเกิน
                self.preview_canvas.create_rectangle(
                    -10,
                    -10,
                    canvas_width + 10,
                    canvas_height + 10,
                    fill="#4a4a4a",
                    outline="#4a4a4a",
                    tags="background",
                )

                # แสดงข้อความเริ่มต้น
                self.preview_canvas.create_text(
                    10,
                    20,
                    text="กำลังโหลดตัวอย่างฟอนต์...",
                    font=("IBM Plex Sans Thai Medium", 12),
                    anchor=tk.NW,
                    fill="#b0b0b0",
                    tags="loading_text",
                )

                # force update ทันที
                self.preview_canvas.update_idletasks()
                self.preview_canvas.update()

        except Exception as e:
            logging.error(f"ไม่สามารถสร้างพื้นหลังเริ่มต้นให้ canvas: {e}")

    def _initialize_ui_content(self):
        """เริ่มต้น content ของ UI หลังจากสร้าง components เสร็จแล้ว"""
        try:
            # รอให้ UI วาดเสร็จสมบูรณ์
            self.font_window.update_idletasks()

            # สร้างพื้นหลังให้ canvas ก่อนอื่น (ป้องกันการทะลุเห็นพื้นหลัง)
            if hasattr(self, "preview_canvas") and self.preview_canvas:
                self._create_initial_canvas_background()
                # force update canvas ทันที
                self.preview_canvas.update()

            # refresh รายการฟอนต์
            self.refresh_font_list()

            # force update preview ด้วยฟอนต์ปัจจุบัน
            current_font = (
                self.settings.get("font", "IBM Plex Sans Thai Medium")
                if self.settings
                else "IBM Plex Sans Thai Medium"
            )
            self.selected_font.set(current_font)

            # อัปเดต preview ทันที
            self.update_font_preview(current_font)

            # รอสักครู่ให้ font list โหลดเสร็จก่อน
            self.font_window.after(20, lambda: self._finalize_ui_setup(current_font))

        except Exception as e:
            logging.error(f"เกิดข้อผิดพลาดในการเริ่มต้น UI content: {e}")

    def _finalize_ui_setup(self, current_font):
        """ขั้นตอนสุดท้ายของการ setup UI"""
        try:
            # update font preview
            self.update_font_preview(current_font)

            # อัปเดต listbox selection ให้ตรงกับฟอนต์ปัจจุบัน
            if hasattr(self, "font_listbox") and self.font_listbox:
                try:
                    available_fonts = self.font_manager.get_available_fonts()
                    if current_font in available_fonts:
                        idx = available_fonts.index(current_font)
                        self.font_listbox.selection_clear(0, tk.END)
                        self.font_listbox.selection_set(idx)
                        self.font_listbox.see(idx)
                except Exception as e:
                    logging.warning(f"ไม่สามารถ select ฟอนต์ในรายการ: {e}")

            # อัปเดต current font label
            if hasattr(self, "current_font_label"):
                current_font_size = (
                    self.settings.get("font_size", 16) if self.settings else 16
                )
                self.current_font_label.config(
                    text=f"ฟอนต์: {current_font} • {current_font_size}px"
                )

            # เลือกแท็บแรกและ force focus
            if hasattr(self, "notebook") and self.notebook:
                self.notebook.select(0)  # เลือกแท็บแรก
                self.notebook.focus_set()

            # force update ทั้งหน้าต่าง
            self.font_window.update()

            logging.info("เริ่มต้น UI content สำเร็จ")

        except Exception as e:
            logging.error(f"เกิดข้อผิดพลาดในการ finalize UI setup: {e}")

    def _force_update_fonts_tab(self):
        """Force update แท็บจัดการฟอนต์"""
        try:
            # สร้างพื้นหลังให้ canvas ก่อนเสมอ
            if hasattr(self, "preview_canvas") and self.preview_canvas:
                # ตรวจสอบว่า canvas มีพื้นหลังแล้วหรือไม่
                items = self.preview_canvas.find_all()
                has_background = False
                for item in items:
                    tags = self.preview_canvas.gettags(item)
                    if "background" in tags:
                        has_background = True
                        break

                # ถ้าไม่มีพื้นหลัง ให้สร้างใหม่
                if not has_background:
                    self._create_initial_canvas_background()

                # force update preview
                current_font = self.selected_font.get() or "IBM Plex Sans Thai Medium"
                self.update_font_preview(current_font)
                self.preview_canvas.update()

            # force update listbox selection
            if hasattr(self, "font_listbox") and self.font_listbox:
                current_font = (
                    self.settings.get("font", "IBM Plex Sans Thai Medium")
                    if self.settings
                    else "IBM Plex Sans Thai Medium"
                )
                try:
                    available_fonts = self.font_manager.get_available_fonts()
                    if current_font in available_fonts:
                        idx = available_fonts.index(current_font)
                        self.font_listbox.selection_clear(0, tk.END)
                        self.font_listbox.selection_set(idx)
                        self.font_listbox.see(idx)
                except:
                    pass

        except Exception as e:
            logging.warning(f"เกิดข้อผิดพลาดใน force update fonts tab: {e}")

    def _force_update_details_tab(self):
        """Force update แท็บรายละเอียดฟอนต์"""
        try:
            # force update validation status
            if hasattr(self, "validation_status"):
                self.validation_status.config(text="เลือกฟอนต์และกดปุ่มตรวจสอบ")

        except Exception as e:
            logging.warning(f"เกิดข้อผิดพลาดใน force update details tab: {e}")

    def _apply_rounded_corners(self):
        """ใช้ Windows API เพื่อสร้างมุมโค้งมนให้กับหน้าต่าง (สำหรับ Windows เท่านั้น)"""
        if platform.system() != "Windows":
            return

        try:
            # ตรวจสอบว่าหน้าต่างยังมีอยู่
            if (
                not hasattr(self, "font_window")
                or not self.font_window
                or not self.font_window.winfo_exists()
            ):
                return

            self.font_window.update_idletasks()
            CORNER_RADIUS = 20

            # ตรวจสอบขนาดหน้าต่างก่อนดำเนินการ
            width = self.font_window.winfo_width()
            height = self.font_window.winfo_height()

            # ป้องกันขนาดผิดปกติ
            if width <= 0 or height <= 0 or width > 2000 or height > 1500:
                logging.warning(
                    f"ขนาดหน้าต่างผิดปกติ: {width}x{height}, ข้าม rounded corners"
                )
                return

            hwnd = self.font_window.winfo_id()
            if not hwnd:
                return

            gdi32 = ctypes.windll.gdi32
            user32 = ctypes.windll.user32

            # สร้าง region อย่างปลอดภัย
            hRgn = gdi32.CreateRoundRectRgn(
                0, 0, width, height, CORNER_RADIUS, CORNER_RADIUS
            )

            if hRgn:
                user32.SetWindowRgn(hwnd, hRgn, True)
                # เก็บ reference ของ region ไว้
                self.font_window.hRgn = hRgn
            else:
                logging.warning("ไม่สามารถสร้าง rounded region ได้")

        except Exception as e:
            logging.error(f"ไม่สามารถสร้างมุมโค้งมนได้: {e}")
            # ไม่ให้ error นี้ขัดขวางการทำงานของโปรแกรม

    def _start_move(self, event):
        """บันทึกตำแหน่งเริ่มต้นของการคลิกเมาส์"""
        self._offset_x = event.x
        self._offset_y = event.y

    def _stop_move(self, event):
        """รีเซ็ตตำแหน่งเมื่อปล่อยเมาส์"""
        self._offset_x = None
        self._offset_y = None

    def _on_motion(self, event):
        """ย้ายตำแหน่งหน้าต่างตามการลากเมาส์"""
        if hasattr(self, "_offset_x") and self._offset_x is not None:
            x = self.font_window.winfo_rootx() + event.x - self._offset_x
            y = self.font_window.winfo_rooty() + event.y - self._offset_y
            self.font_window.geometry(f"+{x}+{y}")

    def open_font_ui(self, translated_ui=None):
        """เปิดหน้าต่างจัดการฟอนต์ (ดีไซน์ใหม่ ไร้ขอบ มุมโค้งมน)"""
        try:
            if (
                hasattr(self, "font_window")
                and self.font_window
                and self.font_window.winfo_exists()
            ):
                # ถ้าหน้าต่างแสดงอยู่ ให้ปิด (toggle behavior)
                if self.font_window.winfo_viewable():
                    self.close_font_ui()
                    return
                # ถ้าหน้าต่างถูก minimize ให้ restore
                else:
                    self.font_window.lift()
                    self.font_window.focus_set()
                    return

            self.translated_ui = translated_ui
            if self.translated_ui and hasattr(self.translated_ui, "pause_fade_out"):
                try:
                    self.translated_ui.pause_fade_out()
                except Exception as e:
                    logging.error(f"Error pausing fade out effect: {e}")

            self.font_window = tk.Toplevel(self.parent)
            self.font_window.title("จัดการฟอนต์บน TUI และ LOG")
            self.font_window.configure(bg="#2e2e2e")
            self.font_window.overrideredirect(True)

            self._offset_x = None
            self._offset_y = None

            self._is_resizing = False
            self._offset_x = None
            self._offset_y = None

            self.font_window.bind("<ButtonRelease-1>", self._on_release)

            def on_configure(event):
                if event.widget == self.font_window:
                    try:
                        width = event.width
                        height = event.height

                        min_w = getattr(self, "min_width", 600)
                        min_h = getattr(self, "min_height", 400)
                        max_w = getattr(self, "max_width", 1200)
                        max_h = getattr(self, "max_height", 800)

                        if (
                            width < min_w
                            or width > max_w
                            or height < min_h
                            or height > max_h
                        ):
                            corrected_width = max(min_w, min(width, max_w))
                            corrected_height = max(min_h, min(height, max_h))

                            if width != corrected_width or height != corrected_height:
                                logging.warning(
                                    f"แก้ไขขนาดจาก {width}x{height} เป็น {corrected_width}x{corrected_height}"
                                )
                                self.font_window.after_idle(
                                    lambda: self.font_window.geometry(
                                        f"{corrected_width}x{corrected_height}"
                                    )
                                )

                    except Exception as e:
                        logging.error(f"เกิดข้อผิดพลาดในการตรวจสอบ configure: {e}")

                self._apply_rounded_corners()

            self.font_window.bind("<Configure>", on_configure)

            window_width = 880  # Increased width for better content space
            window_height = 620  # Increased height for better content space

            min_width = 650    # Increased minimum width
            min_height = 480   # Increased minimum height
            max_width = 1400   # Increased maximum width
            max_height = 900   # Increased maximum height

            self.font_window.minsize(min_width, min_height)
            self.font_window.maxsize(max_width, max_height)

            self.min_width = min_width
            self.min_height = min_height
            self.max_width = max_width
            self.max_height = max_height

            screen_width = self.font_window.winfo_screenwidth()
            screen_height = self.font_window.winfo_screenheight()
            position_x = int((screen_width - window_width) / 2)
            position_y = int((screen_height - window_height) / 2)

            if window_width > max_width:
                window_width = max_width
            if window_height > max_height:
                window_height = max_height

            self.font_window.geometry(
                f"{window_width}x{window_height}+{position_x}+{position_y}"
            )

            self.font_window.transient(None)
            self.font_window.attributes("-topmost", True)

            if hasattr(self.parent, "winfo_toplevel"):
                try:
                    parent_window = self.parent.winfo_toplevel()
                    self.font_window.lift(parent_window)
                except:
                    pass

            try:
                if os.path.exists(resource_path(os.path.join("assets", "fonts.ico"))):
                    self.font_window.iconbitmap(resource_path(os.path.join("assets", "fonts.ico")))
            except Exception as e:
                logging.error(f"Error setting icon: {e}")

            self.font_window.protocol("WM_DELETE_WINDOW", self.on_font_window_close)

            if self.should_show_install_dialog:
                self.show_font_installation_dialog()
            else:
                self.create_font_ui_components()

                def on_window_mapped(event):
                    if event.widget == self.font_window:
                        if hasattr(self, "preview_canvas") and self.preview_canvas:
                            self._create_initial_canvas_background()
                            self.preview_canvas.update()
                        self.font_window.unbind("<Map>")

                self.font_window.bind("<Map>", on_window_mapped)

                self.font_window.after(50, self._initialize_ui_content)
                self.font_window.after(100, self.create_notification_area)
                self.font_window.after(200, self._ensure_canvas_background)
                self.font_window.after(
                    350, self._safe_update_target_colors
                )  # << เพิ่มบรรทัดนี้

            self.font_window.after(10, self._apply_rounded_corners)

            logging.info("สร้างหน้าต่างจัดการฟอนต์ (ดีไซน์ไร้ขอบ) สำเร็จ")
        except Exception as e:
            logging.error(f"เกิดข้อผิดพลาดในการสร้างหน้าต่างจัดการฟอนต์: {e}")
            messagebox.showerror("Error", f"เกิดข้อผิดพลาด: {e}")

    def show_font_installation_dialog(self):
        """แสดงหน้าจอติดตั้งฟอนต์"""
        # ตรวจสอบว่ามี font_window หรือไม่
        if not self.font_window:
            logging.error("Font window is None, cannot show installation dialog")
            return
            
        # ลบ components เดิมถ้ามี
        for widget in self.font_window.winfo_children():
            widget.destroy()

        main_frame = tk.Frame(self.font_window, bg="#2e2e2e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # แสดงหัวข้อ
        header_label = tk.Label(
            main_frame,
            text="ติดตั้งฟอนต์สำหรับโปรแกรม",
            font=("IBM Plex Sans Thai Medium", 16),
            bg="#2e2e2e",
            fg="#e0e0e0",
        )
        header_label.pack(pady=(0, 10))

        # คำอธิบาย
        description = tk.Label(
            main_frame,
            text="พบฟอนต์ที่ยังไม่ได้ติดตั้งในเครื่องของคุณ หากต้องการใช้งานฟอนต์เหล่านี้ในโปรแกรม คุณจำเป็นต้องติดตั้งก่อน",
            font=("IBM Plex Sans Thai Medium", 11),
            bg="#2e2e2e",
            fg="#e0e0e0",
            wraplength=480,
            justify=tk.CENTER,
        )
        description.pack(pady=(0, 20))

        # สร้างกรอบสำหรับแสดงรายการฟอนต์
        fonts_frame = tk.Frame(main_frame, bg="#3a3a3a")
        fonts_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # สร้างหัวข้อตาราง
        headers_frame = tk.Frame(fonts_frame, bg="#4a4a4a")
        headers_frame.pack(fill=tk.X, padx=10, pady=5)

        # คอลัมน์
        tk.Label(
            headers_frame,
            text="ไฟล์ฟอนต์",
            font=("IBM Plex Sans Thai Medium", 11),
            width=25,
            anchor=tk.W,
            bg="#4a4a4a",
            fg="#e0e0e0",
            padx=10,
        ).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        tk.Label(
            headers_frame,
            text="ชื่อฟอนต์",
            font=("IBM Plex Sans Thai Medium", 11),
            width=25,
            anchor=tk.W,
            bg="#4a4a4a",
            fg="#e0e0e0",
            padx=10,
        ).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        tk.Label(
            headers_frame,
            text="สถานะ",
            font=("IBM Plex Sans Thai Medium", 11),
            width=15,
            anchor=tk.W,
            bg="#4a4a4a",
            fg="#e0e0e0",
            padx=10,
        ).grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)

        # สร้างฟรีมสำหรับแสดงรายการฟอนต์ (มี scrollbar)
        list_frame = tk.Frame(fonts_frame, bg="#3a3a3a")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # สร้าง Canvas สำหรับ scrolling
        canvas = tk.Canvas(list_frame, bg="#3a3a3a", highlightthickness=0, bd=0)

        # สร้าง scrollbar แบบ ttk ที่มีสีเข้ากับธีม
        scrollbar_frame = tk.Frame(list_frame, bg="#3a3a3a")
        scrollbar_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # สร้าง style สำหรับ scrollbar ที่ไม่มีขอบ
        if not hasattr(self, "style"):
            self.style = ttk.Style()
            self.style.theme_use("clam")
        
        self.style.configure(
            "Vertical.TScrollbar",
            background="#4a4a4a",
            troughcolor="#2e2e2e",
            bordercolor="#2e2e2e",
            arrowcolor="#b0b0b0",
            darkcolor="#4a4a4a",
            lightcolor="#4a4a4a",
            borderwidth=0,
            relief=tk.FLAT,
            width=12,
        )

        # ใช้ ttk scrollbar แทน tk scrollbar
        scrollbar = ttk.Scrollbar(
            scrollbar_frame,
            orient=tk.VERTICAL,
            command=canvas.yview,
            style="Vertical.TScrollbar",
        )

        # ผูก scrollbar กับ canvas
        canvas.configure(yscrollcommand=scrollbar.set)

        # วาง canvas และ scrollbar
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # สร้าง frame ใน canvas สำหรับใส่รายการฟอนต์
        font_list_frame = tk.Frame(canvas, bg="#3a3a3a")
        canvas.create_window(
            (0, 0), window=font_list_frame, anchor=tk.NW, tags="font_list_frame"
        )

        # คำนวณจำนวนฟอนต์ที่ยังไม่ได้ติดตั้ง
        uninstalled_fonts = [f for f in self.project_fonts if not f["installed"]]

        # แสดงรายการฟอนต์
        row = 0
        for font in uninstalled_fonts:
            # สีพื้นหลังสลับแถว - ใช้เฉดสีเทา
            bg_color = "#404040" if row % 2 == 0 else "#484848"

            font_frame = tk.Frame(font_list_frame, bg=bg_color)
            font_frame.pack(fill=tk.X, pady=1)

            # แสดงชื่อไฟล์ฟอนต์
            tk.Label(
                font_frame,
                text=font["file_name"],
                font=("IBM Plex Sans Thai Medium", 11),
                width=25,
                anchor=tk.W,
                bg=bg_color,
                fg="#e0e0e0",
                padx=10,
            ).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

            # แสดงชื่อฟอนต์
            tk.Label(
                font_frame,
                text=font["font_name"],
                font=("IBM Plex Sans Thai Medium", 11),
                width=25,
                anchor=tk.W,
                bg=bg_color,
                fg="#e0e0e0",
                padx=10,
            ).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

            # แสดงสถานะ
            status_text = "ไม่ได้ติดตั้ง" if not font["installed"] else "ติดตั้งแล้ว"
            status_color = "#f44336" if not font["installed"] else "#4CAF50"

            tk.Label(
                font_frame,
                text=status_text,
                font=("IBM Plex Sans Thai Medium", 11),
                width=15,
                anchor=tk.W,
                bg=bg_color,
                fg=status_color,
                padx=10,
            ).grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)

            row += 1

        # อัปเดต scrollregion หลังจากใส่รายการทั้งหมด
        font_list_frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

        # สร้างปุ่มกดติดตั้ง
        button_frame = tk.Frame(main_frame, bg="#2e2e2e")
        button_frame.pack(fill=tk.X, pady=20)

        # ปุ่มข้าม
        skip_button = tk.Button(
            button_frame,
            text="ข้าม",
            font=("IBM Plex Sans Thai Medium", 11),
            bg="#5a5a5a",
            fg="#e0e0e0",
            padx=15,
            pady=8,
            bd=0,
            cursor="hand2",
            command=self.skip_installation,
        )
        skip_button.pack(side=tk.LEFT, padx=10)

        # เพิ่มปุ่มเปิดโฟลเดอร์
        open_folder_button = tk.Button(
            button_frame,
            text="เปิดโฟลเดอร์ fonts",
            font=("IBM Plex Sans Thai Medium", 11),
            bg="#FF9800",
            fg="#e0e0e0",
            padx=15,
            pady=8,
            bd=0,
            cursor="hand2",
            command=self.open_fonts_folder,
        )
        open_folder_button.pack(side=tk.RIGHT, padx=(0, 10))

        # ปุ่มติดตั้งทั้งหมด
        install_button = tk.Button(
            button_frame,
            text=f"ติดตั้งฟอนต์ทั้งหมด ({len(uninstalled_fonts)} รายการ)",
            font=("IBM Plex Sans Thai Medium", 11),
            bg="#4CAF50",
            fg="#e0e0e0",
            padx=15,
            pady=8,
            bd=0,
            cursor="hand2",
            command=self.install_all_project_fonts,
        )
        install_button.pack(side=tk.RIGHT, padx=10)

        # เพิ่ม hover effect แบบขอบบางๆ
        def create_install_hover_handlers(btn, hover_c):
            def on_enter(e):
                btn.config(highlightbackground=hover_c, highlightthickness=1)

            def on_leave(e):
                btn.config(highlightbackground=btn["bg"], highlightthickness=0)

            return on_enter, on_leave

        skip_enter, skip_leave = create_install_hover_handlers(skip_button, "#6a6a6a")
        skip_button.bind("<Enter>", skip_enter)
        skip_button.bind("<Leave>", skip_leave)

        folder_enter, folder_leave = create_install_hover_handlers(
            open_folder_button, "#F57C00"
        )
        open_folder_button.bind("<Enter>", folder_enter)
        open_folder_button.bind("<Leave>", folder_leave)

        install_enter, install_leave = create_install_hover_handlers(
            install_button, "#388E3C"
        )
        install_button.bind("<Enter>", install_enter)
        install_button.bind("<Leave>", install_leave)

        # เพิ่มข้อความคำแนะนำ
        hint_label = tk.Label(
            main_frame,
            text="คำแนะนำ: หากการติดตั้งอัตโนมัติไม่ทำงาน ให้กดปุ่ม 'เปิดโฟลเดอร์ fonts' และคัดลอกไฟล์ฟอนต์ไปติดตั้งเอง",
            font=("IBM Plex Sans Thai Medium", 9),
            bg="#2e2e2e",
            fg="#FFEB3B",
            wraplength=480,
        )
        hint_label.pack(pady=(0, 5))

    def open_fonts_folder(self):
        """เปิดโฟลเดอร์ fonts ของโปรเจค"""
        try:
            if os.path.exists(self.font_manager.fonts_dir):
                import platform

                system = platform.system()

                if system == "Windows":
                    os.startfile(self.font_manager.fonts_dir)
                elif system == "Darwin":  # macOS
                    import subprocess

                    subprocess.Popen(["open", self.font_manager.fonts_dir])
                else:  # Linux และระบบอื่นๆ
                    import subprocess

                    subprocess.Popen(["xdg-open", self.font_manager.fonts_dir])

                self.show_temporary_notification("เปิดโฟลเดอร์ fonts สำเร็จ")
                return True
            else:
                self.show_temporary_notification("ไม่พบโฟลเดอร์ fonts", color="#d32f2f")
                return False
        except Exception as e:
            logging.error(f"เกิดข้อผิดพลาดในการเปิดโฟลเดอร์ fonts: {e}")
            self.show_temporary_notification(f"เกิดข้อผิดพลาด: {e}", color="#d32f2f")
            return False

    def skip_installation(self):
        """ข้ามการติดตั้งฟอนต์"""
        try:
            # ตรวจสอบว่ามี font_window หรือไม่
            if not self.font_window:
                logging.error("Font window is None, cannot skip installation")
                return
                
            # ลบ widgets ในหน้าจอติดตั้ง
            for widget in self.font_window.winfo_children():
                widget.destroy()

            # เปิดหน้าจอจัดการฟอนต์ปกติ
            self.create_font_ui_components()
            self.refresh_font_list()
            self.create_notification_area()

            # ไม่แสดงหน้าจอติดตั้งอีก
            self.should_show_install_dialog = False
        except Exception as e:
            logging.error(f"เกิดข้อผิดพลาดในการเปลี่ยนไปหน้าจัดการฟอนต์: {e}")
            try:
                # สร้างหน้าจอใหม่แบบง่ายๆ
                self.font_window.title("จัดการฟอนต์บน TUI และ LOG")
                simple_frame = tk.Frame(self.font_window, bg="#2e2e2e")
                simple_frame.pack(fill=tk.BOTH, expand=True)

                warning_label = tk.Label(
                    simple_frame,
                    text="เกิดข้อผิดพลาดในการแสดงหน้าจัดการฟอนต์\nโปรดปิดหน้าต่างนี้และเปิดใหม่",
                    font=("IBM Plex Sans Thai Medium", 14),
                    bg="#2e2e2e",
                    fg="#FF9800",
                    pady=30,
                )
                warning_label.pack()

                close_button = tk.Button(
                    simple_frame,
                    text="ปิดหน้าต่าง",
                    font=("IBM Plex Sans Thai Medium", 12),
                    bg="#d32f2f",
                    fg="#e0e0e0",
                    padx=15,
                    pady=8,
                    bd=0,
                    cursor="hand2",
                    command=self.close_font_ui,
                )
                close_button.pack(pady=10)

                self.should_show_install_dialog = False
            except:
                logging.error("เกิดข้อผิดพลาดร้ายแรง กำลังปิดหน้าต่าง")
                try:
                    self.font_window.destroy()
                    self.font_window = None
                except:
                    pass

    def install_all_project_fonts(self):
        """ติดตั้งฟอนต์ทั้งหมดในโปรเจค"""
        # แสดง loading dialog
        loading_frame = tk.Frame(self.font_window, bg="#2e2e2e")
        loading_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=400, height=200)

        # แสดงข้อความ
        loading_label = tk.Label(
            loading_frame,
            text="กำลังติดตั้งฟอนต์...",
            font=("IBM Plex Sans Thai Medium", 14),
            bg="#2e2e2e",
            fg="#e0e0e0",
        )
        loading_label.pack(pady=20)

        # สร้าง progress bar แบบ styled
        if not hasattr(self, "style"):
            self.style = ttk.Style()
            self.style.theme_use("clam")

        self.style.configure(
            "TProgressbar",
            background="#3a71c7",
            troughcolor="#4a4a4a",
            bordercolor="#2e2e2e",
            lightcolor="#3a71c7",
            darkcolor="#3a71c7",
        )

        progress = ttk.Progressbar(
            loading_frame, mode="indeterminate", style="TProgressbar"
        )
        progress.pack(fill=tk.X, padx=20, pady=10)
        progress.start()

        # อัปเดต UI
        self.font_window.update()

        try:
            # ติดตั้งฟอนต์ทั้งหมด
            results = self.font_manager.install_all_fonts()

            # ตรวจสอบผลลัพธ์
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)

            # ลบ loading frame
            loading_frame.destroy()

            # แสดงผลลัพธ์
            if success_count == total_count and total_count > 0:
                messagebox.showinfo(
                    "ติดตั้งสำเร็จ", f"ติดตั้งฟอนต์ทั้งหมด {success_count} รายการเรียบร้อยแล้ว"
                )
            elif success_count > 0:
                messagebox.showwarning(
                    "ติดตั้งบางส่วน", f"ติดตั้งสำเร็จ {success_count} จาก {total_count} รายการ"
                )
            else:
                messagebox.showerror(
                    "ติดตั้งไม่สำเร็จ", "ไม่สามารถติดตั้งฟอนต์ได้ โปรดติดตั้งฟอนต์ด้วยตนเอง"
                )

            # อัปเดตรายการฟอนต์ในระบบ (ปิดการทำงาน)
            # self.check_project_fonts()

            # รีเฟรชหน้าจอ UI ปกติ
            if self.font_window:
                for widget in self.font_window.winfo_children():
                    widget.destroy()
            else:
                logging.error("Font window is None, cannot refresh UI")
                return

            # สร้าง UI ใหม่
            self.create_font_ui_components()
            self.refresh_font_list()
            self.create_notification_area()

            # ปิดแฟล็กไม่ให้แสดงหน้าต่างติดตั้งอีก
            self.should_show_install_dialog = False

        except Exception as e:
            # ลบ loading frame
            try:
                loading_frame.destroy()
            except:
                pass

            logging.error(f"เกิดข้อผิดพลาดในการติดตั้งฟอนต์: {e}")
            messagebox.showerror("Error", f"เกิดข้อผิดพลาดในการติดตั้งฟอนต์: {e}")

            try:
                if self.font_window:
                    for widget in self.font_window.winfo_children():
                        widget.destroy()
                    self.create_font_ui_components()
                else:
                    logging.error("Font window is None, cannot create UI components")
                self.refresh_font_list()
                self.create_notification_area()

                self.should_show_install_dialog = False
            except Exception as ex:
                logging.error(f"ไม่สามารถสร้างหน้าจอใหม่ได้: {ex}")
                try:
                    simple_frame = tk.Frame(self.font_window, bg="#2e2e2e")
                    simple_frame.pack(fill=tk.BOTH, expand=True)

                    tk.Label(
                        simple_frame,
                        text="เกิดข้อผิดพลาดในการติดตั้งฟอนต์\nโปรดปิดหน้าต่างนี้และเปิดใหม่",
                        font=("IBM Plex Sans Thai Medium", 14),
                        bg="#2e2e2e",
                        fg="#FF9800",
                        pady=30,
                    ).pack()

                    tk.Button(
                        simple_frame,
                        text="ปิดหน้าต่าง",
                        font=("IBM Plex Sans Thai Medium", 12),
                        bg="#d32f2f",
                        fg="#e0e0e0",
                        padx=15,
                        pady=8,
                        bd=0,
                        command=self.close_font_ui,
                    ).pack(pady=10)
                except:
                    try:
                        self.close_font_ui()
                    except:
                        if self.font_window:
                            self.font_window.destroy()
                            self.font_window = None

    def on_font_window_close(self):
        """จัดการเมื่อปิดหน้าต่าง font manager"""
        try:
            self.font_window.destroy()
            self.font_window = None
        except Exception as e:
            logging.error(f"Error closing font window: {e}")
            try:
                if self.font_window:
                    self.font_window.destroy()
            except:
                pass

    def _start_resize(self, event):
        """บันทึกสถานะเริ่มต้นก่อนการปรับขนาด พร้อมการป้องกันปัญหา"""
        try:
            # ตรวจสอบว่าหน้าต่างยังคงมีอยู่
            if not self.font_window or not self.font_window.winfo_exists():
                return

            self._is_resizing = True

            # บันทึกขนาดและตำแหน่งปัจจุบัน
            self._start_width = self.font_window.winfo_width()
            self._start_height = self.font_window.winfo_height()
            self._start_x = event.x_root
            self._start_y = event.y_root

            # ป้องกันค่าผิดปกติ
            if self._start_width <= 0 or self._start_height <= 0:
                logging.warning("ขนาดหน้าต่างผิดปกติ กำลังรีเซ็ต...")
                self._start_width = getattr(self, "min_width", 600)
                self._start_height = getattr(self, "min_height", 400)

            # จำกัดขนาดเริ่มต้นให้อยู่ในขอบเขตที่ปลอดภัย
            min_w = getattr(self, "min_width", 600)
            min_h = getattr(self, "min_height", 400)
            max_w = getattr(self, "max_width", 1200)
            max_h = getattr(self, "max_height", 800)

            self._start_width = max(min_w, min(self._start_width, max_w))
            self._start_height = max(min_h, min(self._start_height, max_h))

        except Exception as e:
            logging.error(f"เกิดข้อผิดพลาดในการเริ่ม resize: {e}")
            self._is_resizing = False

    def _do_resize(self, event):
        """คำนวณและปรับขนาดหน้าต่างขณะลากเมาส์ พร้อมการป้องกันปัญหา"""
        if not hasattr(self, "_is_resizing") or not self._is_resizing:
            return

        try:
            # คำนวณขนาดใหม่
            delta_x = event.x_root - self._start_x
            delta_y = event.y_root - self._start_y
            new_width = self._start_width + delta_x
            new_height = self._start_height + delta_y

            # ใช้ขนาดที่กำหนดไว้ หรือค่าเริ่มต้นถ้าไม่มี
            min_w = getattr(self, "min_width", 600)
            min_h = getattr(self, "min_height", 400)
            max_w = getattr(self, "max_width", 1200)
            max_h = getattr(self, "max_height", 800)

            # จำกัดขนาดให้อยู่ในขอบเขตที่ปลอดภัย
            new_width = max(min_w, min(new_width, max_w))
            new_height = max(min_h, min(new_height, max_h))

            # ตรวจสอบขนาดหน้าจอเพื่อป้องกันการขยายเกินขอบจอ
            try:
                screen_width = self.font_window.winfo_screenwidth()
                screen_height = self.font_window.winfo_screenheight()

                # ลดขนาดลงหากใกล้เกินขอบจอ (เหลือที่ว่าง 50px)
                if new_width > screen_width - 50:
                    new_width = screen_width - 50
                if new_height > screen_height - 50:
                    new_height = screen_height - 50

            except Exception as e:
                logging.warning(f"ไม่สามารถตรวจสอบขนาดหน้าจอ: {e}")

            # ปรับขนาดหน้าต่างอย่างปลอดภัย
            try:
                current_geometry = self.font_window.geometry()
                # ดึงตำแหน่งปัจจุบัน
                if "+" in current_geometry:
                    size_part, pos_part = current_geometry.split("+", 1)
                    if "+" in pos_part:
                        x_pos, y_pos = pos_part.split("+")
                    else:
                        x_pos, y_pos = pos_part.split("-")
                        y_pos = "-" + y_pos

                    # ตรวจสอบตำแหน่งไม่ให้เกินขอบจอ
                    x_pos = max(0, min(int(x_pos), screen_width - new_width))
                    y_pos = max(0, min(int(y_pos), screen_height - new_height))

                    self.font_window.geometry(
                        f"{new_width}x{new_height}+{x_pos}+{y_pos}"
                    )
                else:
                    self.font_window.geometry(f"{new_width}x{new_height}")

            except Exception as e:
                logging.error(f"เกิดข้อผิดพลาดในการปรับขนาดหน้าต่าง: {e}")
                # หยุดการ resize หากเกิดข้อผิดพลาด
                self._is_resizing = False

        except Exception as e:
            logging.error(f"เกิดข้อผิดพลาดร้ายแรงในการ resize: {e}")
            # หยุดการ resize และรีเซ็ตสถานะ
            self._is_resizing = False

    def _on_release(self, event):
        """จัดการเมื่อปล่อยปุ่มเมาส์ หยุดทั้งการลากและการปรับขนาด"""
        try:
            # รีเซ็ตสถานะการลาก
            self._offset_x = None
            self._offset_y = None

            # รีเซ็ตสถานะการปรับขนาดอย่างปลอดภัย
            if hasattr(self, "_is_resizing"):
                self._is_resizing = False

            # ตรวจสอบและแก้ไขขนาดหน้าต่างหากผิดปกติ
            if (
                hasattr(self, "font_window")
                and self.font_window
                and self.font_window.winfo_exists()
            ):
                try:
                    current_width = self.font_window.winfo_width()
                    current_height = self.font_window.winfo_height()

                    # ใช้ขนาดที่กำหนดไว้
                    min_w = getattr(self, "min_width", 600)
                    min_h = getattr(self, "min_height", 400)
                    max_w = getattr(self, "max_width", 1200)
                    max_h = getattr(self, "max_height", 800)

                    # แก้ไขขนาดหากผิดปกติ
                    corrected = False
                    if current_width < min_w or current_width > max_w:
                        current_width = max(min_w, min(current_width, max_w))
                        corrected = True
                    if current_height < min_h or current_height > max_h:
                        current_height = max(min_h, min(current_height, max_h))
                        corrected = True

                    if corrected:
                        logging.info(
                            f"แก้ไขขนาดหน้าต่างเป็น {current_width}x{current_height}"
                        )
                        self.font_window.geometry(f"{current_width}x{current_height}")

                except Exception as e:
                    logging.warning(f"ไม่สามารถตรวจสอบขนาดหน้าต่างหลัง release: {e}")

        except Exception as e:
            logging.error(f"เกิดข้อผิดพลาดใน _on_release: {e}")
            # รีเซ็ตสถานะแบบบังคับหากเกิดข้อผิดพลาด
            self._offset_x = None
            self._offset_y = None
            if hasattr(self, "_is_resizing"):
                self._is_resizing = False

    def _start_resize_panels(self, event):
        """เริ่มการ resize list/preview panels"""
        self._resize_start_x = event.x_root
        self._resize_start_width = self.list_width

    def _on_resize_panels(self, event):
        """จัดการการ resize list/preview panels"""
        try:
            delta = event.x_root - self._resize_start_x
            new_width = max(200, min(600, self._resize_start_width + delta))
            
            self.list_width = new_width
            self.list_frame.config(width=new_width)
            
        except Exception as e:
            logging.error(f"Error during panel resize: {e}")

    def _end_resize_panels(self, event):
        """จบการ resize list/preview panels"""
        pass  # Clean up if needed

    def create_font_ui_components(self) -> None:
        """สร้าง UI สำหรับจัดการฟอนต์"""
        main_frame = tk.Frame(self.font_window, bg="#2e2e2e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        if not hasattr(self, "style"):
            self.style = ttk.Style()
            self.style.theme_use("clam")

        header_frame = tk.Frame(main_frame, bg="#2e2e2e")
        header_frame.pack(fill=tk.X, pady=(0, 5))

        header_label = tk.Label(
            header_frame,
            text="จัดการฟอนต์บน TUI และ LOG",
            font=("IBM Plex Sans Thai Medium", 12),
            bg="#2e2e2e",
            fg="#e0e0e0",
        )
        header_label.pack(side=tk.LEFT, padx=10)

        close_button = tk.Button(
            header_frame,
            text="✕",
            font=("Arial", 14),
            bg="#2e2e2e",
            fg="#e0e0e0",
            bd=0,
            cursor="hand2",
            command=self.on_font_window_close,
            activebackground="#c62828",
            activeforeground="#e0e0e0",
        )
        close_button.pack(side=tk.RIGHT, padx=5, pady=0)

        # Make drag area wider - bind to main areas for better UX
        def bind_drag_to_widget(widget):
            try:
                widget.bind("<Button-1>", self._start_move)
                widget.bind("<B1-Motion>", self._on_motion)
            except:
                pass  # Skip if widget doesn't exist yet
        
        # Bind initially available widgets
        for widget in [header_frame, header_label, main_frame]:
            bind_drag_to_widget(widget)
        
        # Store binding function for later use
        self._bind_drag_to_widget = bind_drag_to_widget

        # Compact top controls with reduced height
        top_controls_frame = tk.Frame(main_frame, bg="#2e2e2e", height=60)
        top_controls_frame.pack(fill=tk.X, pady=(0, 8))
        top_controls_frame.pack_propagate(False)

        # Left side controls (more compact)
        left_controls = tk.Frame(top_controls_frame, bg="#2e2e2e")
        left_controls.pack(side=tk.LEFT, fill=tk.Y)

        # Buttons in a more compact layout
        buttons_frame = tk.Frame(left_controls, bg="#2e2e2e")
        buttons_frame.pack(side=tk.LEFT, anchor=tk.W, pady=2)

        font_size_frame = tk.Frame(left_controls, bg="#2e2e2e")
        font_size_frame.pack(side=tk.LEFT, anchor=tk.W, padx=(12, 0), pady=2)

        # Right side - Apply button and target mode
        right_controls = tk.Frame(top_controls_frame, bg="#2e2e2e")  
        right_controls.pack(side=tk.RIGHT, fill=tk.Y)

        apply_frame = tk.Frame(right_controls, bg="#2e2e2e")
        apply_frame.pack(side=tk.RIGHT, anchor=tk.E, pady=2)
        
        # Bind drag functionality to additional frames
        for widget in [main_frame, top_controls_frame, left_controls, buttons_frame, font_size_frame, right_controls, apply_frame]:
            self._bind_drag_to_widget(widget)

        # Flat design button style with muted colors
        button_style = {
            "font": ("IBM Plex Sans Thai Medium", 9),
            "bd": 0,
            "padx": 8,
            "pady": 6,
            "cursor": "hand2",
            "width": 9,
            "relief": "flat"
        }

        button_row = tk.Frame(buttons_frame, bg="#2e2e2e")
        button_row.pack(side=tk.LEFT)

        add_button = tk.Button(
            button_row,
            text="เพิ่มฟอนต์",
            bg="#5a5a5a",  # Muted grey instead of bright blue
            fg="#e0e0e0",
            **button_style,
            command=self.add_font,
        )
        add_button.pack(side=tk.LEFT, padx=1)

        # Remove font button removed per user request

        font_size_label = tk.Label(
            font_size_frame,
            text="ขนาด:",
            font=("IBM Plex Sans Thai Medium", 9),
            bg="#2e2e2e",
            fg="#e0e0e0",
        )
        font_size_label.pack(side=tk.LEFT, padx=(0, 5))

        decrease_button = tk.Button(
            font_size_frame,
            text="-",
            font=("IBM Plex Sans Thai Medium", 11),
            bg="#4a4a4a",  # Darker muted grey
            fg="#e0e0e0",
            width=2,
            bd=0,
            cursor="hand2",
            relief="flat",
            command=lambda: self.adjust_font_size(-1),
        )
        decrease_button.pack(side=tk.LEFT, padx=1)

        font_size_value_label = tk.Label(
            font_size_frame,
            textvariable=self.font_size,
            width=3,
            font=("IBM Plex Sans Thai Medium", 10),
            bg="#2e2e2e",
            fg="#c4a777",  # Muted gold color
        )
        font_size_value_label.pack(side=tk.LEFT, padx=4)

        increase_button = tk.Button(
            font_size_frame,
            text="+",
            font=("IBM Plex Sans Thai Medium", 11),
            bg="#4a4a4a",  # Darker muted grey
            fg="#e0e0e0",
            width=2,
            bd=0,
            cursor="hand2",
            relief="flat",
            command=lambda: self.adjust_font_size(1),
        )
        increase_button.pack(side=tk.LEFT, padx=2)

        for btn in [decrease_button, increase_button]:

            def create_size_hover_handlers(button):
                def on_enter(e):
                    button.config(bg="#5a5a5a", highlightbackground="#5a5a5a", highlightthickness=0)  # Muted hover

                def on_leave(e):
                    button.config(bg="#4a4a4a", highlightbackground="#4a4a4a", highlightthickness=0)  # Original muted

                return on_enter, on_leave

            enter_h, leave_h = create_size_hover_handlers(btn)
            btn.bind("<Enter>", enter_h)
            btn.bind("<Leave>", leave_h)

        apply_button = tk.Button(
            apply_frame,
            text="Apply",
            bg="#c4a777",  # Muted gold
            fg="#2e2e2e",  # Dark text for better contrast
            font=("IBM Plex Sans Thai Medium", 9, "bold"),
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            relief="flat",
            command=self.apply_font,
        )
        apply_button.pack(side=tk.RIGHT, padx=2)

        # === Target Selection Section (Enhanced and Prominent) ===
        target_section = tk.Frame(main_frame, bg="#1a1a1a", relief="solid", bd=1)
        target_section.pack(fill=tk.X, pady=(4, 10), padx=4)
        
        # Header for target selection with better styling
        target_header_frame = tk.Frame(target_section, bg="#1a1a1a")
        target_header_frame.pack(fill=tk.X, padx=6, pady=(6, 2))
        
        target_header = tk.Label(
            target_header_frame, 
            text="🎯 เลือกปลายทางสำหรับการ Apply ฟอนต์", 
            font=("IBM Plex Sans Thai Medium", 11, "bold"),
            bg="#1a1a1a", fg="#f0f0f0", 
            anchor=tk.W
        )
        target_header.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Separator line
        separator = tk.Frame(target_section, bg="#4a4a4a", height=1)
        separator.pack(fill=tk.X, padx=8, pady=(2, 8))
        
        # Create target options in enhanced horizontal layout
        options_frame = tk.Frame(target_section, bg="#1a1a1a")
        options_frame.pack(fill=tk.X, padx=16, pady=(0, 12))
        
        # Main UI option with enhanced design and full clickable area
        ui_option_frame = tk.Frame(options_frame, bg="#2a3a2a", relief="solid", bd=1, cursor="hand2")
        ui_option_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8), pady=2)
        
        ui_icon_label = tk.Label(
            ui_option_frame,
            text="🖥️",
            font=("Segoe UI Emoji", 14),
            bg="#2a3a2a", fg="#e0e0e0",
            cursor="hand2"
        )
        ui_icon_label.pack(anchor=tk.W, padx=(8, 4), pady=(8, 2))
        
        self.translated_ui_rb = tk.Radiobutton(
            ui_option_frame,
            text="หน้าต่างแปลหลัก (TUI)",
            variable=self.target_mode,
            value="translated_ui",
            font=("IBM Plex Sans Thai Medium", 9),
            bg="#2a3a2a", fg="#e0e0e0",
            selectcolor="#000000",  # Black indicator when not selected
            activebackground="#3a5a3a",
            activeforeground="#ffffff",
            anchor=tk.W,
            cursor="hand2",
            command=self._update_target_colors
        )
        self.translated_ui_rb.pack(anchor=tk.W, padx=(8, 8), pady=(0, 8))
        
        # Make frame clickable
        def ui_frame_click(event):
            self.target_mode.set("translated_ui")
            self._update_target_colors()
        ui_option_frame.bind("<Button-1>", ui_frame_click)
        ui_icon_label.bind("<Button-1>", ui_frame_click)
        
        # Logs option with enhanced design and full clickable area
        logs_option_frame = tk.Frame(options_frame, bg="#3a2a2a", relief="solid", bd=1, cursor="hand2")
        logs_option_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=0, pady=2)
        
        logs_icon_label = tk.Label(
            logs_option_frame,
            text="📄",
            font=("Segoe UI Emoji", 14),
            bg="#3a2a2a", fg="#e0e0e0",
            cursor="hand2"
        )
        logs_icon_label.pack(anchor=tk.W, padx=(8, 4), pady=(8, 2))
        
        self.translated_logs_rb = tk.Radiobutton(
            logs_option_frame,
            text="หน้าต่างประวัติการแปล (LOG)",
            variable=self.target_mode,
            value="translated_logs",
            font=("IBM Plex Sans Thai Medium", 9),
            bg="#3a2a2a", fg="#e0e0e0",
            selectcolor="#000000",  # Black indicator when not selected
            activebackground="#5a3a3a",
            activeforeground="#ffffff",
            anchor=tk.W,
            cursor="hand2",
            command=self._update_target_colors
        )
        self.translated_logs_rb.pack(anchor=tk.W, padx=(8, 8), pady=(0, 8))
        
        # Make frame clickable
        def logs_frame_click(event):
            self.target_mode.set("translated_logs")
            self._update_target_colors()
        logs_option_frame.bind("<Button-1>", logs_frame_click)
        logs_icon_label.bind("<Button-1>", logs_frame_click)
        
        # เก็บ reference ของ frame สำหรับการจัดการสี
        self.ui_option_frame = ui_option_frame
        self.logs_option_frame = logs_option_frame
        
        # ตั้งค่า default selection
        self._update_target_colors()

        def on_font_size_change(*args):
            font_name = self.selected_font.get() or "IBM Plex Sans Thai Medium"
            self.update_font_preview(font_name)

        self.font_size.trace_add("write", on_font_size_change)

        for button, hover_color, normal_color in [
            (add_button, "#6a6a6a", "#5a5a5a"),  # Muted grey hover
            (apply_button, "#d4b787", "#c4a777"),  # Muted gold hover
            (close_button, "#d32f2f", "#2e2e2e"),  # Keep red for close
        ]:

            def create_hover_handlers(btn, hover_c, normal_c):
                def on_enter(e):
                    btn.config(highlightbackground=hover_c, highlightthickness=1)

                def on_leave(e):
                    btn.config(highlightbackground=normal_c, highlightthickness=0)

                return on_enter, on_leave

            enter_handler, leave_handler = create_hover_handlers(
                button, hover_color, normal_color
            )
            button.bind("<Enter>", enter_handler)
            button.bind("<Leave>", leave_handler)

        # More subtle current font display
        current_font_frame = tk.Frame(main_frame, bg="#323232", height=24)
        current_font_frame.pack(fill=tk.X, pady=(0, 6))
        current_font_frame.pack_propagate(False)

        current_font_name = (
            self.settings.get("font", "IBM Plex Sans Thai Medium")
            if self.settings
            else "IBM Plex Sans Thai Medium"
        )
        current_font_size = self.settings.get("font_size", 16) if self.settings else 16

        self.current_font_label = tk.Label(
            current_font_frame,
            text=f"ฟอนต์: {current_font_name} • {current_font_size}px",
            font=("IBM Plex Sans Thai Medium", 9),
            bg="#323232",
            fg="#c4a777",  # Muted gold
            justify=tk.CENTER,
        )
        self.current_font_label.pack(fill=tk.BOTH, expand=True)
        self.current_font_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Flat design notebook without borders
        self.style.configure(
            "TNotebook", 
            background="#2e2e2e", 
            borderwidth=0, 
            relief="flat",
            tabmargins=[0, 0, 0, 0]
        )
        self.style.configure(
            "TNotebook.Tab",
            background="#3a3a3a",
            foreground="#8a8a8a",
            borderwidth=0,
            relief="flat",
            padding=[16, 8],  # Reduced padding for more compact tabs
            focuscolor="none",
            font=("IBM Plex Sans Thai Medium", 9)
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", "#4a4a4a"), ("active", "#454545")],  # Subtle selected state
            foreground=[("selected", "#c4a777"), ("active", "#b09660")],  # Muted gold when selected
            borderwidth=[("selected", 0)],
            relief=[("selected", "flat")],
        )

        # Create notebook with flat design
        self.notebook = ttk.Notebook(main_frame, style="TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=0, padx=0)

        fonts_tab = tk.Frame(self.notebook, bg="#3a3a3a", bd=0, relief="flat")
        self.notebook.add(fonts_tab, text="จัดการฟอนต์")

        details_tab = tk.Frame(self.notebook, bg="#3a3a3a", bd=0, relief="flat")
        self.notebook.add(details_tab, text="รายละเอียดฟอนต์")

        self.notebook.select(0)
        self.notebook.update_idletasks()
        self.notebook.update()

        # Main content area with more space for font list
        fonts_frame = tk.Frame(fonts_tab, bg="#3a3a3a", bd=0, relief="flat")
        fonts_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Resizable font list frame
        self.list_width = 350  # Default width
        list_frame = tk.Frame(fonts_frame, bg="#3a3a3a", width=self.list_width, bd=0, relief="flat")
        list_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False)
        list_frame.pack_propagate(False)

        list_label = tk.Label(
            list_frame,
            text="รายการฟอนต์",
            font=("IBM Plex Sans Thai Medium", 9),
            bg="#3a3a3a",
            fg="#c0c0c0",
        )
        list_label.pack(pady=(2, 3))

        listbox_frame = tk.Frame(list_frame, bg="#3a3a3a", bd=0, relief="flat")
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)

        # Minimalistic scrollbar
        self.style.configure(
            "Vertical.TScrollbar",
            background="#3a3a3a",  # Same as background
            troughcolor="#3a3a3a",
            bordercolor="#3a3a3a",
            arrowcolor="#6a6a6a",
            darkcolor="#3a3a3a",
            lightcolor="#3a3a3a",
            borderwidth=0,
            relief=tk.FLAT,
            width=8,  # Thinner scrollbar
        )
        scrollbar = ttk.Scrollbar(
            listbox_frame, orient=tk.VERTICAL, style="Vertical.TScrollbar"
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(2, 0))

        fonts_listbox = tk.Listbox(
            listbox_frame,
            bg="#424242",  # Slightly lighter than background
            fg="#e0e0e0",
            font=("IBM Plex Sans Thai Medium", 9),
            selectbackground="#c4a777",  # Muted gold selection
            selectforeground="#2e2e2e",  # Dark text on gold
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
            width=25,  # Wider to show more text
            yscrollcommand=scrollbar.set,
        )
        fonts_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=fonts_listbox.yview)
        self.font_listbox = fonts_listbox

        available_fonts = self.font_manager.get_available_fonts()
        for font in available_fonts:
            fonts_listbox.insert(tk.END, font)

        # Resize handle between list and preview (hidden but functional)
        resize_handle = tk.Frame(fonts_frame, bg="#3a3a3a", width=4, cursor="sb_h_double_arrow")
        resize_handle.pack(side=tk.LEFT, fill=tk.Y, padx=1)
        
        # Store references for resizing
        self.list_frame = list_frame
        self.resize_handle = resize_handle
        self.fonts_frame = fonts_frame
        
        # Bind resize events
        resize_handle.bind("<Button-1>", self._start_resize_panels)
        resize_handle.bind("<B1-Motion>", self._on_resize_panels)
        resize_handle.bind("<ButtonRelease-1>", self._end_resize_panels)

        # Compact preview frame
        preview_frame = tk.Frame(fonts_frame, bg="#3a3a3a", bd=0, relief="flat")
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))
        preview_frame.pack_propagate(False)

        preview_label = tk.Label(
            preview_frame,
            text="ตัวอย่างฟอนต์",
            font=("IBM Plex Sans Thai Medium", 9),
            bg="#3a3a3a",
            fg="#e0e0e0",
        )
        preview_label.pack(pady=(5, 2))

        self.preview_canvas = tk.Canvas(
            preview_frame,
            bg="#4a4a4a",
            highlightthickness=0,
            bd=0,
            relief=tk.FLAT,
            height=220,
        )
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self._create_initial_canvas_background()
        self.preview_canvas.update_idletasks()
        self.preview_canvas.update()

        def on_canvas_configure(event):
            if event.widget == self.preview_canvas:
                items = self.preview_canvas.find_all()
                if not items:
                    self._create_initial_canvas_background()

        self.preview_canvas.bind("<Configure>", on_canvas_configure)

        def on_font_select(event):
            try:
                selected_idx = fonts_listbox.curselection()
                if selected_idx:
                    selected_font = fonts_listbox.get(selected_idx[0])
                    self.selected_font.set(selected_font)
                    self.update_font_preview(selected_font)
                    if hasattr(self, "preview_canvas") and self.preview_canvas:
                        self.preview_canvas.update()
            except Exception as e:
                logging.warning(f"เกิดข้อผิดพลาดในการเลือกฟอนต์: {e}")

        fonts_listbox.bind("<<ListboxSelect>>", on_font_select)

        def on_notebook_focus(event):
            current_tab = self.notebook.index(self.notebook.select())
            self.notebook.focus_set()

        def on_lose_focus(event):
            pass

        def on_tab_changed(event):
            # ทำให้ Frame ภายใน Tab มีสีพื้นหลังตรงกับ Tab ที่เลือก
            selected_tab_index = self.notebook.index(self.notebook.select())
            for i, tab_frame in enumerate([fonts_tab, details_tab]):
                if i == selected_tab_index:
                    tab_frame.configure(bg="#3a3a3a")
                else:
                    tab_frame.configure(bg="#2e2e2e")  # สีของ Tab ที่ไม่ถูกเลือก

            try:
                current_tab = self.notebook.index(self.notebook.select())
                if current_tab == 0:
                    if hasattr(self, "preview_canvas") and self.preview_canvas:
                        items = self.preview_canvas.find_all()
                        if not items:
                            self._create_initial_canvas_background()
                            current_font = (
                                self.selected_font.get()
                                or self.settings.get(
                                    "font", "IBM Plex Sans Thai Medium"
                                )
                                if self.settings
                                else "IBM Plex Sans Thai Medium"
                            )
                            self.update_font_preview(current_font)
                    if hasattr(self, "font_listbox") and self.font_listbox:
                        self.font_window.after(10, self._force_update_fonts_tab)
                elif current_tab == 1:
                    if hasattr(self, "validation_status"):
                        self.font_window.after(10, self._force_update_details_tab)
            except Exception as e:
                logging.warning(f"เกิดข้อผิดพลาดในการเปลี่ยนแท็บ: {e}")

        self.notebook.bind("<Button-1>", on_notebook_focus)
        self.notebook.bind("<<NotebookTabChanged>>", on_tab_changed)
        main_frame.bind("<Button-1>", on_lose_focus)

        self.create_validation_panel(details_tab)
        self.font_window.after(1, lambda: self._ensure_canvas_background())

        # Hidden resize functionality - completely invisible
        try:
            # Create completely invisible resize area in bottom-right corner
            resize_area = tk.Frame(
                main_frame,
                bg="#2e2e2e",  # Match background exactly
                cursor="bottom_right_corner",
                width=15,
                height=15,
                bd=0,
                relief="flat",
                highlightthickness=0
            )
            resize_area.place(relx=1.0, rely=1.0, anchor="se", x=-2, y=-2)
            resize_area.bind("<Button-1>", lambda e: self._start_resize(e))
            resize_area.bind("<B1-Motion>", self._do_resize)

            logging.info("Invisible resize area created successfully")

        except Exception as e:
            logging.error(f"Error creating resize area: {e}")
            # Skip fallback to avoid any visible elements

    def adjust_font_size(self, increment):
        """ปรับขนาดฟอนต์ขึ้นหรือลง"""
        current_size = self.font_size.get()
        new_size = current_size + increment

        # จำกัดขนาดฟอนต์ระหว่าง 8-48
        if 8 <= new_size <= 48:
            self.font_size.set(new_size)
            # อัปเดต preview
            font_name = self.selected_font.get() or "IBM Plex Sans Thai Medium"
            self.update_font_preview(font_name)

    def _update_target_colors(self):
        """อัปเดตสีของ radiobuttons ตามการเลือก"""
        try:
            if not hasattr(self, "translated_ui_rb") or not hasattr(
                self, "translated_logs_rb"
            ):
                return
            if (
                not self.translated_ui_rb.winfo_exists()
                or not self.translated_logs_rb.winfo_exists()
            ):
                return

            selected = self.target_mode.get()

            # Enhanced colors for better visibility
            active_color = "#c4a777"     # Muted gold for selected
            active_select_color = "#c4a777"  # Muted gold indicator
            active_bg = "#4a5a4a"        # Slightly lighter background
            active_frame_bg = "#4a5a4a"   # Frame background for selected

            # สีสำหรับตัวที่ไม่เลือก (สีดำตามที่ต้องการ)
            inactive_color = "#505050"   # Dark grey text
            inactive_select_color = "#000000"  # Black indicator
            inactive_bg = "#1a1a1a"      # Dark background
            inactive_frame_bg = "#1a1a1a"  # Dark frame background for unselected

            if selected == "translated_ui":
                # อัปเดตปุ่ม "หน้าจอแปลหลัก" ให้เป็น Active
                self.translated_ui_rb.config(
                    fg=active_color, selectcolor=active_select_color, bg=active_bg
                )
                if hasattr(self, 'ui_option_frame'):
                    self.ui_option_frame.config(bg=active_frame_bg)
                
                # อัปเดตปุ่ม "ประวัติบทสนทนา" ให้เป็น Inactive
                self.translated_logs_rb.config(
                    fg=inactive_color, selectcolor=inactive_select_color, bg=inactive_bg
                )
                if hasattr(self, 'logs_option_frame'):
                    self.logs_option_frame.config(bg=inactive_frame_bg)
            else:
                # อัปเดตปุ่ม "หน้าจอแปลหลัก" ให้เป็น Inactive
                self.translated_ui_rb.config(
                    fg=inactive_color, selectcolor=inactive_select_color, bg=inactive_bg
                )
                if hasattr(self, 'ui_option_frame'):
                    self.ui_option_frame.config(bg=inactive_frame_bg)
                
                # อัปเดตปุ่ม "ประวัติบทสนทนา" ให้เป็น Active
                self.translated_logs_rb.config(
                    fg=active_color, selectcolor=active_select_color, bg=active_bg
                )
                if hasattr(self, 'logs_option_frame'):
                    self.logs_option_frame.config(bg=active_frame_bg)

        except Exception as e:
            logging.error(f"Error updating target colors: {e}")

    def _safe_update_target_colors(self):
        """ปลอดภัยอัปเดตสีของ radiobuttons - กันไม่ให้กระทบ UI อื่น"""
        try:
            if (
                not hasattr(self, "font_window")
                or not self.font_window
                or not self.font_window.winfo_exists()
            ):
                return
            if not hasattr(self, "target_mode"):
                return
            self._update_target_colors()
        except Exception as e:
            logging.warning(f"Could not update target colors (non-critical): {e}")

    def apply_font(self) -> None:
        """ใช้ฟอนต์ที่เลือก"""
        selected_font = self.selected_font.get()
        selected_size = self.font_size.get()

        if not selected_font:
            return

        try:
            # ไม่ใช้ font_settings.apply_font เพราะจะแจ้ง observers ทั้งหมด
            # แต่จะจัดการผ่าน callback แทน
            
            # อัพเดต settings โดยตรง
            if self.settings:
                self.settings.set("font", selected_font)
                self.settings.set("font_size", selected_size)
            
            # อัพเดต UI
            if hasattr(self, "current_font_label"):
                self.current_font_label.config(
                    text=f"ฟอนต์ปัจจุบัน: {selected_font} • ขนาด: {selected_size}px"
                )

            self.show_temporary_notification(
                f"✅ เปลี่ยนฟอนต์เป็น '{selected_font}' ขนาด {selected_size}px เรียบร้อยแล้ว",
                color="#4CAF50",
                duration=3000,
            )

            # เรียก callback พร้อมส่ง target ที่ถูกต้อง
            if self.apply_callback:
                target_value = self.target_mode.get()
                self.apply_callback(
                    {
                        "font": selected_font,
                        "font_size": selected_size,
                        "target": target_value,  # ส่ง target จาก UI
                    }
                )
                
                # เพิ่ม callback สถานะปุ่มไปที่ settings
                if self.settings and target_value:
                    self.settings.set("font_target_mode", target_value)
                    logging.info(f"บันทึกสถานะ target mode: {target_value}")

        except Exception as e:
            logging.error(f"เกิดข้อผิดพลาดในการเปลี่ยนฟอนต์: {e}")
            self.show_temporary_notification(f"❌ เกิดข้อผิดพลาด: {e}", color="#d32f2f")

    def update_font_size_preview(self, value=None) -> None:
        """อัพเดตขนาดฟอนต์ในตัวอย่าง"""
        try:
            # ตรวจสอบว่า preview_canvas มีอยู่จริง
            if not hasattr(self, "preview_canvas") or not self.preview_canvas:
                return

            # ล้าง canvas ยกเว้น background
            self.preview_canvas.delete("all")

            # สร้างพื้นหลังใหม่
            self.preview_canvas.create_rectangle(
                0, 0, 1000, 1000, fill="#4a4a4a", outline="#4a4a4a", tags="background"
            )

            font_name = self.selected_font.get() or "IBM Plex Sans Thai Medium"
            font_size = self.font_size.get()

            # ลดความยาวตัวอย่างข้อความให้สั้นลง
            sample_text = "ทดสอบภาษาไทย Aa Bb 123"

            # แสดงตัวอย่างฟอนต์ด้วยขนาดที่เลือก
            self.preview_canvas.create_text(
                10,
                10,
                text=sample_text,
                font=(font_name, font_size),
                anchor=tk.NW,
                fill="#e0e0e0",
            )

            # แสดงขนาดฟอนต์ต่างๆ แต่ลดจำนวนตัวอย่าง
            y_pos = 50 + font_size
            medium_size = font_size

            # แสดงแค่ขนาดปัจจุบัน
            self.preview_canvas.create_text(
                10,
                y_pos,
                text=f"ขนาด: {medium_size}px",
                font=(font_name, max(medium_size - 4, 10)),  # ขนาดเล็กกว่าเล็กน้อย
                anchor=tk.NW,
                fill="#b0b0b0",
            )

            # force update canvas
            self.preview_canvas.update_idletasks()
            self.preview_canvas.update()

        except Exception as e:
            # หากเกิดข้อผิดพลาด ให้สร้างพื้นหลังและข้อความ error
            try:
                if hasattr(self, "preview_canvas") and self.preview_canvas:
                    self.preview_canvas.delete("all")
                    self.preview_canvas.create_rectangle(
                        0, 0, 1000, 1000, fill="#4a4a4a", outline="#4a4a4a"
                    )
                    self.preview_canvas.create_text(
                        10,
                        20,
                        text=f"ไม่สามารถแสดงตัวอย่างฟอนต์ได้",
                        font=("Arial", 12),
                        anchor=tk.NW,
                        fill="#ff6666",
                    )
                    self.preview_canvas.update()
            except:
                pass
            logging.error(f"ไม่สามารถอัพเดตตัวอย่างขนาดฟอนต์: {e}")

    def create_notification_area(self) -> None:
        """สร้างพื้นที่สำหรับแสดงข้อความแจ้งเตือน"""
        notification_frame = tk.Frame(self.font_window, bg="#2e2e2e", height=20)
        notification_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(0, 2))
        notification_frame.pack_propagate(False)

        self.notification_label = tk.Label(
            notification_frame,
            text="",
            font=("IBM Plex Sans Thai Medium", 8),
            bg="#2e2e2e",
            fg="#4CAF50",
            wraplength=380,
        )
        self.notification_label.pack(fill=tk.BOTH, expand=True)

    def show_temporary_notification(
        self, message, color="#4CAF50", duration=2000
    ) -> None:
        """แสดงข้อความแจ้งเตือนชั่วคราว"""
        if self.notification_label:
            if hasattr(self, "notification_timer") and self.notification_timer:
                self.notification_label.after_cancel(self.notification_timer)
                self.notification_timer = None

            # สร้างเอฟเฟกต์เล็กน้อยก่อนแสดงข้อความใหม่
            current_bg = self.notification_label.cget("bg")
            self.notification_label.config(bg="#4a4a4a")

            # ย้อนกลับพื้นหลังหลังจาก 100ms
            self.notification_label.after(
                100, lambda: self.notification_label.config(bg="#2e2e2e")
            )

            # แสดงข้อความใหม่
            self.notification_label.config(text=message, fg=color)

            # ตั้ง timer ให้ข้อความหายไป
            self.notification_timer = self.notification_label.after(
                duration, lambda: self.notification_label.config(text="")
            )

            logging.info(f"Notification: {message}")

    def update_font_preview(self, font_name: str) -> None:
        """อัพเดตตัวอย่างฟอนต์"""
        try:
            # ตรวจสอบว่า preview_canvas มีอยู่จริง
            if not hasattr(self, "preview_canvas") or not self.preview_canvas:
                return

            self.selected_font.set(font_name)

            # อัปเดตการแสดงผลตัวอย่าง
            self.update_font_size_preview()

            # นำไปใช้งานจริงแบบ real-time เมื่อเลือกฟอนต์
            self.font_settings.apply_font(font_name, self.font_size.get())

            # force update canvas
            if hasattr(self, "preview_canvas") and self.preview_canvas:
                self.preview_canvas.update_idletasks()
                self.preview_canvas.update()

        except Exception as e:
            # แสดงข้อความแจ้งเตือนในกรณีที่ไม่สามารถแสดงตัวอย่างฟอนต์ได้
            try:
                if hasattr(self, "preview_canvas") and self.preview_canvas:
                    self.preview_canvas.delete("all")
                    # สร้างพื้นหลัง
                    self.preview_canvas.create_rectangle(
                        0,
                        0,
                        1000,
                        1000,
                        fill="#4a4a4a",
                        outline="#4a4a4a",
                        tags="background",
                    )
                    self.preview_canvas.create_text(
                        10,
                        20,
                        text=f"ไม่สามารถแสดงตัวอย่างฟอนต์ {font_name} ได้",
                        font=("Arial", 12),
                        anchor=tk.NW,
                        fill="#ff6666",
                    )
                    self.preview_canvas.update()
            except:
                pass
            logging.error(f"ไม่สามารถแสดงตัวอย่างฟอนต์ {font_name}: {e}")

    def close_font_ui(self) -> None:
        """ปิดหน้าต่างจัดการฟอนต์"""
        if self.font_window:
            self.font_window.destroy()
            self.font_window = None

    def add_font(self) -> None:
        """เปิดหน้าต่างเลือกไฟล์ฟอนต์"""
        try:
            file_path = filedialog.askopenfilename(
                title="เลือกไฟล์ฟอนต์",
                filetypes=[("Font Files", "*.ttf *.otf")],
            )

            if not file_path:
                return

            success = self.font_manager.add_font(file_path)
            if success:
                self.show_temporary_notification(
                    f"เพิ่มฟอนต์ {os.path.basename(file_path)} เรียบร้อยแล้ว"
                )
                self.refresh_font_list()
            else:
                self.show_temporary_notification(
                    "ไม่สามารถเพิ่มฟอนต์ได้ โปรดตรวจสอบว่าไฟล์ถูกต้องหรือไม่", color="#d32f2f"
                )

        except Exception as e:
            logging.error(f"เกิดข้อผิดพลาดในการเพิ่มฟอนต์: {e}")
            self.show_temporary_notification(f"เกิดข้อผิดพลาด: {e}", color="#d32f2f")

    # Remove font functionality removed per user request

    def refresh_font_list(self, listbox=None) -> None:
        """รีเฟรชรายการฟอนต์"""
        self.font_manager.load_and_register_fonts()

        if listbox is None:
            listbox = self.font_listbox

        if listbox:
            listbox.delete(0, tk.END)

            available_fonts = self.font_manager.get_available_fonts()
            for font in available_fonts:
                listbox.insert(tk.END, font)

            current_font = (
                self.settings.get("font", "IBM Plex Sans Thai Medium")
                if self.settings
                else "IBM Plex Sans Thai Medium"
            )
            if current_font in available_fonts:
                idx = available_fonts.index(current_font)
                listbox.selection_set(idx)
                listbox.see(idx)

    def create_validation_panel(self, parent_frame):
        """สร้าง UI สำหรับตรวจสอบการแสดงผลฟอนต์"""
        main_frame = tk.Frame(parent_frame, bg="#2e2e2e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # คำอธิบาย
        explanation = tk.Label(
            main_frame,
            text="ระบบตรวจสอบฟอนต์จะช่วยคุณยืนยันว่าฟอนต์ที่เลือกสามารถแสดงผลได้ถูกต้อง\nแสดงข้อมูลจริงของฟอนต์ และตรวจสอบว่ารองรับภาษาไทยหรือไม่",
            font=("IBM Plex Sans Thai Medium", 10),
            bg="#2e2e2e",
            fg="#e0e0e0",
            justify=tk.LEFT,
            wraplength=800,
        )
        explanation.pack(pady=(0, 10), anchor=tk.W)

        # กรอบแสดงผลการตรวจสอบ
        result_frame = tk.Frame(main_frame, bg="#3a3a3a")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # สร้างแนวนอนแบ่งเป็น 2 ส่วน
        horizontal_frame = tk.Frame(result_frame, bg="#3a3a3a")
        horizontal_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ฝั่งซ้าย: แสดงตัวอย่างข้อความและสถานะการรองรับภาษาไทย
        left_panel = tk.Frame(horizontal_frame, bg="#3a3a3a", width=600)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        left_panel.pack_propagate(False)

        # ฝั่งขวา: แสดงข้อมูล metadata
        right_panel = tk.Frame(horizontal_frame, bg="#3a3a3a", width=600)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        right_panel.pack_propagate(False)

        # สร้างปุ่มตรวจสอบฟอนต์และย้ายไปชิดขวา
        validate_btn_frame = tk.Frame(result_frame, bg="#3a3a3a")
        validate_btn_frame.pack(fill=tk.X, pady=(0, 5))

        validate_btn = tk.Button(
            validate_btn_frame,
            text="ตรวจสอบฟอนต์ที่เลือก",
            font=("IBM Plex Sans Thai Medium", 10),
            bg="#3a71c7",
            fg="#e0e0e0",
            padx=10,
            pady=5,
            bd=0,
            cursor="hand2",
            command=self.validate_selected_font,
        )
        validate_btn.pack(side=tk.RIGHT, padx=10, pady=5)

        # เพิ่ม hover effect ให้ปุ่ม แบบแสดงขอบบางๆ
        def validate_hover_enter(e):
            validate_btn.config(highlightbackground="#2980b9", highlightthickness=1)

        def validate_hover_leave(e):
            validate_btn.config(highlightbackground="#3a71c7", highlightthickness=0)

        validate_btn.bind("<Enter>", validate_hover_enter)
        validate_btn.bind("<Leave>", validate_hover_leave)

        # ===== ส่วนซ้าย: ตัวอย่างข้อความและสถานะการรองรับภาษาไทย =====

        # สถานะการตรวจสอบ
        self.validation_status = tk.Label(
            left_panel,
            text="เลือกฟอนต์และกดปุ่มตรวจสอบ",
            font=("IBM Plex Sans Thai Medium", 12),
            bg="#3a3a3a",
            fg="#cccccc",
        )
        self.validation_status.pack(anchor=tk.W, pady=(20, 10))

        # พื้นที่แสดงตัวอย่างข้อความพิเศษ - ลบ bd และ highlightthickness
        test_frame = tk.Frame(left_panel, bg="#4a4a4a", padx=20, pady=20)
        test_frame.pack(fill=tk.X, pady=10)

        self.validation_sample = tk.Label(
            test_frame,
            text="การทดสอบฟอนต์ไทย ABCdef 123 !@#$",
            font=("Arial", 14),
            bg="#4a4a4a",
            fg="#e0e0e0",
            wraplength=500,
            justify=tk.LEFT,
        )
        self.validation_sample.pack(anchor=tk.W)

        # Thai support indicator ย้ายไปไว้ด้านล่าง
        self.thai_support_frame = tk.Frame(left_panel, bg="#3a3a3a", padx=5, pady=5)
        self.thai_support_frame.pack(fill=tk.X, pady=(10, 0), side=tk.BOTTOM)

        self.thai_support_indicator = tk.Label(
            self.thai_support_frame,
            text="รองรับภาษาไทย: ไม่ทราบสถานะ",
            font=("IBM Plex Sans Thai Medium", 10),
            bg="#3a3a3a",
            fg="#cccccc",
        )
        self.thai_support_indicator.pack(side=tk.LEFT)

        # ===== ส่วนขวา: ข้อมูล metadata =====

        # พื้นที่แสดงข้อมูล metadata - ปรับ LabelFrame style ให้ไม่มีขอบ
        self.style.configure(
            "TLabelframe",
            background="#3a3a3a",
            foreground="#e0e0e0",
            bordercolor="#3a3a3a",
            darkcolor="#3a3a3a",
            lightcolor="#3a3a3a",
            relief="flat",
            borderwidth=0,
        )

        self.style.configure(
            "TLabelframe.Label",
            background="#3a3a3a",
            foreground="#e0e0e0",
            font=("IBM Plex Sans Thai Medium", 10),
        )

        metadata_frame = ttk.LabelFrame(
            right_panel, text="ข้อมูลฟอนต์", style="TLabelframe", padding=10
        )
        metadata_frame.pack(fill=tk.BOTH, expand=True, pady=20)

        # สร้าง grid สำหรับข้อมูลต่างๆ
        self.metadata_labels = {}
        metadata_fields = [
            ("file_name", "ชื่อไฟล์:"),
            ("family_name", "ชื่อตระกูลฟอนต์:"),
            ("subfamily", "สไตล์:"),
            ("full_name", "ชื่อเต็ม:"),
            ("postscript_name", "ชื่อ PostScript:"),
            ("supported_scripts", "รองรับภาษา:"),
        ]

        for i, (field_id, label_text) in enumerate(metadata_fields):
            label = tk.Label(
                metadata_frame,
                text=label_text,
                font=("IBM Plex Sans Thai Medium", 10),
                bg="#3a3a3a",
                fg="#cccccc",
                anchor=tk.W,
            )
            label.grid(row=i, column=0, sticky=tk.W, pady=2)

            value_label = tk.Label(
                metadata_frame,
                text="-",
                font=("IBM Plex Sans Thai Medium", 10),
                bg="#3a3a3a",
                fg="#e0e0e0",
                anchor=tk.W,
                wraplength=350,
            )
            value_label.grid(row=i, column=1, sticky=tk.W, padx=10, pady=2)

            self.metadata_labels[field_id] = value_label

        # เพิ่ม resizable columns
        metadata_frame.columnconfigure(1, weight=1)

        # Open sample image button อยู่ด้านขวาล่าง
        self.open_sample_btn = tk.Button(
            right_panel,
            text="เปิดภาพตัวอย่าง",
            font=("IBM Plex Sans Thai Medium", 9),
            bg="#5a5a5a",
            fg="#e0e0e0",
            padx=8,
            pady=3,
            bd=0,
            cursor="hand2",
            state=tk.DISABLED,
            command=self.open_sample_image,
        )
        self.open_sample_btn.pack(side=tk.BOTTOM, anchor=tk.SE, pady=(0, 10))

        # เก็บ path ของภาพตัวอย่าง
        self.sample_image_path = None

    def open_sample_image(self):
        """เปิดภาพตัวอย่างฟอนต์ในหน้าต่างเล็กๆ"""
        if self.sample_image_path and os.path.exists(self.sample_image_path):
            try:
                # สร้างหน้าต่างแสดงภาพตัวอย่าง
                sample_window = tk.Toplevel(self.font_window)
                sample_window.title("ตัวอย่างฟอนต์")
                sample_window.geometry("500x350")
                sample_window.minsize(400, 300)
                sample_window.resizable(True, True)
                sample_window.configure(bg="#2e2e2e")

                # โหลดภาพด้วย PIL
                from PIL import Image, ImageTk

                # โหลดภาพต้นฉบับและปรับขนาด
                image = Image.open(self.sample_image_path)
                self.original_image = image
                image_copy = image.copy()

                # ปรับขนาดภาพให้พอดีกับหน้าต่าง โดยคงอัตราส่วน
                image_copy.thumbnail((480, 320), Image.LANCZOS)

                # แปลงเป็น ImageTk
                photo_image = ImageTk.PhotoImage(image_copy)

                # สร้าง canvas สำหรับแสดงภาพ
                canvas = tk.Canvas(
                    sample_window, bg="#2e2e2e", bd=0, highlightthickness=0
                )
                canvas.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

                # แสดงภาพตรงกลาง canvas
                canvas_image = canvas.create_image(
                    0, 0, image=photo_image, anchor=tk.NW
                )

                # ต้องเก็บ reference ของ PhotoImage ไว้ไม่ให้ถูก garbage collect
                canvas.photo_image = photo_image

                # เพิ่มฟังก์ชั่นปิดหน้าต่างเมื่อคลิกที่ใดก็ได้
                canvas.bind("<Button-1>", lambda e: sample_window.destroy())

                # ฟังก์ชั่นจัดการเมื่อมีการปรับขนาดหน้าต่าง
                def on_resize(event):
                    # ปรับขนาดภาพใหม่ตามขนาด canvas
                    new_width = canvas.winfo_width() - 20
                    new_height = canvas.winfo_height() - 20

                    if new_width <= 0 or new_height <= 0:
                        return

                    # สร้างภาพใหม่จากภาพต้นฉบับ
                    resized_image = self.original_image.copy()
                    resized_image.thumbnail((new_width, new_height), Image.LANCZOS)

                    # อัปเดต PhotoImage
                    new_photo = ImageTk.PhotoImage(resized_image)
                    canvas.itemconfig(canvas_image, image=new_photo)
                    canvas.photo_image = new_photo

                    # ปรับตำแหน่งของภาพให้อยู่ตรงกลาง canvas
                    x_pos = (canvas.winfo_width() - resized_image.width) // 2
                    y_pos = (canvas.winfo_height() - resized_image.height) // 2
                    canvas.coords(canvas_image, x_pos, y_pos)

                    # อัปเดตตำแหน่งของข้อความคำแนะนำ
                    canvas.delete("guide_text")
                    canvas.create_text(
                        canvas.winfo_width() - 10,
                        canvas.winfo_height() - 10,
                        text="คลิกเพื่อปิด",
                        fill="#cccccc",
                        font=("IBM Plex Sans Thai Medium", 8),
                        anchor=tk.SE,
                        tags="guide_text",
                    )

                # ผูก event การ resize กับฟังก์ชั่น
                canvas.bind("<Configure>", on_resize)

                # ให้ภาพอยู่ตรงกลางเริ่มต้น - เรียกฟังก์ชั่น on_resize ครั้งแรก
                sample_window.update_idletasks()
                on_resize(None)

                # วางหน้าต่างตรงกลางจอ
                sample_window.update_idletasks()
                width = sample_window.winfo_width()
                height = sample_window.winfo_height()

                # ใช้ตำแหน่งกลางของ parent window เป็นจุดอ้างอิง
                x = (
                    self.font_window.winfo_rootx()
                    + (self.font_window.winfo_width() // 2)
                    - (width // 2)
                )
                y = (
                    self.font_window.winfo_rooty()
                    + (self.font_window.winfo_height() // 2)
                    - (height // 2)
                )

                # ตรวจสอบว่าหน้าต่างไม่เกินขอบจอ
                screen_width = sample_window.winfo_screenwidth()
                screen_height = sample_window.winfo_screenheight()

                # ปรับตำแหน่งหากเกินขอบจอ
                x = max(0, min(x, screen_width - width))
                y = max(0, min(y, screen_height - height))

                sample_window.geometry(f"{width}x{height}+{x}+{y}")

                # ทำให้หน้าต่างอยู่ด้านหน้าเสมอ
                sample_window.attributes("-topmost", True)
                sample_window.transient(self.font_window)
                sample_window.focus_set()

            except Exception as e:
                self.show_temporary_notification(
                    f"ไม่สามารถเปิดภาพตัวอย่าง: {e}", color="#f44336"
                )
                # ถ้าเกิดข้อผิดพลาด ให้ลองใช้ webbrowser เปิดไฟล์โดยตรง
                try:
                    import webbrowser

                    webbrowser.open(self.sample_image_path)
                except:
                    pass

    def validate_selected_font(self):
        """ตรวจสอบฟอนต์ที่เลือกในปัจจุบัน"""
        selected = self.font_listbox.curselection()
        if not selected:
            self.show_temporary_notification("กรุณาเลือกฟอนต์ก่อน", color="#f44336")
            return

        font_name = self.font_listbox.get(selected[0])
        font_size = int(self.font_size.get())

        # แสดง loading state
        self.validation_status.config(text="กำลังตรวจสอบฟอนต์...", fg="#ffbf00")
        self.validation_sample.config(text="กำลังประมวลผล...")
        for label in self.metadata_labels.values():
            label.config(text="-")
        self.thai_support_indicator.config(
            text="รองรับภาษาไทย: กำลังตรวจสอบ...", fg="#ffbf00"
        )
        self.open_sample_btn.config(state=tk.DISABLED)
        self.sample_image_path = None

        # อัพเดต UI เพื่อให้เห็น loading state
        self.font_window.update()

        # ตรวจสอบการแสดงผล
        validation = self.font_manager.validate_font_rendering(font_name, font_size)

        # แสดงผลลัพธ์
        if validation["status"] == "success":
            self.validation_status.config(
                text=f"✅ ฟอนต์ {font_name} สามารถโหลดได้ถูกต้อง", fg="#4CAF50"
            )

            # อัพเดทตัวอย่างข้อความด้วยฟอนต์ที่เลือก
            self.validation_sample.config(
                text="การทดสอบฟอนต์ภาษาไทย กขคง ABCdef 123 !@#",
                font=(font_name, font_size),
            )

            # แสดง metadata
            metadata = validation.get("metadata", {})
            for field, label in self.metadata_labels.items():
                if field == "supported_scripts" and field in metadata:
                    label.config(text=", ".join(metadata[field]))
                elif field in metadata:
                    label.config(text=metadata[field] or "-")
                else:
                    label.config(text="-")

            # แสดงสถานะการรองรับภาษาไทย
            has_thai = validation.get("has_thai_support", False)
            if has_thai:
                self.thai_support_indicator.config(text="✅ รองรับภาษาไทย", fg="#4CAF50")
            else:
                self.thai_support_indicator.config(
                    text="❌ ไม่รองรับภาษาไทย", fg="#f44336"
                )

            # เปิดใช้งานปุ่มเปิดภาพตัวอย่าง
            if "test_image" in validation and os.path.exists(validation["test_image"]):
                self.sample_image_path = validation["test_image"]
                self.open_sample_btn.config(state=tk.NORMAL)

                # แสดงข้อความแจ้งเตือน
                self.show_temporary_notification(
                    "ตรวจสอบฟอนต์เสร็จสิ้น คลิกที่ปุ่ม 'เปิดภาพตัวอย่าง' เพื่อดูภาพตัวอย่างเพิ่มเติม"
                )
        else:
            self.validation_status.config(
                text=f"❌ พบปัญหา: {validation.get('message', 'ไม่ทราบสาเหตุ')}",
                fg="#f44336",
            )

            self.validation_sample.config(
                text=f"ไม่สามารถแสดงตัวอย่างฟอนต์ได้", font=("Arial", 12)
            )

            self.thai_support_indicator.config(
                text="❌ ไม่สามารถตรวจสอบการรองรับภาษาไทย", fg="#f44336"
            )

            self.show_temporary_notification(
                f"การตรวจสอบฟอนต์ล้มเหลว: {validation.get('message', 'ไม่ทราบสาเหตุ')}",
                color="#f44336",
            )


# ฟังก์ชันเริ่มต้นโมดูล
def initialize_font_manager(project_dir=None, settings=None):
    """
    เริ่มต้นใช้งานตัวจัดการฟอนต์

    Args:
        project_dir: ที่อยู่โฟลเดอร์โปรเจค
        settings: ตัวจัดการการตั้งค่า

    Returns:
        FontManager: ตัวจัดการฟอนต์
    """
    font_manager = FontManager(project_dir)

    if settings:
        font_settings = FontSettings(settings)
        font_manager.font_settings = font_settings

    return font_manager


class FontUIManager:
    """Singleton manager สำหรับจัดการ FontUI instance เพื่อป้องกันการเปิดหลายหน้าต่าง"""
    _instance = None
    _font_ui = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_or_create_font_ui(self, parent, font_manager, settings, apply_callback):
        """สร้างหรือคืน FontUI instance ที่มีอยู่"""
        if self._font_ui is None or not self._is_font_ui_valid():
            self._font_ui = FontUI(parent, font_manager, settings, apply_callback)
        else:
            # อัพเดต callback ถ้าจำเป็น
            self._font_ui.apply_callback = apply_callback
            # อัพเดต parent ถ้าเปลี่ยน
            self._font_ui.parent = parent
        return self._font_ui
    
    def _is_font_ui_valid(self):
        """ตรวจสอบว่า FontUI instance ยังใช้งานได้หรือไม่"""
        if self._font_ui is None:
            return False
        if not hasattr(self._font_ui, 'font_window'):
            return False
        try:
            return self._font_ui.font_window and self._font_ui.font_window.winfo_exists()
        except:
            return False
    
    def close_font_ui(self):
        """ปิด FontUI และเคลียร์ reference"""
        if self._font_ui:
            try:
                if hasattr(self._font_ui, 'close_font_ui'):
                    self._font_ui.close_font_ui()
            except:
                pass
            self._font_ui = None
