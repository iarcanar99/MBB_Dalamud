import json
import os


class EnhancedNameDetector:
    """
    คลาสเสริมสำหรับเพิ่มความแม่นยำในการตรวจจับชื่อตัวละคร
    สามารถเพิ่มเป็นส่วนเสริมของ TextCorrector
    """

    def __init__(self, character_database, logging_manager=None):
        self.character_db = character_database
        self.logging_manager = logging_manager
        self.recent_names = []  # เก็บชื่อที่พบล่าสุด 10 ชื่อ
        self.max_recent = 10
        self.correction_patterns = self.build_correction_patterns()
        self.name_embeddings = {}  # สำหรับเก็บ vector embedding ของชื่อ
        self.word_fixes = {}  # เพิ่มตัวแปรนี้
        self.initialize_embeddings()
        self.load_word_fixes_from_npc_data()  # เพิ่มการเรียกเมธอดนี้

    def load_word_fixes_from_npc_data(self):
        """โหลดข้อมูลการแก้ไขคำจาก NPC.json"""
        try:
            with open("NPC.json", "r", encoding="utf-8") as file:
                npc_data = json.load(file)
                if "word_fixes" in npc_data:
                    self.word_fixes = npc_data["word_fixes"]
                    if self.logging_manager:
                        self.logging_manager.info(
                            f"Loaded {len(self.word_fixes)} word fixes from NPC.json"
                        )
                    else:
                        print(f"Loaded {len(self.word_fixes)} word fixes from NPC.json")
                else:
                    self.word_fixes = {}
        except Exception as e:
            self.word_fixes = {}
            if self.logging_manager:
                self.logging_manager.error(f"Error loading word fixes: {str(e)}")
            else:
                print(f"Error loading word fixes: {str(e)}")

    def build_correction_patterns(self):
        """สร้างรูปแบบการแก้ไขทั่วไปสำหรับข้อผิดพลาด OCR"""
        patterns = {
            "l": ["I", "1", "|"],  # l อาจถูกอ่านเป็น I, 1 หรือ |
            "I": ["l", "1", "|"],
            "0": ["O", "o", "D"],
            "O": ["0", "o", "D"],
            "rn": ["m"],
            "m": ["rn"],
            "5": ["S", "s"],
            "S": ["5"],
            "'": ["`", "´", "'"],
            " ": ["_", "-"],
            "-": [" ", "_"],
            # เพิ่มรูปแบบอื่นๆ ตามที่พบเจอ
        }
        return patterns

    def initialize_embeddings(self):
        """สร้าง embedding vectors สำหรับชื่อที่รู้จัก"""
        # ในอนาคตอาจใช้โมเดล NLP จริง
        # แต่ตอนนี้ใช้วิธีอย่างง่าย
        for name in self.character_db:
            clean_name = self._clean_name(name)
            char_vector = {}
            for i, char in enumerate(clean_name):
                char_vector[char] = char_vector.get(char, 0) + 1
                char_vector[f"pos_{i}_{char}"] = 1  # เก็บตำแหน่งของตัวอักษรด้วย
            self.name_embeddings[name] = char_vector

    def _clean_name(self, name):
        """ทำความสะอาดชื่อเพื่อเปรียบเทียบ โดยใช้ข้อมูลจาก word_fixes ด้วย"""
        if not name:
            return ""

        # ก่อนอื่นตรวจสอบว่ามีการแก้ไขใน word_fixes หรือไม่
        if hasattr(self, "word_fixes") and self.word_fixes:
            # ตรวจสอบทั้งชื่อเต็ม
            if name in self.word_fixes:
                return self.word_fixes[name].replace("!", "").replace(" ", "").lower()

            # ถ้าชื่อลงท้ายด้วย ! หรือ space
            name_clean = name.rstrip("! ")
            if name_clean in self.word_fixes:
                return (
                    self.word_fixes[name_clean]
                    .replace("!", "")
                    .replace(" ", "")
                    .lower()
                )

        # ดำเนินการทำความสะอาดตามปกติ
        name = name.lower().strip()
        replacements = {
            "'": "",
            "`": "",
            " ": "",
            "z": "2",
            "$": "s",
            "0": "o",
            "1": "l",
            ".": "",
            ",": "",
            "!": "",
            "?": "",
        }
        for old, new in replacements.items():
            name = name.replace(old, new)
        return name

    def add_recent_name(self, name):
        """เพิ่มชื่อเข้าประวัติล่าสุด"""
        if not name:
            return

        if name in self.recent_names:
            # ย้ายชื่อที่มีอยู่แล้วขึ้นมาเป็นลำดับแรก
            self.recent_names.remove(name)

        self.recent_names.insert(0, name)

        # ตัดให้เหลือเท่าที่กำหนด
        if len(self.recent_names) > self.max_recent:
            self.recent_names = self.recent_names[: self.max_recent]

    def generate_name_variations(self, name):
        """สร้างรูปแบบชื่อที่อาจเกิดจากข้อผิดพลาด OCR"""
        if not name or len(name) <= 1:
            return [name]

        variations = [name]

        # สร้างรูปแบบที่อาจเกิดจากข้อผิดพลาด OCR
        for i in range(len(name)):
            char = name[i]

            if char in self.correction_patterns:
                for alt_char in self.correction_patterns[char]:
                    # แทนที่ตัวอักษรที่ i ด้วยทางเลือกอื่น
                    var = name[:i] + alt_char + name[i + 1 :]
                    variations.append(var)

        # สร้างรูปแบบโดยลบช่องว่าง
        if " " in name:
            variations.append(name.replace(" ", ""))

        # สร้างรูปแบบโดยเพิ่มช่องว่าง
        if len(name) > 3:
            for i in range(1, len(name) - 1):
                if name[i] not in " -_" and name[i - 1] not in " -_":
                    variations.append(name[:i] + " " + name[i:])

        return variations

    def n_gram_similarity(self, name1, name2, n=2):
        """คำนวณความคล้ายคลึงแบบ n-gram ระหว่างชื่อสองชื่อ"""
        if not name1 or not name2:
            return 0.0

        # ทำความสะอาดก่อน
        name1 = self._clean_name(name1)
        name2 = self._clean_name(name2)

        if name1 == name2:
            return 1.0

        # สร้าง n-grams
        def get_ngrams(text, n):
            return (
                [text[i : i + n] for i in range(len(text) - n + 1)]
                if len(text) >= n
                else [text]
            )

        ngrams1 = get_ngrams(name1, n)
        ngrams2 = get_ngrams(name2, n)

        # หาจำนวน n-grams ที่ซ้ำกัน
        common = set(ngrams1).intersection(set(ngrams2))

        # คำนวณความคล้ายคลึง
        return len(common) / max(len(set(ngrams1)), len(set(ngrams2)))

    def weighted_context_match(self, name, dialogue=None):
        """
        ค้นหาชื่อที่น่าจะตรงกับชื่อที่ได้จาก OCR โดยพิจารณาบริบท
        ใช้หลายปัจจัยในการตัดสินใจ และเพิ่มการใช้ word_fixes
        """
        if not name:
            return None, 0.0

        # เช็คก่อนว่ามีใน word_fixes หรือไม่
        if hasattr(self, "word_fixes") and self.word_fixes and name in self.word_fixes:
            fixed_name = self.word_fixes[name]
            # ตัด ! ออกถ้ามี
            if fixed_name.endswith("!"):
                fixed_name = fixed_name[:-1].strip()

            # เช็คว่า fixed_name มีในฐานข้อมูลหรือไม่
            if fixed_name in self.character_db:
                return fixed_name, 1.0  # คืนค่าด้วยความมั่นใจสูงสุด

        # สร้างรูปแบบอื่นที่อาจเกิดจากข้อผิดพลาด OCR (โค้ดเดิม)
        variations = self.generate_name_variations(name)
        best_match = None
        best_score = 0.0

        # เพิ่มชื่อที่รู้จักในฐานข้อมูลลงในรายการค้นหา
        candidates = list(self.character_db)

        # เพิ่มชื่อที่พบล่าสุดเข้าไปด้วย
        for recent in self.recent_names:
            if recent not in candidates:
                candidates.append(recent)

        # ตรวจสอบกับทุกชื่อที่รู้จัก
        for candidate in candidates:
            for variation in variations:
                # คำนวณความคล้ายคลึงของชื่อ
                name_sim = self.n_gram_similarity(variation, candidate)

                # คำนวณแบบ Levenshtein distance
                edit_sim = self.calculate_name_similarity(variation, candidate)

                # คำนวณคะแนนจากความถี่ในประวัติล่าสุด
                recency_score = 0.0
                if candidate in self.recent_names:
                    # ตำแหน่งที่พบล่าสุดมีคะแนนสูงกว่า
                    recency_score = 0.3 * (
                        1.0
                        - self.recent_names.index(candidate) / len(self.recent_names)
                    )

                # ให้น้ำหนักแต่ละปัจจัย
                total_score = (
                    (0.4 * name_sim) + (0.4 * edit_sim) + (0.2 * recency_score)
                )

                if total_score > best_score and total_score > 0.6:  # กำหนดค่า threshold
                    best_score = total_score
                    best_match = candidate

        return best_match, best_score

    def save_learned_corrections(self, filename="learned_corrections.json"):
        """บันทึกการแก้ไขที่เรียนรู้ลงไฟล์"""
        if hasattr(self, "learned_corrections") and self.learned_corrections:
            try:
                with open(filename, "w", encoding="utf-8") as file:
                    json.dump(
                        self.learned_corrections, file, ensure_ascii=False, indent=2
                    )
                print(
                    f"Saved {len(self.learned_corrections)} learned corrections to {filename}"
                )
            except Exception as e:
                print(f"Error saving learned corrections: {str(e)}")

    def load_learned_corrections(self, filename="learned_corrections.json"):
        """โหลดการแก้ไขที่เรียนรู้จากไฟล์"""
        try:
            if not hasattr(self, "learned_corrections"):
                self.learned_corrections = {}

            if os.path.exists(filename):
                with open(filename, "r", encoding="utf-8") as file:
                    loaded_corrections = json.load(file)
                    self.learned_corrections.update(loaded_corrections)
                print(
                    f"Loaded {len(loaded_corrections)} learned corrections from {filename}"
                )
        except Exception as e:
            print(f"Error loading learned corrections: {str(e)}")

    def calculate_name_similarity(self, name1, name2):
        """
        คำนวณความคล้ายคลึงของชื่อโดยใช้ Levenshtein distance
        คล้ายกับที่มีใน TextCorrector แต่ปรับปรุงให้แม่นยำยิ่งขึ้น
        """
        if not name1 or not name2:
            return 0

        clean_name1 = self._clean_name(name1)
        clean_name2 = self._clean_name(name2)

        if clean_name1 == clean_name2:
            return 1.0

        len1, len2 = len(clean_name1), len(clean_name2)
        if len1 == 0 or len2 == 0:
            return 0

        # สร้าง matrix สำหรับคำนวณ Levenshtein distance
        matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]

        for i in range(len1 + 1):
            matrix[i][0] = i
        for j in range(len2 + 1):
            matrix[0][j] = j

        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                cost = 0 if clean_name1[i - 1] == clean_name2[j - 1] else 1

                # ให้น้ำหนักพิเศษกับการสับสนระหว่างตัวอักษรที่มักเกิดข้อผิดพลาด OCR
                if cost == 1:
                    c1, c2 = clean_name1[i - 1], clean_name2[j - 1]
                    for char, alternatives in self.correction_patterns.items():
                        if (c1 == char and c2 in alternatives) or (
                            c2 == char and c1 in alternatives
                        ):
                            cost = 0.5  # ลดค่า penalty สำหรับความผิดพลาดที่เกิดขึ้นบ่อย

                matrix[i][j] = min(
                    matrix[i - 1][j] + 1,  # deletion
                    matrix[i][j - 1] + 1,  # insertion
                    matrix[i - 1][j - 1] + cost,  # substitution
                )

        # นอกจากนี้ยังตรวจหาการสลับตำแหน่งตัวอักษร (transposition)
        for i in range(1, len1):
            for j in range(1, len2):
                if (
                    clean_name1[i] == clean_name2[j - 1]
                    and clean_name1[i - 1] == clean_name2[j]
                ):
                    matrix[i + 1][j + 1] = min(
                        matrix[i + 1][j + 1], matrix[i - 1][j - 1] + 0.5
                    )  # ใช้ค่า penalty น้อยกว่าการแทนที่

        distance = matrix[len1][len2]
        max_length = max(len1, len2)
        similarity = 1 - (distance / max_length)

        return similarity

    def is_likely_character_name(self, text):
        """ตรวจสอบว่าข้อความน่าจะเป็นชื่อตัวละครหรือไม่"""
        # คล้ายกับที่มีใน TextCorrector แต่เพิ่มความยืดหยุ่น

        if not text:
            return False

        words = text.split()
        first_word = words[0] if words else ""

        # 1. ชื่อตัวละครส่วนใหญ่ขึ้นต้นด้วยตัวพิมพ์ใหญ่
        if not first_word or not (first_word[0].isupper() or first_word[0] in "?*_-"):
            # ยอมรับกรณีพิเศษ เช่น "???", "*something*"
            if not (
                text.startswith("???") or text.startswith("*") or text.startswith("_")
            ):
                return False

        # 2. ตรวจสอบความยาว (ชื่อตัวละครมักไม่ยาวมาก)
        if len(text) > 50:
            return False

        # 3. ตรวจสอบรูปแบบพิเศษ
        special_patterns = ["???", "…", "...", "*", "_"]
        for pattern in special_patterns:
            if text.startswith(pattern):
                return True

        # 4. ความยาวของชื่อต้องสมเหตุสมผล
        if len(text) < 2:
            return False

        # 5. ชื่อตัวละครมักไม่ประกอบด้วยคำทั่วไปเช่น The, A, An
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
        if first_word_lower in common_words:
            # แต่จะยอมรับกรณีที่มีรูปแบบพิเศษ เช่น "The Warrior"
            return len(words) > 1 and all(w[0].isupper() for w in words[1:] if w)

        # 6. ตรวจสอบกับรายชื่อตัวละครที่รู้จัก
        for known_name in self.character_db:
            if self.n_gram_similarity(text, known_name) > 0.7:
                return True

        # 7. ถ้ามีหลายคำ ทุกคำควรขึ้นต้นด้วยตัวพิมพ์ใหญ่หรือเป็นคำเชื่อม
        connecting_words = {"van", "von", "de", "del", "of", "the"}
        if len(words) > 1:
            for word in words[1:]:
                if not word:
                    continue
                if not word[0].isupper() and word.lower() not in connecting_words:
                    return False

        return True

    def enhanced_split_speaker_and_content(self, text, previous_speaker=None):
        """
        ปรับปรุงการแยกชื่อผู้พูดและเนื้อหาให้ยืดหยุ่นมากขึ้น
        รองรับการใช้ word_fixes และบริบทจากบทสนทนาก่อนหน้า

        Args:
            text: ข้อความที่ต้องการแยก
            previous_speaker: ชื่อผู้พูดก่อนหน้า (ถ้ามี)

        Returns:
            tuple: (speaker, content, dialogue_type)
        """
        import re
        from enum import Enum

        # ใช้ DialogueType จาก text_corrector
        class DialogueType(Enum):
            NORMAL = "normal"
            CHARACTER = "character"
            CHOICE = "choice"
            SYSTEM = "system"

        if not text:
            return None, "", DialogueType.NORMAL

        # 1. ตรวจสอบว่ามีการแก้ไขเต็มรูปประโยคใน word_fixes หรือไม่
        if hasattr(self, "word_fixes") and text in self.word_fixes:
            fixed_text = self.word_fixes[text]
            if fixed_text == "???":
                return "???", "", DialogueType.CHARACTER

        # 2. จัดการกรณีพิเศษ
        special_cases = ["22", "22?", "222", "222?", "???"]
        if text.strip() in special_cases:
            return "???", "", DialogueType.CHARACTER

        # 3. ตรวจสอบรูปแบบที่มีเครื่องหมายคั่นชัดเจน
        content_separators = [": ", " - ", " – ", " : ", ": ", "- ", "– "]

        for separator in content_separators:
            if separator in text:
                parts = text.split(separator, 1)
                if len(parts) == 2:
                    potential_speaker = parts[0].strip()
                    content = parts[1].strip()

                    # ตรวจสอบว่ามีการแก้ไขใน word_fixes หรือไม่
                    if (
                        hasattr(self, "word_fixes")
                        and potential_speaker in self.word_fixes
                    ):
                        fixed_speaker = self.word_fixes[potential_speaker]
                        # ตัด ! ออกถ้ามี
                        if fixed_speaker.endswith("!"):
                            fixed_speaker = fixed_speaker[:-1].strip()

                        # เช็คว่ามีในฐานข้อมูลหรือไม่
                        if fixed_speaker in self.character_db:
                            return fixed_speaker, content, DialogueType.CHARACTER
                        elif fixed_speaker.startswith("?"):
                            return "???", content, DialogueType.CHARACTER

                    # ตรวจสอบว่า potential_speaker น่าจะเป็นชื่อตัวละครหรือไม่
                    if self.is_likely_character_name(potential_speaker):
                        # ตรวจสอบกับชื่อที่รู้จัก
                        match, score = self.weighted_context_match(potential_speaker)

                        if match and score > 0.7:
                            # พบชื่อที่คล้ายในฐานข้อมูล
                            return match, content, DialogueType.CHARACTER
                        elif potential_speaker.startswith("?"):
                            # กรณีชื่อลึกลับ
                            return "???", content, DialogueType.CHARACTER
                        else:
                            # ชื่อใหม่ที่น่าจะเป็นชื่อตัวละคร
                            return potential_speaker, content, DialogueType.CHARACTER

        # 4. ตรวจสอบรูปแบบพิเศษ - ไม่มีตัวคั่น แต่น่าจะมีชื่อตัวละคร
        # เช่น "Character name Dialogue text..." โดยไม่มี ":"
        words = text.split()

        if len(words) >= 3:  # ต้องมีอย่างน้อย 3 คำ (ชื่อ + ข้อความ)
            # ทดลองตัดเป็นชื่อ 1-2 คำ
            for word_count in [1, 2]:
                if len(words) <= word_count:
                    continue

                potential_speaker = " ".join(words[:word_count])

                # ตรวจสอบการแก้ไขใน word_fixes
                if hasattr(self, "word_fixes") and potential_speaker in self.word_fixes:
                    fixed_speaker = self.word_fixes[potential_speaker]
                    # ตัด ! ออกถ้ามี
                    if fixed_speaker.endswith("!"):
                        fixed_speaker = fixed_speaker[:-1].strip()

                    if fixed_speaker in self.character_db:
                        content = " ".join(words[word_count:])
                        return fixed_speaker, content, DialogueType.CHARACTER

                # ตรวจสอบว่า potential_speaker น่าจะเป็นชื่อตัวละครหรือไม่
                if self.is_likely_character_name(potential_speaker):
                    # ตรวจสอบกับชื่อที่รู้จัก
                    match, score = self.weighted_context_match(potential_speaker)

                    if match and score > 0.85:  # ต้องการความแม่นยำสูงมากในกรณีนี้
                        content = " ".join(words[word_count:])
                        return match, content, DialogueType.CHARACTER

        # 5. ใช้ชื่อจากบทสนทนาก่อนหน้า (ถ้ามี)
        if previous_speaker and self.is_likely_character_name(previous_speaker):
            # ตรวจสอบว่าข้อความปัจจุบันต่อเนื่องจากผู้พูดคนเดิมหรือไม่
            if len(self.recent_names) > 0 and previous_speaker == self.recent_names[0]:
                # ถ้าเป็นผู้พูดเดียวกับครั้งล่าสุด ให้ถือว่าเป็นข้อความต่อเนื่อง
                return previous_speaker, text, DialogueType.CHARACTER

        # 6. ถ้าไม่สามารถระบุชื่อผู้พูดได้ ให้ถือเป็นข้อความทั่วไป
        return None, text.strip(), DialogueType.NORMAL

    def evaluate_name_quality(self, name):
        """
        ประเมินคุณภาพของชื่อที่ OCR พบด้วยเกณฑ์หลายข้อ สำหรับ H-game context

        Args:
            name: ชื่อที่ต้องการตรวจสอบ

        Returns:
            float: คะแนนคุณภาพ (0.0-1.0) โดย 1.0 คือมั่นใจสูงว่าเป็นชื่อจริง
        """
        if not name or len(name) < 2:
            return 0.0

        score = 0.0

        # 1. ตรวจสอบขนาดชื่อ (ไม่สั้นหรือยาวเกินไป)
        length = len(name)
        if 2 <= length <= 30:
            score += 0.2
        elif length > 30:
            score -= 0.1  # ชื่อยาวเกินไปอาจเป็นประโยคที่ OCR ผิดพลาด

        # 2. ตรวจสอบอักขระที่อาจเกิดจาก OCR ผิดพลาด
        suspicious_chars = "~!@#$%^&*+={}[]|\<>?/;0123456789"
        suspicious_count = sum(1 for c in name if c in suspicious_chars)

        if suspicious_count == 0:
            score += 0.2
        else:
            score -= 0.1 * min(suspicious_count, 5)  # ลดคะแนนแต่ไม่เกิน 0.5

        # 3. ตรวจสอบรูปแบบการเขียนชื่อคน (ขึ้นต้นด้วยตัวใหญ่)
        if name[0].isupper():
            score += 0.2

        # 4. ตรวจสอบกับชื่อที่รู้จักในฐานข้อมูล (character_db)
        best_match = None
        best_similarity = 0

        for known_name in self.character_db:
            similarity = self.calculate_name_similarity(name, known_name)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = known_name

        # ถ้าคล้ายกับชื่อที่รู้จักมาก จะเพิ่มคะแนน
        if best_similarity > 0.8:
            score += 0.4
        elif best_similarity > 0.7:
            score += 0.2
        elif best_similarity > 0.5:
            score += 0.1

        # 5. (ลบส่วนตรวจสอบ FFXIV ออก) ตรวจสอบรูปแบบทั่วไปอื่นๆ ที่อาจพบในชื่อเกม
        # เช่น การมีช่องว่าง หรือการใช้อักขระพิเศษที่สมเหตุสมผลในชื่อ (เช่น -)
        if ' ' in name and all(word.isalpha() or '-' in word for word in name.split()):
             score += 0.1 # เพิ่มคะแนนเล็กน้อยถ้ามีรูปแบบชื่อที่ดูสมเหตุสมผล

        # ปรับคะแนนให้อยู่ระหว่าง 0.0-1.0
        return max(0.0, min(1.0, score))

    def learn_correction(self, wrong_name, correct_name):
        """
        เรียนรู้รูปแบบการแก้ไขชื่อจากการ force translate และบันทึกลงไฟล์
        """
        if not wrong_name or not correct_name:
            return

        # เก็บคู่การแก้ไขลงใน dict
        if not hasattr(self, "learned_corrections"):
            self.learned_corrections = {}

        self.learned_corrections[wrong_name] = correct_name

        # วิเคราะห์การเปลี่ยนแปลงเพื่อสร้างกฎใหม่
        clean_wrong = self._clean_name(wrong_name)
        clean_correct = self._clean_name(correct_name)

        # หาจุดที่แตกต่างกัน
        i = 0
        while (
            i < min(len(clean_wrong), len(clean_correct))
            and clean_wrong[i] == clean_correct[i]
        ):
            i += 1

        if i < min(len(clean_wrong), len(clean_correct)):
            # พบจุดที่แตกต่าง
            wrong_char = clean_wrong[i : i + 1]
            correct_char = clean_correct[i : i + 1]

            # เพิ่มลงในรูปแบบการแก้ไข (correction_patterns)
            if wrong_char in self.correction_patterns:
                if correct_char not in self.correction_patterns[wrong_char]:
                    self.correction_patterns[wrong_char].append(correct_char)
            else:
                self.correction_patterns[wrong_char] = [correct_char]

            # ทำในทางกลับกันด้วย
            if correct_char in self.correction_patterns:
                if wrong_char not in self.correction_patterns[correct_char]:
                    self.correction_patterns[correct_char].append(wrong_char)
            else:
                self.correction_patterns[correct_char] = [wrong_char]

        # บันทึกการเรียนรู้หลังจากทุกครั้งที่เรียนรู้
        self.save_learned_corrections()
