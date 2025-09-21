import time
import re
import json
import os
from enum import Enum
import logging


# DialogueType Enum
class DialogueType(Enum):
    NORMAL = "normal"  # ข้อความทั่วไป
    CHARACTER = "character"  # ข้อความของตัวละคร มีชื่อนำหน้า
    CHOICE = "choice"  # ข้อความตัวเลือกของผู้เล่น
    SYSTEM = "system"  # ข้อความระบบ


class NameConfidence:
    def __init__(self, name):
        self.name = name
        self.confidence = 0.8  # เริ่มต้นที่ 0.8 เพราะผ่านการตรวจสอบแล้ว
        self.last_update = time.time()

    def add_appearance(self):
        """อัพเดทเวลาล่าสุดที่พบชื่อนี้"""
        self.last_update = time.time()

    def should_confirm(self):
        """ตรวจสอบว่าควรยืนยันชื่อนี้หรือไม่"""
        return (
            self.confidence >= 0.7  # ลดเกณฑ์ความเชื่อมั่น
            and len(self.appearances) >= 2  # ลดจำนวนครั้งที่ต้องเจอ
            and time.time() - self.appearances[0]["time"] < 600  # เพิ่มเวลาเป็น 10 นาที
        )


class TextCorrector:
    def __init__(self):
        self.load_npc_data()

        # สร้างไฟล์ new_friends.json ถ้ายังไม่มี
        initial_data = {"npcs": [], "last_updated": time.time(), "version": "1.0"}
        if not os.path.exists("new_friends.json"):
            try:
                with open("new_friends.json", "w", encoding="utf-8") as f:
                    json.dump(initial_data, f, indent=4, ensure_ascii=False)
                logging.info("Created new new_friends.json file")
            except Exception as e:
                logging.error(f"Failed to create new_friends.json: {e}")

        # โหลดข้อมูล
        self.load_new_friends()

        # ระบบแคชใหม่
        self.temp_names_cache = []  # เปลี่ยนเป็น list เพื่อเก็บลำดับ
        self.confirmed_names = set()  # เพิ่มบรรทัดนี้
        self.max_cached_names = 10

    def initialize_enhanced_name_detector(self):
        """
        เพิ่มระบบตรวจจับชื่อขั้นสูงเข้าไปใน TextCorrector
        """
        try:
            from enhanced_name_detector import EnhancedNameDetector

            # ตรวจสอบว่ามี names แล้วหรือยัง
            if not hasattr(self, "names") or len(self.names) == 0:
                print("Warning: No character names available for EnhancedNameDetector")
                logging.warning("No character names available for EnhancedNameDetector")
                self.names = set(["???"])  # อย่างน้อยมีชื่อพื้นฐาน

            self.enhanced_detector = EnhancedNameDetector(
                self.names, logging_manager=logging.getLogger()
            )
            print("Enhanced name detector initialized successfully")
            logging.info("Enhanced name detector initialized successfully")
        except ImportError as e:
            print(f"Could not import EnhancedNameDetector: {e}")
            logging.warning(f"Could not import EnhancedNameDetector: {e}")
        except Exception as e:
            print(f"Error initializing enhanced name detector: {e}")
            logging.warning(f"Error initializing enhanced name detector: {e}")

    # อัพเดทเมธอด split_speaker_and_content เพื่อใช้ระบบตรวจจับชื่อใหม่
    def split_speaker_and_content(self, text):
        """แยกชื่อผู้พูดและเนื้อหาด้วยระบบที่แม่นยำขึ้น"""

        # ตรวจสอบว่ามีการเปิดใช้ระบบขั้นสูงหรือไม่
        if hasattr(self, "enhanced_detector"):
            # ใช้ระบบตรวจจับชื่อขั้นสูง
            speaker, content, dialogue_type = (
                self.enhanced_detector.enhanced_split_speaker_and_content(
                    text, previous_speaker=self.get_last_speaker_if_available()
                )
            )

            # บันทึกชื่อลงในประวัติล่าสุดถ้าพบ
            if speaker:
                self.enhanced_detector.add_recent_name(speaker)

            return speaker, content, dialogue_type

        # ถ้าไม่มีระบบขั้นสูง ใช้โค้ดเดิม
        # ตรวจสอบ ??? หรือ 22 หรือ 222 ก่อน
        if text.startswith(("???", "??", "22", "222")):
            for separator in [": ", " - ", " – "]:
                if separator in text:
                    content = text.split(separator, 1)[1].strip()
                    return "???", content, DialogueType.CHARACTER
            return None, text, DialogueType.NORMAL

        # จัดการกับ underscore ที่ท้ายประโยค
        text = text.replace("_", "")

        # ตรวจสอบรูปแบบที่มีเครื่องหมายคั่น
        content_separators = [": ", " - ", " – "]
        speaker = None
        content = None

        for separator in content_separators:
            if separator in text:
                parts = text.split(separator, 1)
                if len(parts) == 2:
                    speaker = parts[0].strip()
                    content = parts[1].strip()

                    # เพิ่มการใช้ word_corrections กับ speaker ตรงนี้
                    # แก้ไขคำใน speaker โดยใช้ word_corrections
                    words_in_speaker = speaker.split()
                    corrected_speaker_words = []
                    for word in words_in_speaker:
                        if not re.search(r"[\u0E00-\u0E7F]", word):
                            word = self.word_corrections.get(word, word)
                        corrected_speaker_words.append(word)
                    speaker = " ".join(corrected_speaker_words)

                    # เพิ่มการจัดการกรณีเฉพาะเช่น "Graha Tia Tia"
                    if "Tia Tia" in speaker:
                        speaker = speaker.replace("Tia Tia", "Tia")

                    # เพิ่มการตรวจสอบชื่อที่เป็นตัวเลข
                    if self.is_numeric_name(speaker):
                        return None, text, DialogueType.NORMAL  # ให้รอ OCR รอบถัดไป

                    # ถ้าชื่อขึ้นต้นด้วย ? ให้แปลงเป็น ???
                    if speaker.startswith("?"):
                        speaker = "???"
                        return speaker, content.strip(), DialogueType.CHARACTER

                    # ตรวจสอบในชื่อที่รู้จัก
                    if speaker in self.names or speaker in self.confirmed_names:
                        return speaker, content.strip(), DialogueType.CHARACTER
                    else:
                        # ถ้าไม่พบชื่อที่ตรงกัน ให้ถือเป็นข้อความทั้งหมด
                        return None, text, DialogueType.NORMAL

        # กรณีไม่มีเครื่องหมายคั่น ให้ถือเป็นข้อความทั่วไป
        return None, text, DialogueType.NORMAL

    def get_last_speaker_if_available(self):
        """
        ดึงชื่อผู้พูดล่าสุดจากประวัติ (ถ้ามี)
        """
        if hasattr(self, "temp_names_cache") and self.temp_names_cache:
            return (
                self.temp_names_cache[0].name
                if hasattr(self.temp_names_cache[0], "name")
                else None
            )
        return None

    # อัพเดทเมธอด calculate_name_similarity เพื่อปรับปรุงให้แม่นยำขึ้น
    def calculate_name_similarity(self, name1, name2):
        """คำนวณความคล้ายคลึงของชื่อด้วยวิธีที่ปรับปรุงแล้ว"""
        # ใช้ระบบตรวจจับชื่อขั้นสูงถ้ามี
        if hasattr(self, "enhanced_detector"):
            return self.enhanced_detector.calculate_name_similarity(name1, name2)

        # ถ้าไม่มีระบบขั้นสูง ใช้โค้ดเดิม
        if not name1 or not name2:
            return 0

        clean_name1 = self._clean_name(name1)
        clean_name2 = self._clean_name(name2)

        if clean_name1 == clean_name2:
            return 1.0

        len1, len2 = len(clean_name1), len(clean_name2)
        if len1 == 0 or len2 == 0:
            return 0

        matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]

        for i in range(len1 + 1):
            matrix[i][0] = i
        for j in range(len2 + 1):
            matrix[0][j] = j

        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if clean_name1[i - 1] == clean_name2[j - 1]:
                    matrix[i][j] = matrix[i - 1][j - 1]
                else:
                    matrix[i][j] = min(
                        matrix[i - 1][j] + 1,  # deletion
                        matrix[i][j - 1] + 1,  # insertion
                        matrix[i - 1][j - 1] + 1,  # substitution
                    )

        distance = matrix[len1][len2]
        max_length = max(len1, len2)
        similarity = 1 - (distance / max_length)

        return similarity

    def load_new_friends(self):
        """โหลดชื่อที่ยืนยันแล้วจาก new_friends.json"""
        try:
            if os.path.exists("new_friends.json"):
                with open("new_friends.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for npc in data.get("npcs", []):
                        self.confirmed_names.add(npc["name"])
        except Exception as e:
            logging.error(f"Error loading new_friends.json: {e}")

    # save_new_friend method removed - was only used by force translate

    def cache_new_name(self, name):
        """เพิ่มชื่อใหม่เข้าแคชแบบวงกลม"""
        # ตรวจสอบว่ามีชื่อนี้ในแคชหรือไม่
        for cached in self.temp_names_cache:
            if cached.name == name:
                cached.add_appearance()
                return cached.name

        # ถ้าไม่มี เพิ่มชื่อใหม่
        new_name = NameConfidence(name)
        self.temp_names_cache.append(new_name)

        # ถ้าเกินขนาด ลบตัวแรกออก
        if len(self.temp_names_cache) > self.max_cached_names:
            self.temp_names_cache.pop(0)

        return name

    def find_similar_cached_name(self, name):
        """ค้นหาชื่อที่คล้ายกันในแคช"""
        highest_similarity = 0
        best_match = None

        for cached in self.temp_names_cache:
            similarity = self.calculate_name_similarity(name, cached.name)
            if (
                similarity > highest_similarity and similarity > 0.7
            ):  # ต้องคล้ายกันมากกว่า 70%
                highest_similarity = similarity
                best_match = cached.name

        return best_match

    def is_likely_character_name(self, text):
        """ตรวจสอบว่าข้อความน่าจะเป็นชื่อคนหรือไม่"""
        words = text.split()
        first_word = words[0] if words else ""

        # ต้องขึ้นต้นด้วยตัวพิมพ์ใหญ่
        if not first_word or not first_word[0].isupper():
            return False

        # ไม่ควรมีตัวอักษรพิเศษมากเกินไป (ยกเว้น ' - และ space)
        special_chars = sum(1 for c in text if not c.isalnum() and c not in "' -")
        if special_chars > 1:
            return False

        # ความยาวของชื่อทั้งหมดควรอยู่ในช่วงที่เหมาะสม
        if len(text) < 2 or len(text) > 50:  # เพิ่มความยาวให้รองรับชื่อยาวๆ
            return False

        # ตรวจสอบแต่ละคำในชื่อ
        common_words = {
            "the",
            "a",
            "an",
            "this",
            "that",
            "these",
            "those",
            "here",
            "there",
        }
        first_word_lower = first_word.lower()

        # คำแรกต้องไม่ใช่คำทั่วไป
        if first_word_lower in common_words:
            return False

        # ถ้ามีหลายคำ ทุกคำควรขึ้นต้นด้วยตัวพิมพ์ใหญ่หรือเป็นคำเชื่อม
        connecting_words = {"van", "von", "de", "del", "of", "the"}
        for word in words[1:]:
            if not word[0].isupper() and word.lower() not in connecting_words:
                return False

        return True

    def load_npc_data(self):
        try:
            # ทำให้การค้นหาไฟล์ทนทานมากขึ้น โดยทดลองชื่อไฟล์ที่ต่างกัน
            file_candidates = ["NPC.json", "npc.json"]
            file_path = None

            # หาไดเรกทอรีปัจจุบัน
            base_dir = os.path.dirname(os.path.abspath(__file__))

            # ลองหาไฟล์ในโฟลเดอร์ปัจจุบัน
            for candidate in file_candidates:
                temp_path = os.path.join(base_dir, candidate)
                if os.path.exists(temp_path):
                    file_path = temp_path
                    print(f"Found NPC data file at: {file_path}")
                    break

            # ถ้าไม่พบ ลองหาในโฟลเดอร์ชั้นบน
            if not file_path:
                parent_dir = os.path.dirname(base_dir)
                for candidate in file_candidates:
                    temp_path = os.path.join(parent_dir, candidate)
                    if os.path.exists(temp_path):
                        file_path = temp_path
                        print(f"Found NPC data file at: {file_path}")
                        break

            # ถ้ายังไม่พบ ลองค้นหาในโฟลเดอร์ C:\Magicite_Babel
            if not file_path:
                mb_dir = "C:\\Magicite_Babel"
                for candidate in file_candidates:
                    temp_path = os.path.join(mb_dir, candidate)
                    if os.path.exists(temp_path):
                        file_path = temp_path
                        print(f"Found NPC data file at: {file_path}")
                        break

            # ถ้าไม่พบไฟล์เลย
            if not file_path:
                print("NPC.json file not found in any search locations!")
                raise FileNotFoundError("NPC.json file not found")

            # เปิดไฟล์ที่พบและโหลดข้อมูล
            with open(file_path, "r", encoding="utf-8") as file:
                npc_data = json.load(file)
                self.word_corrections = npc_data["word_fixes"]
                self.names = set()

                # เพิ่ม "???" เป็นชื่อที่ยอมรับได้
                self.names.add("???")

                # Load main characters
                for char in npc_data["main_characters"]:
                    if char["firstName"]:
                        self.names.add(char["firstName"])
                    if char["lastName"]:
                        self.names.add(char["lastName"])

                # Load NPCs
                for npc in npc_data["npcs"]:
                    self.names.add(npc["name"])

                print(f"Loaded {len(self.names)} character names successfully")
                logging.info(
                    f"TextCorrector: Loaded {len(self.names)} character names from {file_path}"
                )

                # พยายามเริ่มต้น enhanced detector ถ้ามี
                try:
                    if not hasattr(self, "enhanced_detector"):
                        self.initialize_enhanced_name_detector()
                except ImportError:
                    logging.warning(
                        "EnhancedNameDetector not available - some name detection features will be limited"
                    )
                except Exception as e:
                    logging.warning(f"Could not initialize enhanced name detector: {e}")

        except FileNotFoundError:
            print("NPC.json file not found!")
            raise FileNotFoundError("NPC.json file not found")
        except json.JSONDecodeError:
            print("Invalid JSON in NPC.json!")
            raise ValueError("Invalid JSON in NPC.json")
        except Exception as e:
            print(f"Unexpected error loading NPC data: {e}")
            raise Exception(f"Failed to load NPC data: {e}")

    def correct_text(self, text):
        # เพิ่มการจัดการพิเศษสำหรับ 22, 222 และ ?
        if text.strip() in ["22", "22?", "222", "222?", "???"]:
            return "???"

        # แทนที่ 22 หรือ 222 ด้วย ??? ถ้าขึ้นต้นด้วย 22 หรือ 222
        text = re.sub(r"^(22|222)\s*", "??? ", text)

        speaker, content, dialogue_type = self.split_speaker_and_content(text)

        if speaker and speaker != "???":
            # เพิ่มการตรวจสอบ compound words ใน speaker
            for original, replacement in self.word_corrections.items():
                if " " in original and original in speaker:  # เฉพาะคำที่มีช่องว่าง (หลายคำ)
                    speaker = speaker.replace(original, replacement)

            # ล้างเครื่องหมายพิเศษที่ไม่ต้องการ
            speaker = re.sub(r"[^\w\s\u0E00-\u0E7F]", "", speaker)

        # เพิ่มการตรวจหาและแก้ไขชื่อที่ซ้ำซ้อน
        # ตรวจสอบกรณีเฉพาะเช่น "Graha Tia Tia" -> "G'raha Tia"
        if speaker and "Tia Tia" in speaker:
            speaker = speaker.replace("Tia Tia", "Tia")

        # ตรวจสอบกรณีทั่วไปของคำซ้ำ
        repeated_word_pattern = r"\b(\w+)(\s+\1)+\b"
        if speaker:
            speaker = re.sub(repeated_word_pattern, r"\1", speaker)

        words = content.split() if content else []
        corrected_words = []
        for word in words:
            if not re.search(r"[\u0E00-\u0E7F]", word):
                word = self.word_corrections.get(word, word)
            corrected_words.append(word)

        content = (
            self.clean_content(" ".join(corrected_words)) if corrected_words else ""
        )

        if speaker:
            return f"{speaker}: {content}" if content else speaker
        return content

    def _clean_name(self, name):
        """ทำความสะอาดชื่อเพื่อเปรียบเทียบ"""
        if not name:
            return ""
        name = name.lower().strip()
        replacements = {
            "'": "",
            "`": "",
            " ": "",
            "z": "2",
            "$": "s",
            "0": "o",
            "1": "l",
        }
        for old, new in replacements.items():
            name = name.replace(old, new)
        return name

    def calculate_name_similarity(self, name1, name2):
        """คำนวณความคล้ายคลึงของชื่อ"""
        if not name1 or not name2:
            return 0

        clean_name1 = self._clean_name(name1)
        clean_name2 = self._clean_name(name2)

        if clean_name1 == clean_name2:
            return 1.0

        len1, len2 = len(clean_name1), len(clean_name2)
        if len1 == 0 or len2 == 0:
            return 0

        matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]

        for i in range(len1 + 1):
            matrix[i][0] = i
        for j in range(len2 + 1):
            matrix[0][j] = j

        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if clean_name1[i - 1] == clean_name2[j - 1]:
                    matrix[i][j] = matrix[i - 1][j - 1]
                else:
                    matrix[i][j] = min(
                        matrix[i - 1][j] + 1,  # deletion
                        matrix[i][j - 1] + 1,  # insertion
                        matrix[i - 1][j - 1] + 1,  # substitution
                    )

        distance = matrix[len1][len2]
        max_length = max(len1, len2)
        similarity = 1 - (distance / max_length)

        return similarity

    def is_numeric_name(self, name: str) -> bool:
        """
        ตรวจสอบว่าชื่อเป็นตัวเลขหรือไม่
        Args:
            name: ชื่อที่ต้องการตรวจสอบ
        Returns:
            bool: True ถ้าชื่อเป็นตัวเลข, False ถ้าไม่ใช่
        """
        # ลบช่องว่างและอักขระพิเศษ
        cleaned_name = re.sub(r"[^a-zA-Z0-9]", "", name)
        # ตรวจสอบว่าเหลือแต่ตัวเลขหรือไม่
        return cleaned_name.isdigit()

    def split_speaker_and_content(self, text):
        """แยกชื่อผู้พูดและเนื้อหา"""
        # ตรวจสอบ ??? หรือ 22 หรือ 222 ก่อน
        if text.startswith(("???", "??", "22", "222")):
            for separator in [": ", " - ", " – "]:
                if separator in text:
                    content = text.split(separator, 1)[1].strip()
                    return "???", content, DialogueType.CHARACTER
            return None, text, DialogueType.NORMAL

        # จัดการกับ underscore ที่ท้ายประโยค
        text = text.replace("_", "")

        # ตรวจสอบรูปแบบที่มีเครื่องหมายคั่น
        content_separators = [": ", " - ", " – "]
        speaker = None
        content = None

        for separator in content_separators:
            if separator in text:
                parts = text.split(separator, 1)
                if len(parts) == 2:
                    speaker = parts[0].strip()
                    content = parts[1].strip()

                    # เพิ่มการใช้ word_corrections กับ speaker ตรงนี้
                    # แก้ไขคำใน speaker โดยใช้ word_corrections
                    words_in_speaker = speaker.split()
                    corrected_speaker_words = []
                    for word in words_in_speaker:
                        if not re.search(r"[\u0E00-\u0E7F]", word):
                            word = self.word_corrections.get(word, word)
                        corrected_speaker_words.append(word)
                    speaker = " ".join(corrected_speaker_words)

                    # เพิ่มการจัดการกรณีเฉพาะเช่น "Graha Tia Tia"
                    if "Tia Tia" in speaker:
                        speaker = speaker.replace("Tia Tia", "Tia")

                    # เพิ่มการตรวจสอบชื่อที่เป็นตัวเลข
                    if self.is_numeric_name(speaker):
                        return None, text, DialogueType.NORMAL  # ให้รอ OCR รอบถัดไป

                    # ถ้าชื่อขึ้นต้นด้วย ? ให้แปลงเป็น ???
                    if speaker.startswith("?"):
                        speaker = "???"
                        return speaker, content.strip(), DialogueType.CHARACTER

                    # ตรวจสอบในชื่อที่รู้จัก
                    if speaker in self.names or speaker in self.confirmed_names:
                        return speaker, content.strip(), DialogueType.CHARACTER
                    else:
                        # ถ้าไม่พบชื่อที่ตรงกัน ให้ถือเป็นข้อความทั้งหมด
                        return None, text, DialogueType.NORMAL

        # กรณีไม่มีเครื่องหมายคั่น ให้ถือเป็นข้อความทั่วไป
        return None, text, DialogueType.NORMAL

    def clean_content(self, content):
        # Clean content for English + Thai characters only
        # \u0E00-\u0E7F = Thai characters
        # Future: add \u4E00-\u9FFF for Traditional Chinese
        content = re.sub(
            r"[^\w\s\u0E00-\u0E7F.!...—()]", "", content
        )

        # แก้ไข '|' เป็น 'I' เสมอ
        content = content.replace("|", "I")

        # แก้ไข '!' เป็น 'I' เมื่ออยู่ต้นประโยคหรือหลังช่องว่าง
        content = re.sub(r'(^|(?<=\s))!(?![\s"\'.])', "I", content)

        # แทนที่สัญลักษณ์การหยุดรอด้วย ...
        content = re.sub(r"[_\-]{2,}", "...", content)

        # รวมช่องว่าง
        content = re.sub(r"\s+", " ", content)

        # จัดการ ... ท้ายประโยค
        if not content.endswith(("...", "!", "—")):
            content = re.sub(r"\.{1,2}$", "...", content)

        # รักษาเครื่องหมาย —
        content = content.replace(" - ", " — ")

        return content.strip()

    def reload_data(self):
        """โหลดข้อมูลใหม่"""
        print("TextCorrector: Reloading NPC data...")  # เพิ่มบรรทัดนี้
        self.load_npc_data()
        # ล้างแคชทั้งหมด
        self.temp_names_cache.clear()
        self.load_new_friends()  # โหลด confirmed names ใหม่
        print("TextCorrector: Data reloaded successfully")  # เพิ่มบรรทัดนี้
