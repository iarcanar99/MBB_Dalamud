import os
import json
from datetime import datetime
import difflib
import logging

class TranslationLogger:
    def __init__(self, base_path=r"C:\Magicite Babel"):
        """
        Initialize translation logger
        Args:
            base_path (str): Base directory path where logs will be stored
        """
        # กำหนดพาธพื้นฐาน
        self.base_path = base_path
        self.log_path = os.path.join(base_path, "logs", "translations")
        
        # สร้างโฟลเดอร์ถ้ายังไม่มี
        self.ensure_log_directory()
        
        # เก็บวันที่ปัจจุบัน
        self.today_date = self._get_today_date()
        
        # เก็บข้อความแปลล่าสุดเพื่อเช็คความซ้ำซ้อน
        self.last_en_text = None
        self.last_th_text = None
        
        logging.info(f"TranslationLogger initialized. Log path: {self.log_path}")
        
    def ensure_log_directory(self):
        """Create log directory if it doesn't exist"""
        try:
            if not os.path.exists(self.log_path):
                os.makedirs(self.log_path)
                logging.info(f"Created log directory: {self.log_path}")
        except Exception as e:
            logging.error(f"Error creating log directory: {e}")
            raise

    def _get_today_date(self):
        """Get current date in YYYYMMDD format"""
        return datetime.now().strftime("%Y%m%d")

    def _get_log_files(self):
        """
        Get paths for today's log files
        Returns:
            dict: Paths for English and Thai log files
        """
        today = self._get_today_date()
        return {
            'en': os.path.join(self.log_path, f"EN_cons_{today}.log"),
            'th': os.path.join(self.log_path, f"TH_cons_{today}.log")
        }

    def _format_message(self, text):
        """
        Format message for logging with speaker name and content
        Args:
            text (str): Text to format
        Returns:
            tuple: (speaker, content) or (None, text) if no speaker
        """
        # ถ้าข้อความว่างเปล่า
        if not text or not text.strip():
            return None, ""
                
        # แยกส่วนชื่อผู้พูดและข้อความ
        if ": " in text:
            speaker, message = text.split(": ", 1)
            return speaker.strip(), message.strip()
        return None, text.strip()

    def _clean_text_for_comparison(self, text):
        """
        Clean text for similarity comparison
        Args:
            text (str): Text to clean
        Returns:
            str: Cleaned text
        """
        if not text:
            return ""
        # ลบช่องว่างและตัวอักษรพิเศษ
        text = text.strip()
        # ถ้ามีชื่อคนพูด ให้ตัดออกก่อนเปรียบเทียบ
        if ": " in text:
            text = text.split(": ", 1)[1]
        return text

    def _is_similar(self, text1, text2, threshold=0.8):
        """
        Check if two texts are similar using difflib
        Args:
            text1 (str): First text
            text2 (str): Second text
            threshold (float): Similarity threshold (0-1)
        Returns:
            bool: True if texts are similar
        """
        if not text1 or not text2:
            return False
            
        # ทำความสะอาดข้อความก่อนเปรียบเทียบ
        clean_text1 = self._clean_text_for_comparison(text1)
        clean_text2 = self._clean_text_for_comparison(text2)
        
        if not clean_text1 or not clean_text2:
            return False
            
        # คำนวณความเหมือน
        similarity = difflib.SequenceMatcher(None, clean_text1, clean_text2).ratio()
        return similarity >= threshold

    def _load_last_text(self, file_path):
        """
        Load last non-empty text from file
        Args:
            file_path (str): Path to log file
        Returns:
            str: Last text or None if file doesn't exist
        """
        if not os.path.exists(file_path):
            return None
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # ย้อนกลับมาหาข้อความสุดท้ายที่ไม่ใช่บรรทัดว่าง
                for line in reversed(lines):
                    if line.strip():
                        return line.strip()
        except Exception as e:
            logging.error(f"Error loading last text from {file_path}: {e}")
            return None
            
        return None

    def log_translation(self, original_text, translated_text):
        """
        Log original and translated text to respective files
        Args:
            original_text (str): Original English text
            translated_text (str): Translated Thai text
        """
        # เช็ควันที่เพื่อสร้างชื่อไฟล์
        current_date = self._get_today_date()
        if current_date != self.today_date:
            self.today_date = current_date

        # ถ้าข้อความว่างเปล่า ไม่ต้องบันทึก
        if not original_text.strip() or not translated_text.strip():
            return

        try:
            log_files = self._get_log_files()
            
            # แยกชื่อผู้พูดและข้อความต้นฉบับ
            en_speaker, en_content = self._format_message(original_text)
            _, th_content = self._format_message(translated_text)
            
            # บันทึกข้อความต้นฉบับ
            with open(log_files['en'], 'a', encoding='utf-8') as f:
                if en_speaker:
                    f.write(f"{en_speaker}: {en_content}\n\n")
                else:
                    f.write(f"{en_content}\n\n")
                    
            # บันทึกข้อความแปลพร้อมชื่อผู้พูดจากต้นฉบับ
            with open(log_files['th'], 'a', encoding='utf-8') as f:
                if en_speaker:
                    f.write(f"{en_speaker}: {th_content}\n\n")
                else:
                    f.write(f"{th_content}\n\n")
                
            logging.debug(f"Translation logged successfully")
                
        except Exception as e:
            logging.error(f"Error logging translation: {e}")

    def get_today_logs(self):
        """
        Get both English and Thai logs for today
        Returns:
            dict: Dictionary containing English and Thai logs
        """
        log_files = self._get_log_files()
        logs = {'en': [], 'th': []}
        
        for lang, file_path in log_files.items():
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        # อ่านและกรองเฉพาะบรรทัดที่ไม่ว่างเปล่า
                        logs[lang] = [line.strip() for line in f.readlines() if line.strip()]
                except Exception as e:
                    logging.error(f"Error reading {lang} log file: {e}")
                    logs[lang] = []
                    
        return logs

    def clear_today_logs(self):
        """Clear log files for today"""
        try:
            log_files = self._get_log_files()
            for file_path in log_files.values():
                if os.path.exists(file_path):
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write("")
            logging.info("Today's logs cleared")
        except Exception as e:
            logging.error(f"Error clearing logs: {e}")
            raise