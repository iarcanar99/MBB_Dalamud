import os
import logging
from datetime import datetime
import time
import psutil  # type: ignore
import GPUtil  # type: ignore
import traceback


class LoggingManager:
    def __init__(self, settings):
        self.settings = settings
        self.log_dir = "logs"
        self.ensure_directories()
        self.setup_logging()
        self.error_file = None
        self.last_status_message = ""
        self.loading_symbols = ["|", "/", "-", "\\"]
        self.loading_index = 0
        self.seen_messages = set()  # เพิ่มตัวแปรเก็บข้อความที่เคยแสดงแล้ว
        # เพิ่มตัวแปรควบคุมการแสดง log
        self.initialization_complete = False
        self.npc_loaded = False
        self.font_loaded = False

    def log_npc_manager(self, message):
        """บันทึกข้อความสำหรับ NPC Manager แบบกรองแล้ว"""
        # ข้อความสำคัญที่ต้องการแสดง
        important_messages = [
            "NPC Manager started",
            "Data loaded successfully",
            "Font system ready",
            "Error:",
            "Warning:",
        ]

        # แสดงเฉพาะข้อความสำคัญ
        if any(msg in message for msg in important_messages):
            print(message)

    def log_startup_info(self):
        """บันทึกข้อมูลสำคัญตอนเริ่มต้นระบบ"""
        current_model = self.settings.get_displayed_model()
        screen_size = self.settings.get("screen_size", "2560x1440")
        use_gpu = self.settings.get("use_gpu_for_ocr", False)

        startup_info = [
            "=== MagicBabel System Started ===",
            f"Model: {current_model}",
            f"Screen Size: {screen_size}",
            f"OCR Processing: {'GPU' if use_gpu else 'CPU'}",
            "===============================",
        ]

        for line in startup_info:
            logging.info(line)
            print(line)

    def log_model_change(self, old_model, new_model, parameters):
        """บันทึกการเปลี่ยนแปลง model"""
        log_lines = [
            "=== Model Change ===",
            f"From: {old_model}",
            f"To: {new_model}",
            "Parameters:",
            f"- Max Tokens: {parameters.get('max_tokens', 'N/A')}",
            f"- Temperature: {parameters.get('temperature', 'N/A')}",
            "===================",
        ]

        for line in log_lines:
            logging.info(line)
            print(line)

    def log_system_status(self):
        """บันทึกสถานะระบบ"""
        memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        gpu_usage = (
            self.get_gpu_usage() if self.settings.get("use_gpu_for_ocr") else "N/A"
        )

        status_lines = [
            "=== System Status ===",
            f"Memory Usage: {memory_usage:.2f} MB",
            f"GPU Usage: {gpu_usage}",
            "====================",
        ]

        for line in status_lines:
            logging.info(line)
            print(line)

    def ensure_directories(self):
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def setup_logging(self):
        """ตั้งค่าระบบ logging"""
        logging.basicConfig(
            filename=os.path.join(self.log_dir, "app.log"),
            level=logging.INFO,
            format="%(levelname)s: %(message)s",  # ลดรูปแบบให้กระชับ
        )

    def get_gpu_usage(self):
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                return f"{gpus[0].load * 100:.2f}%"
        except Exception as e:
            logging.error(f"Error getting GPU usage: {e}")
        return "N/A"

    def log_error(self, error_message):
        """บันทึกข้อความแจ้งเตือนระดับข้อผิดพลาด"""
        logging.error(error_message)
        self.write_error_to_file(error_message)
        print(f"\r❌ ERROR: {error_message}", flush=True)

    def write_error_to_file(self, error_message):
        """บันทึกข้อผิดพลาดลงไฟล์"""
        today = datetime.now().strftime("%Y%m%d")
        self.error_file = os.path.join(self.log_dir, f"error_{today}.log")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_error = f"[{timestamp}] {error_message}\n"
        
        # เพิ่ม traceback เฉพาะกรณีที่มี exception จริงๆ
        if traceback.format_exc() != 'NoneType: None\n':
            formatted_error += f"Traceback:\n{traceback.format_exc()}\n\n"

        with open(self.error_file, "a", encoding="utf-8") as file:
            file.write(formatted_error)

    def log_info(self, info_message):
        """กรองและบันทึก log เฉพาะข้อความสำคัญ"""
        # ข้อความที่อนุญาตให้แสดง
        allowed_messages = [
            "=== MagicBabel System Started ===",
            "Model: ",
            "Screen: ",
            "OCR: ",
            "===============================",
            "MagicBabel application started and ready",
        ]

        # แสดงเฉพาะข้อความที่อนุญาต
        if any(msg in info_message for msg in allowed_messages):
            logging.info(info_message.replace("INFO:root:", ""))
            return

        # กรณี warning จาก easyocr แสดงแบบกระชับ
        if "Using CPU" in info_message:
            logging.warning("OCR running on CPU mode")
            return

        # กรณี NPC.json โหลดสำเร็จ แสดงครั้งเดียว
        if "Loaded NPC.json successfully" in info_message and not hasattr(
            self, "_npc_loaded"
        ):
            logging.info("NPC data loaded")
            self._npc_loaded = True
            return

        # ข้อความอื่นๆ ไม่ต้องแสดง
        return

    def log_warning(self, warning_message):
        """บันทึกข้อความแจ้งเตือนระดับคำเตือน"""
        logging.warning(warning_message)
        print(f"\r⚠️ WARNING: {warning_message}", flush=True)

    def log_critical(self, critical_message):
        """บันทึกข้อความแจ้งเตือนระดับวิกฤต"""
        logging.critical(critical_message)
        self.write_error_to_file(f"CRITICAL: {critical_message}")
        print(f"\r🔥 CRITICAL: {critical_message}", flush=True)

    def update_status(self, message):
        """
        อัพเดทและแสดงสถานะแบบต่อเนื่องในบรรทัดเดียว
        Args:
            message: ข้อความที่ต้องการแสดง
        """
        current_time = time.time()

        # สถานะการทำงานต่อเนื่อง
        continuous_states = {
            "OCR scanning": {
                "icon": "🔍",
                "variants": ["scanning.", "scanning..", "scanning..."],
            },
            "Waiting for text": {
                "icon": "⌛",
                "variants": ["waiting.", "waiting..", "waiting..."],
            },
        }

        # ตรวจสอบว่าเป็นสถานะต่อเนื่องหรือไม่
        for state, config in continuous_states.items():
            if state in message:
                if not hasattr(self, "_animation_state"):
                    self._animation_state = 0
                    self._last_animation_time = 0

                # อัพเดทแอนิเมชันทุก 0.3 วินาที
                if current_time - self._last_animation_time > 0.3:
                    self._animation_state = (self._animation_state + 1) % len(
                        config["variants"]
                    )
                    self._last_animation_time = current_time

                display_message = f"{config['icon']} {state}{config['variants'][self._animation_state]}"
                print(f"\r{display_message:<60}", end="", flush=True)
                return

        # ข้อความที่ไม่ต้องแสดงซ้ำ
        skip_messages = {"OCR completed", "Processing image"}

        if message in skip_messages:
            if hasattr(self, "_last_message") and self._last_message == message:
                return

        # เก็บข้อความล่าสุด
        self._last_message = message

        # แสดงข้อความสำคัญเท่านั้น
        important_messages = {
            "Translation updated": "✅ Translation updated",
            "Error": "❌ Error detected",
        }

        if message in important_messages:
            display_message = important_messages[message]
            print(f"\r{display_message:<60}", end="", flush=True)
            logging.info(message)