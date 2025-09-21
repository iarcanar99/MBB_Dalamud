# translator_gemini.py
import os
from dotenv import load_dotenv
import re
import tkinter as tk
from tkinter import messagebox
import json
import difflib
import time
import logging
from enum import Enum
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from text_corrector import TextCorrector, DialogueType
from dialogue_cache import DialogueCache

# เพิ่มการ import EnhancedNameDetector ถ้ามี
try:
    from enhanced_name_detector import EnhancedNameDetector

    HAS_ENHANCED_DETECTOR = True
except ImportError:
    HAS_ENHANCED_DETECTOR = False

load_dotenv()


class TranslatorGemini:
    def __init__(self, settings=None):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            # เพิ่มการแจ้งเตือนที่ชัดเจนเมื่อไม่พบ API Key
            error_msg = "GEMINI_API_KEY not found in .env file"
            logging.error(error_msg)
            messagebox.showerror(
                "API Key Error", f"{error_msg}\nPlease add your API key to .env file"
            )
            raise ValueError(error_msg)

        # Initialize Gemini API
        genai.configure(api_key=self.api_key)

        # Initialize default values first
        self.model_name = "gemini-2.0-flash-lite"
        self.max_tokens = 500
        self.temperature = 0.7
        self.top_p = 0.9
        self.current_role_mode = "rpg_general"

        # ใช้ settings object ถ้ามี
        if settings:
            api_params = settings.get_api_parameters()
            self.model_name = api_params.get("model", self.model_name)
            self.max_tokens = api_params.get("max_tokens", self.max_tokens)
            self.temperature = api_params.get("temperature", self.temperature)
            self.top_p = api_params.get("top_p", self.top_p)
            self.current_role_mode = api_params.get("role_mode", self.current_role_mode)
        else:
            # ถ้าไม่มี settings ให้โหลดจากไฟล์
            try:
                with open("settings.json", "r") as f:
                    settings_data = json.load(f)
                    api_params = settings_data.get("api_parameters", {})
                    self.model_name = api_params.get("model", "gemini-2.0-flash-lite")
                    self.max_tokens = api_params.get("max_tokens", 500)
                    self.temperature = api_params.get("temperature", 0.7)
                    self.top_p = api_params.get("top_p", 0.9)
                    self.current_role_mode = api_params.get("role_mode", "rpg_general")
            except (FileNotFoundError, json.JSONDecodeError):
                self.model_name = "gemini-2.0-flash-lite"
                self.max_tokens = 500
                self.temperature = 0.7
                self.top_p = 0.9
                self.current_role_mode = "rpg_general"
                logging.warning("Could not load settings.json, using default values")

        # ตั้งค่า safety settings - ปิดการบล็อกเนื้อหาเพื่อให้แปล H-game ได้
        self.safety_settings = [
            {
                "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
        ]

        # Initialize Gemini model
        genai_model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={
                "max_output_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
            },
            safety_settings=self.safety_settings,
        )
        self.model = genai_model

        self.cache = DialogueCache()
        self.last_translations = {}
        self.character_names_cache = set()
        self.text_corrector = TextCorrector()
        self.load_npc_data()
        self.load_example_translations()

        # Session-based character name cache for consistency
        self.session_character_names = {}  # {original_name: translated_name}
        self.session_speaker_count = 0     # Track session activity
        self.max_session_names = 50        # Prevent memory growth
        self.cache_hits = 0                # Track cache performance
        self.cache_misses = 0              # Track cache performance

        # ดูว่าสามารถใช้ EnhancedNameDetector ได้หรือไม่
        self.enhanced_detector = None
        if HAS_ENHANCED_DETECTOR:
            try:
                self.enhanced_detector = EnhancedNameDetector(
                    self.character_names_cache
                )
                logging.info("Initialized EnhancedNameDetector successfully")
            except Exception as e:
                logging.warning(f"Failed to initialize EnhancedNameDetector: {e}")
                self.enhanced_detector = None

    def get_current_parameters(self):
        """Return current translation parameters"""
        # สำหรับ Gemini จะแสดงชื่อรุ่นที่ง่ายต่อการอ่าน
        displayed_model = self.model_name
        if self.model_name == "gemini-1.5-pro":
            displayed_model = "gemini-1.5-pro"
        elif self.model_name == "gemini-1.5-flash":
            displayed_model = "gemini-1.5-flash"

        return {
            "model": self.model_name,
            "displayed_model": displayed_model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }

    def load_npc_data(self):
        """Load character data, lore, styles, and specific H-game terms from NPC.json."""
        try:
            with open("NPC.json", "r", encoding="utf-8") as file:
                npc_data = json.load(file)
                self.character_data = npc_data["main_characters"]
                self.context_data = npc_data["lore"]
                self.character_styles = npc_data["character_roles"]

                # โหลด word_fixes ถ้ามี
                if "word_fixes" in npc_data:
                    self.word_fixes = npc_data["word_fixes"]
                    logging.info(
                        f"Loaded {len(self.word_fixes)} word fixes from NPC.json"
                    )
                else:
                    self.word_fixes = {}

                # Update character_names_cache
                self.character_names_cache = set()
                self.character_names_cache.add("???")

                # Load main characters
                for char in self.character_data:
                    self.character_names_cache.add(char["firstName"])
                    if char["lastName"]:
                        self.character_names_cache.add(
                            f"{char['firstName']} {char['lastName']}"
                        )

                # Load NPCs
                for npc in npc_data["npcs"]:
                    self.character_names_cache.add(npc["name"])

                logging.info("TranslatorGemini: Loaded NPC.json successfully")

        except FileNotFoundError:
            raise FileNotFoundError("NPC.json file not found")
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON in NPC.json")

    def load_example_translations(self):
        self.example_translations = {
            "'Tis": "ช่างเป็น...",
            "'I do": "ฉันเข้าใจ",
            "'do": "ฉันเข้าใจ",
            "'Twas": "มันเคยเป็น...",
            "Nay": "หามิได้",
            "Aye": "นั่นสินะ, นั่นแหล่ะ, เป็นเช่นนั้น",
            "Mayhaps": "บางที...",
            "Hm...": "อืม...",
            "Wait!": "เดี๋ยวก่อน!",
            "My friend...": "สหายข้า...",
            "Tataru?": "Tataru เหรอ?",
            "Estinien!": "Estinien!",
            "sigh": "เฮ่อ..",
            "Hmph.": "ฮึ่ม.",
            # ลบคอมเมนต์ตัวอย่างเดิมที่ไม่ใช้แล้ว
        }

    def update_parameters(
        self, model=None, max_tokens=None, temperature=None, top_p=None, **kwargs
    ):
        """อัพเดทค่าพารามิเตอร์สำหรับการแปล"""
        try:
            old_params = {
                "model": self.model_name,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
            }

            changes = []

            if model is not None:
                # --- แก้ไขตรงนี้: เพิ่ม gemini-2.0-flash เข้าไปในลิสต์ ---
                valid_models = [
                    "gemini-1.5-pro",
                    "gemini-1.5-flash",
                    "gemini-2.0-flash-lite",
                    "gemini-2.0-flash",  # เพิ่มชื่อโมเดลใหม่ของคุณที่นี่
                ]
                # -----------------------------------------------------------
                if model not in valid_models:
                    raise ValueError(
                        f"Invalid model for Gemini translator. Must be one of: {', '.join(valid_models)}"
                    )
                self.model_name = model
                changes.append(f"Model: {old_params['model']} -> {model}")

            if max_tokens is not None:
                if not (100 <= max_tokens <= 2000):  # Gemini supports up to 2048 tokens
                    raise ValueError(
                        f"Max tokens must be between 100 and 2000, got {max_tokens}"
                    )
                self.max_tokens = max_tokens
                changes.append(
                    f"Max tokens: {old_params['max_tokens']} -> {max_tokens}"
                )

            if temperature is not None:
                if not (0.0 <= temperature <= 1.0):  # Gemini uses 0-1 scale
                    raise ValueError(
                        f"Temperature must be between 0.0 and 1.0, got {temperature}"
                    )
                self.temperature = temperature
                changes.append(
                    f"Temperature: {old_params['temperature']} -> {temperature}"
                )

            if top_p is not None:
                if not (0.0 <= top_p <= 1.0):
                    raise ValueError(f"Top P must be between 0.0 and 1.0, got {top_p}")
                self.top_p = top_p
                changes.append(f"Top P: {old_params['top_p']} -> {top_p}")

            # Re-initialize the model with new parameters
            logging.info(
                f"Recreating Gemini model with parameters: {self.model_name}, max_tokens={self.max_tokens}, temp={self.temperature}"
            )
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config={
                    "max_output_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                },
                safety_settings=self.safety_settings,
            )
            logging.info(f"Successfully recreated Gemini model: {self.model}")

            if changes:
                logging.info("\n=== Gemini Parameters Updated ===")
                for change in changes:
                    logging.info(change)
                logging.info(f"Current model: {self.model_name}")
                logging.info("==========================\n")

            return changes

        except Exception as e:
            error_msg = f"Error updating Gemini parameters: {str(e)}"
            logging.error(error_msg)
            raise ValueError(error_msg)

    def set_role_mode(self, role_mode):
        """Set the current role mode for translation"""
        valid_roles = ["rpg_general", "adult_enhanced"]
        if role_mode in valid_roles:
            self.current_role_mode = role_mode
            logging.info(f"Role mode set to: {role_mode}")
        else:
            logging.warning(
                f"Invalid role mode: {role_mode}, keeping current: {self.current_role_mode}"
            )

    def get_relevant_names(self, text):
        """Extract only character names mentioned in the current text (OPTIMIZATION)"""
        relevant_names = set()
        text_lower = text.lower()

        # Check for names that appear in the text
        for name in self.character_names_cache:
            if name.lower() in text_lower:
                relevant_names.add(name)

        # Always include essential names that might appear frequently
        essential_names = {
            "Y'shtola", "Alphinaud", "Alisaie", "Wuk Lamat", "???",
            "Estinien", "G'raha Tia", "Thancred", "Urianger", "Krile",
            "Emet-Selch", "Hythlodaeus", "Venat", "Meteion", "Zenos",
            "Koana", "Zoraal Ja", "Gulool Ja", "Sphene", "Otis"
        }
        for name in essential_names:
            if name in self.character_names_cache:
                relevant_names.add(name)

        # Limit to maximum 20 names to control token usage (increased for better coverage)
        # Prioritize essential names first, then detected names
        essential_in_relevant = [name for name in essential_names if name in relevant_names]
        other_names = [name for name in relevant_names if name not in essential_names]

        # Combine with essential names first to ensure they're always included
        prioritized_names = essential_in_relevant + other_names
        return prioritized_names[:20]

    def get_relevant_lore_terms(self, text, speaker=None):
        """Extract only lore terms that might be relevant to current text (OPTIMIZATION)"""
        relevant_terms = {}
        text_lower = text.lower()

        # Priority 1: Direct keyword matches
        for term, explanation in self.context_data.items():
            if term.lower() in text_lower:
                relevant_terms[term] = explanation

        # Priority 2: Character-specific lore (if we know the speaker)
        if speaker and len(relevant_terms) < 5:
            character_related_terms = ["Warrior of Light", "Scion", "Crystal", "Eorzea"]
            for term in character_related_terms:
                if term in self.context_data and len(relevant_terms) < 5:
                    relevant_terms[term] = self.context_data[term]

        # Priority 3: Essential game terms (always include if space allows)
        essential_terms = ["Warrior of Light", "Eorzea"]
        for term in essential_terms:
            if (
                term in self.context_data
                and term not in relevant_terms
                and len(relevant_terms) < 3
            ):
                relevant_terms[term] = self.context_data[term]

        return relevant_terms

    def count_tokens_estimate(self, text):
        """Rough token estimation for monitoring (OPTIMIZATION)"""
        # Rough estimate: 1 token ≈ 4 characters for mixed EN/TH
        return len(text) // 4

    def get_system_prompt(self, role_mode=None):
        """Get system prompt based on current role mode"""
        if role_mode is None:
            role_mode = self.current_role_mode

        if role_mode == "adult_enhanced":
            return self.get_adult_enhanced_prompt()
        else:
            return self.get_rpg_general_prompt()

    def get_rpg_general_prompt(self):
        """Text Hook optimized RPG translation prompt for Final Fantasy XIV"""
        return (
            "You are a professional translator specializing in Final Fantasy XIV text hook localization. "
            "You receive precise, complete game text directly from the game engine with perfect accuracy. "
            "Translate this English text to Thai following these requirements:\n\n"
            "**TEXT HOOK ADVANTAGES:**\n"
            "- Perfect text accuracy\n"
            "- Complete dialogue context\n"
            "- Real-time character identification\n"
            "- Precise message boundaries\n\n"
            "**TRANSLATION REQUIREMENTS:**\n"
            "1. **Complete Translation**: Translate ALL content completely - text hook provides perfect input, expect perfect output\n"
            "2. **Character Fidelity**: Maintain the speaker's tone and personality as described in 'Character's style' section. This is the highest priority.\n"
            "3. **Name Preservation (CRITICAL)**: NEVER translate character names, place names, or special terms from the database. Character names must ALWAYS remain in English exactly as provided, even when mentioned in dialogue. Examples: Y'shtola stays Y'shtola, Estinien stays Estinien, G'raha Tia stays G'raha Tia.\n"
            "4. **Lore Integration**: Use Thai explanations from 'Special terms' section below instead of direct translation\n"
            "5. **Default Tone - Modern Game Dialogue**: The default translation style is modern, natural Thai suitable for a video game script. This means clear, direct language. This style should ONLY be changed if the 'Character's style' explicitly demands an archaic or unique tone.\n"
            "6. **ABSOLUTE PROHIBITION (CRITICAL RULE)**: Under NO circumstances are you to use the following modern polite particles: 'ค่ะ', 'คะ', 'ครับ', 'ดิฉัน', 'นะคะ', 'นะครับ', 'ข้าพเจ้า'. Using these words is a critical error that completely destroys the game's atmosphere. If you use 'ข้าพเจ้า' in any translation, it is an immediate failure. Use appropriate pronouns like 'ชั้น', 'ฉัน', 'ข้า', 'เรา' instead. Politeness must be conveyed through respectful word choices and sentence structure ONLY, not by adding these particles.\n"
            "7. Pronoun Selection Guidelines (Context and Personality Based):\n"
            "   - For serious conversations about plans/stories/important matters: Use 'คุณ' or 'เจ้า' instead of 'แก' for appropriateness\n"
            "   - Follow Character's style as main priority:\n"
            "     • Characters described as 'สุภาพ', 'นุ่มนวล', 'อ่อนโยน' should avoid 'แก', use 'คุณ' or 'เจ้า'\n"
            "     • Characters described as 'เฟียส', 'ห้าว', 'หัวร้อน', 'คำพูดขวานผ่าซาก' can use 'เจ้า' normally and 'แก' when challenging/arguing\n"
            "     • Characters described as 'ก้าวร้าว', 'ดุดัน', 'หยาบ' can use 'แก' or 'เอ็ง'\n"
            "   - Consider context appropriateness based on situation and emotional tone\n"
            "8. **Profanity and Emotional Expression (Anime Style)**: Strictly avoid harsh, vulgar pronouns like 'กู' and 'มึง'. However, to capture strong emotions accurately, using expressive exclamations or mild curses like 'แม่ง', 'เชี่ย!', 'บ้าเอ๊ย!' is PERMITTED, but ONLY if the original English text conveys frustration, anger, or shock. The goal is to achieve a vivid, 'anime-style' localization that is expressive without being overly vulgar.\n"
            "9. **Output Format**: Return ONLY the Thai translation - no English text, explanations, or formatting\n\n"
            f"Protected names (use exactly as written): {', '.join(self.character_names_cache)}\n\n"
            "Special terms (use these Thai explanations):\n"
        )

    def get_adult_enhanced_prompt(self):
        """Adult enhanced translation prompt with explicit content support"""
        return (
            "You are an expert translator specializing in translating adult visual novels and mature content from English to Thai. "
            "Your expertise includes handling explicit sexual content, intimate scenes, and mature themes with accuracy and appropriate language.\n"
            "Translate the following English text into Thai, focusing on these enhanced principles:\n\n"
            "ENHANCED GUIDELINES:\n"
            "1. **Bold & Complete Translation:** Translate ALL content completely and directly. "
            "Do NOT censor, omit, or tone down explicit content. Be bold and straightforward with sexual terminology.\n"
            "2. **Mature Thai Expression:** Use appropriate Thai sexual vocabulary and intimate expressions. "
            "Choose words that convey the right level of explicitness - from sensual to graphic as needed.\n"
            "3. **Emotional Intensity:** Capture the full emotional and physical intensity of intimate scenes. "
            "Use expressive language that conveys desire, passion, pleasure, and other mature emotions accurately.\n"
            "4. **Natural Intimacy:** Translate sexual content to sound natural and appealing in Thai, "
            "not clinical or awkward. Use terms that enhance rather than diminish the erotic atmosphere.\n"
            "5. **Contemporary Thai as a Base**: Translate using natural, easy-to-understand Thai, like dialogue in modern RPGs (e.g., Final Fantasy XVI, Persona 5). The primary goal is natural-sounding conversation. Prioritize the 'Character's style' data; if a character needs to sound archaic or formal, that data will specify it. Otherwise, default to a modern, clear tone.\n"
            "6. **Natural Particles and Pronouns**: To make conversations sound authentic, the use of 'ครับ/ค่ะ' is PERMITTED and encouraged for polite or formal situations, based on the character's personality. Avoid overly archaic or overly casual particles unless specified by the character's style.\n"
            "   - **Still Forbidden**: 'เจ้าค่ะ', 'เพคะ' (too historical); 'จ้ะ', 'ฮะ' (can be too casual and break immersion).\n"
            "   - Pronouns should be chosen based on context and 'Character's style' for natural interactions, not rigid rules.\n"
            "7. **Output Format**: Return ONLY the Thai translation - no English text, explanations, or formatting\n\n"
            "8. **RPG Fantasy Tone - STRICTLY FORBIDDEN:** Even in adult content, maintain the fantasy RPG atmosphere. DO NOT USE modern casual particles like 'ครับ/ค่ะ/นะคะ/นะครับ/ดิฉัน/เจ้าค่ะ/เพคะ/จ้ะ/ฮะ' that would break immersion in a fantasy setting. This is a hard rule.\n"
            "9. **Pure Output:** Return ONLY the Thai translation with full adult content intact.\n\n"
            "Remember: Your role is to provide authentic, unfiltered translations that preserve the full adult nature of the content. "
            "Do not shy away from explicit terminology - embrace it for accurate, engaging translation while maintaining the fantasy RPG setting.\n\n"
        )

    def is_translation_complete(self, original_text, translated_text):
        """ตรวจสอบว่าการแปลสมบูรณ์หรือไม่โดยเปรียบเทียบความยาวและเนื้อหาแบบยืดหยุ่น (เหมาะกับภาษาไทย)

        Args:
            original_text: ข้อความต้นฉบับ
            translated_text: ข้อความที่แปลแล้ว

        Returns:
            bool: True ถ้าการแปลดูเหมือนจะสมบูรณ์, False ถ้าอาจจะไม่สมบูรณ์
        """
        # กรณีไม่มีข้อความ
        if not original_text or not translated_text:
            return False

        # กรณีชื่อตัวละครพิเศษ - ให้ผ่านเสมอ
        if translated_text.strip() in ["???", "Y'shtola", "Yshtola"]:
            return True

        # กรณีข้อความต้นฉบับเป็นเลข 2 หรือรูปแบบที่เกี่ยวข้องกับ ???
        if (
            re.match(r"^2+\??$", original_text.strip())
            or original_text.strip() == "???"
        ):
            return translated_text.strip() == "???"

        # แยกชื่อผู้พูดออกจากเนื้อหา
        original_content = original_text
        translated_content = translated_text

        # ตรวจสอบและแยกชื่อผู้พูดออก
        if ":" in original_text:
            parts = original_text.split(":", 1)
            if len(parts) == 2:
                original_content = parts[1].strip()

        if ":" in translated_text:
            parts = translated_text.split(":", 1)
            if len(parts) == 2:
                translated_content = parts[1].strip()

        # คำนวณจำนวนคำ (สำหรับภาษาอังกฤษ) และความยาวตัวอักษร (สำหรับภาษาไทย)
        original_words = original_content.split()
        original_char_length = len(original_content)
        translated_words = translated_content.split()
        translated_char_length = len(translated_content)

        # ข้อความสั้นมาก (1-3 คำ) ถือว่าสมบูรณ์เสมอหากมีตัวอักษร
        if len(original_words) <= 3 and translated_char_length >= 2:
            return True

        # ถ้าเป็นเพียงชื่อ หรือคำทักทาย (5 คำหรือน้อยกว่า) ให้ผ่านง่ายๆ
        if len(original_words) <= 5 and translated_char_length >= 5:
            return True

        # สำหรับภาษาไทย ให้ใช้ความยาวตัวอักษรเทียบกัน (เพราะคำไทยสั้นกว่าภาษาอังกฤษมาก)
        # สัดส่วนความยาวตัวอักษรที่เหมาะสมสำหรับการแปลอังกฤษเป็นไทยประมาณ 1:0.6
        char_ratio = translated_char_length / max(1, original_char_length)

        # ถ้าสัดส่วนตัวอักษรต่ำกว่า 0.3 (30%) ของต้นฉบับ อาจจะไม่สมบูรณ์
        # แต่ตรวจสอบเฉพาะข้อความที่มีความยาวมากกว่า 50 ตัวอักษรเท่านั้น
        if original_char_length > 50 and char_ratio < 0.3:
            return False

        # ข้อความสั้นไม่จำเป็นต้องตรวจสอบวรรคตอน
        if original_char_length <= 50:
            return True

        # ตรวจสอบการตัดท้ายประโยค
        if translated_content.strip().endswith(("-", "...")):
            # อนุญาตให้จบด้วย ... ได้ แต่ไม่อนุญาตให้จบด้วย -
            if translated_content.strip().endswith("-"):
                return False
            # ถ้าจบด้วย ... แต่ต้นฉบับไม่ได้จบด้วย ... ให้ตรวจสอบความยาวเพิ่มเติม
            if not original_content.strip().endswith("...") and char_ratio < 0.5:
                return False

        # ผ่านทุกเงื่อนไข ถือว่าสมบูรณ์
        return True

    def translate(
        self, text, source_lang="English", target_lang="Thai", is_choice_option=False
    ):
        """
        แปลข้อความพร้อมจัดการบริบทของตัวละคร
        Args:
            text: ข้อความที่ต้องการแปล
            source_lang: ภาษาต้นฉบับ (default: English)
            target_lang: ภาษาเป้าหมาย (default: Thai)
            is_choice_option: เป็นข้อความตัวเลือกหรือไม่ (default: False)
        Returns:
            str: ข้อความที่แปลแล้ว
        """
        try:
            if not text:
                logging.warning("Empty text received for translation")
                return ""

            # ใส่ try-except เพื่อป้องกันกรณี split_speaker_and_content เกิด error
            try:
                # ใช้ text_corrector instance ที่สร้างไว้แล้ว
                speaker, content, dialogue_type = (
                    self.text_corrector.split_speaker_and_content(text)
                )
            except (TypeError, ValueError, AttributeError) as e:
                # กรณีที่ split_speaker_and_content มีปัญหา หรือส่งค่า None กลับมา
                logging.warning(
                    f"Error splitting text content: {e}, treating as normal text"
                )
                speaker = None
                content = text
                dialogue_type = None

            # ตรวจสอบ word_fixes สำหรับข้อความทั้งหมด
            if hasattr(self, "word_fixes") and text.strip() in self.word_fixes:
                fixed_text = self.word_fixes[text.strip()]
                if fixed_text == "???":
                    return "???"

            # ตรวจสอบกรณีพิเศษสำหรับเลข 2 และ ???
            if text.strip() in ["2", "2?", "22", "22?", "222", "222?", "???"]:
                return "???"

            # กรณีพิเศษเมื่อข้อความประกอบด้วยเลข 2 ซ้ำกันหลายครั้ง (2, 22, 222, 2222, ฯลฯ)
            if re.match(r"^2+\??$", text.strip()):
                return "???"

            # ใช้ EnhancedNameDetector ถ้ามี เพื่อตรวจสอบเพิ่มเติม
            if self.enhanced_detector:
                try:
                    # ตรวจสอบว่าข้อความอาจเป็นชื่อตัวละครหรือไม่
                    speaker, content, detected_type = (
                        self.enhanced_detector.enhanced_split_speaker_and_content(text)
                    )
                    if detected_type == DialogueType.CHARACTER and speaker == "???":
                        return "???"
                except Exception as e:
                    logging.warning(f"Error using EnhancedNameDetector: {e}")

            # ตรวจสอบว่าเป็นข้อความตัวเลือกหรือไม่
            if is_choice_option:
                # ถ้า MBB บอกว่าเป็น choice ให้เรียก translate_choice ทันที
                logging.info(f"Choice option flag is True, calling translate_choice")
                return self.translate_choice(text)
            else:
                # ถ้า MBB ไม่บอกว่าเป็น choice ให้ตรวจสอบเองอีกครั้ง
                try:
                    is_choice, prompt_part, choices = self.is_similar_to_choice_prompt(
                        text
                    )
                    if is_choice:
                        logging.info(
                            f"Internal choice detection found choice, calling translate_choice"
                        )
                        return self.translate_choice(text)
                except Exception as choice_err:
                    logging.warning(f"Error checking choice prompt: {choice_err}")

            # กรณีมีชื่อผู้พูด
            if dialogue_type == DialogueType.CHARACTER and speaker:
                # กรณีพิเศษสำหรับ ???
                if speaker.startswith("?"):
                    speaker = "???"

                # Check session cache for consistent character names (EXACT MATCH ONLY)
                try:
                    # Normalize speaker for lookup - EXACT MATCH ONLY to avoid substring conflicts
                    normalized_speaker = speaker.lower().strip()

                    # CRITICAL: Use exact string match to prevent "Gulool Ja" vs "Gulool Ja Ja" conflicts
                    if normalized_speaker in self.session_character_names:
                        character_name = self.session_character_names[normalized_speaker]
                        self.cache_hits += 1
                        logging.debug(f"[NAME CACHE] Cache HIT: {speaker} -> {character_name}")
                    else:
                        character_name = speaker  # Use original logic if not cached
                        self.cache_misses += 1
                        logging.debug(f"[NAME CACHE] Cache MISS: {speaker} (will translate)")
                except Exception as e:
                    logging.warning(f"Name cache lookup error: {e}, falling back to original logic")
                    character_name = speaker  # Fallback to original behavior
                dialogue = content

                # ตรวจสอบ cache สำหรับการแปล
                if (
                    dialogue in self.last_translations
                    and character_name == self.cache.get_last_speaker()
                ):
                    translated_dialogue = self.last_translations[dialogue]
                    return f"{character_name}: {translated_dialogue}"

                # 1. ดึงข้อมูลพื้นฐานของตัวละคร
                character_info = self.get_character_info(character_name)
                context = ""
                if character_info:
                    context = (
                        f"Character: {character_info['firstName']}, "
                        f"Gender: {character_info['gender']}, "
                        f"Role: {character_info['role']}, "
                        f"Relationship: {character_info['relationship']}"
                    )
                elif character_name == "???":
                    context = "Character: Unknown, Role: Mystery character"

                # 2. ดึงรูปแบบการพูด
                character_style = self.character_styles.get(character_name, "")
                if not character_style and character_name == "???":
                    character_style = (
                        "พูดจาลึกลับและสร้างความสงสัย ใช้คำพูดแบบไม่ระบุเพศ หลีกเลี่ยงคำสรรพนามที่บ่งบอกเพศ "
                        "ใช้น้ำเสียงที่ปริศนาและทำให้คนฟังสงสัยในตัวตน เช่น 'เรา' แทน 'ฉัน' หรือ 'ข้า' "
                        "และใช้คำพูดที่กำกวม สร้างบรรยากาศลึกลับ"
                    )

                self.cache.add_speaker(character_name)

            else:
                # กรณีข้อความทั่วไป
                dialogue = text
                character_name = ""
                context = ""
                character_style = ""

            # สร้าง prompt และแปล
            # Use role-specific system prompt
            base_prompt = self.get_system_prompt()
            # OPTIMIZATION: Use smart lore filtering instead of all terms
            relevant_lore_terms = self.get_relevant_lore_terms(dialogue, character_name)

            prompt = (
                base_prompt + f"Context: {context}\n"
                f"Character's style: {character_style}\n"
                f"Preserve names: {', '.join(self.get_relevant_names(dialogue))}\n\n"
                "Special Terms (Strongly prefer using these Thai translations):\n"
            )

            for term, explanation in relevant_lore_terms.items():
                prompt += f"{term}: {explanation}\n"

            prompt += f"\n\nText to translate: {dialogue}"

            # OPTIMIZATION: Monitor token usage
            estimated_tokens = self.count_tokens_estimate(prompt)
            logging.info(
                f"🔍 Estimated prompt tokens: {estimated_tokens} (Target: <600)"
            )

            if estimated_tokens > 800:
                logging.warning(
                    f"⚠️ High token usage detected: {estimated_tokens} tokens"
                )
            elif estimated_tokens < 500:
                logging.info(f"✅ Optimized token usage: {estimated_tokens} tokens")

            try:
                # สร้าง Content สำหรับ Gemini API
                generation_config = {
                    "max_output_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                }

                # แสดงข้อความเริ่มการแปลในคอนโซล
                print(
                    f"                                            ", end="\r"
                )  # เคลียร์บรรทัด
                print(f"[Gemini API] Translating: {dialogue[:40]}...", end="\r")

                # บันทึกเวลาเริ่มต้น
                start_time = time.time()

                # แก้ไขวิธีการเรียก API - ส่งเฉพาะ prompt (ไม่ส่ง dialogue แยก)
                response = self.model.generate_content(
                    prompt,  # ส่งเฉพาะ prompt เต็มๆ ไม่ต้องส่ง dialogue แยก
                    generation_config=generation_config,
                    safety_settings=self.safety_settings,
                )

                # คำนวณเวลาที่ใช้
                elapsed_time = time.time() - start_time

                # สำหรับ Gemini เราไม่มีจำนวน token ที่แน่นอน ให้ประมาณจากจำนวนคำ
                input_words = len(prompt.split())
                output_words = (
                    len(response.text.split()) if hasattr(response, "text") else 0
                )
                # ประมาณ token โดยเฉลี่ย 1 คำ = 1.3 token
                input_tokens = int(input_words * 1.3)
                output_tokens = int(output_words * 1.3)
                total_tokens = input_tokens + output_tokens

                # แสดงข้อมูลในคอนโซล
                short_model = (
                    self.model_name if hasattr(self, "model_name") else "gemini"
                )
                # แสดงชื่อเต็มของโมเดลให้ชัดเจน
                print(f"[Gemini API] Translation complete                ", end="\r")
                print(
                    f"[{short_model.upper()}] : {dialogue[:30]}... -> ~{total_tokens} tokens ({elapsed_time:.2f}s)"
                )
                logging.info(
                    f"[Gemini API] Estimated tokens: ~{input_tokens} (input) + ~{output_tokens} (output) = ~{total_tokens} tokens in {elapsed_time:.2f}s"
                )

                # ดึงข้อความจาก response และตรวจสอบอย่างปลอดภัย
                if hasattr(response, "text") and response.text:
                    translated_dialogue = response.text.strip()
                else:
                    raise ValueError("No response text from Gemini API")

                # ทำความสะอาดข้อความแปล
                translated_dialogue = re.sub(
                    r"\b(ครับ|ค่ะ|ครับ/ค่ะ)\b", "", translated_dialogue
                ).strip()
                for term in relevant_lore_terms:
                    translated_dialogue = re.sub(
                        r"\b" + re.escape(term) + r"\b",
                        term,
                        translated_dialogue,
                        flags=re.IGNORECASE,
                    )

                # ตรวจสอบและแทนที่กรณีพิเศษสำหรับเลข 2 และ ???
                if re.match(r"^2+\??$", dialogue.strip()) or dialogue.strip() == "???":
                    translated_dialogue = "???"

                # ตรวจสอบกรณีเลข 2 เป็นส่วนหนึ่งของประโยค
                if dialogue.strip() and re.match(r"^\s*2+\s*$", dialogue.strip()):
                    translated_dialogue = "???"

                # สร้างข้อความผลลัพธ์สุดท้าย
                if character_name:
                    # ตรวจสอบเพิ่มเติมหากชื่อตัวละครเป็นเลข 2
                    if (
                        re.match(r"^2+$", character_name)
                        or character_name.strip() == "???"
                    ):
                        character_name = "???"
                    final_translation = f"{character_name}: {translated_dialogue}"
                else:
                    final_translation = translated_dialogue

                # ตรวจสอบความสมบูรณ์ของการแปล
                if not self.is_translation_complete(text, final_translation):
                    # ตรวจสอบเงื่อนไขที่ไม่ต้องแปลซ้ำ
                    skip_retranslation = False

                    # กรณีข้อความสั้น ไม่ต้องแปลซ้ำ
                    if len(text.split()) <= 5:
                        skip_retranslation = True
                        logging.info("Skip retranslation for short text")

                    # กรณีชื่อตัวละครพิเศษ ไม่ต้องแปลซ้ำ
                    if any(name in text for name in ["Y'shtola", "Yshtola", "???"]):
                        skip_retranslation = True
                        logging.info("Skip retranslation for character names")

                    # กรณีมีตัวละครพูด ให้ตรวจสอบความยาวเพิ่มเติม
                    if ":" in text and len(text.split(":")[1].strip()) < 30:
                        skip_retranslation = True
                        logging.info("Skip retranslation for short dialogue")

                    if not skip_retranslation:
                        logging.warning(
                            "Translation appears incomplete, retrying with stronger prompt"
                        )

                        # ลองแปลอีกครั้งด้วย prompt ที่เน้นย้ำความสมบูรณ์มากขึ้น
                        enhanced_prompt = (
                            prompt
                            + "\n\nVERY IMPORTANT: You MUST translate the ENTIRE text completely. Do not cut off or truncate any part of the message."
                        )

                        retry_response = self.model.generate_content(
                            enhanced_prompt,
                            generation_config=generation_config,
                            safety_settings=self.safety_settings,
                        )

                        if hasattr(retry_response, "text") and retry_response.text:
                            retry_translation = retry_response.text.strip()

                            # ทำความสะอาดข้อความแปล
                            retry_translation = re.sub(
                                r"\b(ครับ|ค่ะ|ครับ/ค่ะ)\b", "", retry_translation
                            ).strip()

                            # เปรียบเทียบความยาวและคุณภาพ - ถ้าแปลใหม่ยาวกว่ามากๆ ถึงจะเอามาใช้
                            if len(retry_translation) > len(translated_dialogue) * 1.3:
                                translated_dialogue = retry_translation

                                if character_name:
                                    final_translation = (
                                        f"{character_name}: {translated_dialogue}"
                                    )
                                else:
                                    final_translation = translated_dialogue

                # บันทึกลง cache เฉพาะคำแปลที่สมบูรณ์
                self.last_translations[dialogue] = translated_dialogue
                if character_name:
                    self.cache.add_validated_name(character_name)  # เพิ่มชื่อเข้า cache

                # Store character name in session cache for consistency (EXACT MATCH ONLY)
                try:
                    if speaker and character_name:
                        # Normalize speaker key for better matching - EXACT MATCH ONLY
                        normalized_speaker = speaker.lower().strip()

                        # Only store if translation actually occurred or if it's a new entry
                        # CRITICAL: This prevents substring conflicts by using exact string matches
                        if (normalized_speaker not in self.session_character_names or
                            self.session_character_names[normalized_speaker] != character_name):

                            self.session_character_names[normalized_speaker] = character_name
                            self.session_speaker_count += 1

                            # Memory management - cleanup old entries using FIFO
                            if len(self.session_character_names) > self.max_session_names:
                                # Remove oldest entries (FIFO approach)
                                keys_to_remove = list(self.session_character_names.keys())[:len(self.session_character_names) // 4]
                                for key in keys_to_remove:
                                    del self.session_character_names[key]
                                logging.debug(f"[NAME CACHE] Cleaned {len(keys_to_remove)} old entries")

                            logging.debug(f"[NAME CACHE] Stored: {speaker} -> {character_name} (normalized: {normalized_speaker})")
                except Exception as e:
                    logging.warning(f"Cache storage error: {e}")

                return final_translation

            except Exception as api_error:
                logging.error(f"Gemini API error: {str(api_error)}")
                # ลองใช้วิธีเรียก API อีกแบบหนึ่ง (กรณี model เก่า)
                try:
                    response = self.model.generate_content(
                        [{"role": "user", "parts": [prompt]}],
                        generation_config=generation_config,
                        safety_settings=self.safety_settings,
                    )

                    if hasattr(response, "text") and response.text:
                        translated_dialogue = response.text.strip()

                        # ทำความสะอาดข้อความแปล
                        translated_dialogue = re.sub(
                            r"\b(ครับ|ค่ะ|ครับ/ค่ะ)\b", "", translated_dialogue
                        ).strip()

                        if character_name:
                            return f"{character_name}: {translated_dialogue}"
                        return translated_dialogue
                    else:
                        raise ValueError("No response text from alternative API call")
                except Exception as alt_error:
                    logging.error(f"Alternative API call also failed: {str(alt_error)}")
                    return f"[Error: {str(api_error)}]"

        except Exception as e:
            logging.error(f"Unexpected error in translation: {str(e)}")
            return f"[Error: {str(e)}]"

    def is_similar_to_choice_prompt(self, text, threshold=0.7):
        """ตรวจสอบและแยกส่วนประกอบของ choice dialogue

        Args:
            text: ข้อความที่ต้องการตรวจสอบ
            threshold: ระดับความคล้ายคลึงที่ยอมรับได้

        Returns:
            tuple: (is_choice, prompt_part, choices) หรือ (False, None, None) ถ้าไม่ใช่ choice
        """
        try:
            # 1. รูปแบบ prompts ที่บ่งบอกว่าเป็น choice dialogue (รวม OCR variations)
            choice_prompts = [
                "What will you say?",
                "What will you say",
                "what will you say?",
                "what will you say",
                "What will YOu say?",  # OCR errors
                "What will YOu say",
                "what will you say",
                "whatwill you say?",
                "what willyou say?",
                "what will yousay?",
                "whatwillyou say?",
                "What would you like to ask?",
                "Choose your response.",
                "Select an option.",
                "How would you like to respond?",
                "Select a dialogue option.",
                "คุณจะพูดว่าอะไร?",
                "คุณจะพูดว่าอย่างไร?",
                "เลือกตัวเลือกของคุณ",
            ]

            # 2. ตรวจสอบการมีอยู่ของ prompt ที่แน่นอน
            clean_text = text.strip()

            # เช็คแบบเข้มงวดตามรูปแบบที่แน่นอน
            # ตรวจสอบว่าข้อความขึ้นต้นด้วย prompt หรือไม่
            for prompt in choice_prompts:
                if clean_text.startswith(prompt) or clean_text.lower().startswith(
                    prompt.lower()
                ):
                    # พบ prompt ที่ตรงกัน
                    parts = clean_text.split(prompt, 1)
                    if len(parts) == 2:
                        prompt_part = prompt
                        choices_part = parts[1].strip()

                        # ดึงตัวเลือกออกมา
                        choices = []

                        # วิธีที่ 1: แยกตามบรรทัด (วิธีที่มีประสิทธิภาพที่สุด)
                        if "\n" in choices_part:
                            lines = [
                                line.strip()
                                for line in choices_part.split("\n")
                                if line.strip()
                            ]
                            if lines:
                                choices = lines

                        # วิธีที่ 2: แยกตามตัวเลือก
                        if not choices:
                            number_starters = self._extract_choices_by_starters(
                                choices_part, ["1.", "2.", "3.", "4."]
                            )
                            if number_starters:
                                choices = number_starters

                        # วิธีที่ 3: แยกตามอักษร
                        if not choices:
                            letter_starters = self._extract_choices_by_starters(
                                choices_part, ["A.", "B.", "C.", "D."]
                            )
                            if letter_starters:
                                choices = letter_starters

                        # วิธีที่ 4: แยกตามเครื่องหมายวรรคตอน
                        if not choices and any(
                            mark in choices_part for mark in [".", "!", "?"]
                        ):
                            import re

                            split_by_punct = re.split(r"(?<=[.!?])\s+", choices_part)
                            if len(split_by_punct) > 1:
                                choices = [
                                    choice.strip()
                                    for choice in split_by_punct
                                    if choice.strip()
                                ]

                        # วิธีที่ 5: ถ้าวิธีข้างต้นล้มเหลว แต่มีข้อความหลัง prompt
                        if not choices and choices_part:
                            choices = [choices_part]

                        # ถ้าพบตัวเลือก
                        if choices:
                            return True, prompt_part, choices
                    else:
                        # กรณีพบเฉพาะ prompt โดยไม่มีเนื้อหาตามหลัง
                        return True, prompt, []

                # 3. ตรวจสอบว่า prompt อยู่ในข้อความหรือไม่ (แม้ไม่ได้อยู่ที่ต้นข้อความ)
                if prompt in clean_text or prompt.lower() in clean_text.lower():
                    idx = max(clean_text.lower().find(prompt.lower()), 0)
                    if idx < 20:  # ถ้าอยู่ในช่วงต้นข้อความ (ในระยะ 20 ตัวอักษรแรก)
                        # แยกข้อความส่วนก่อนและหลัง prompt
                        before_prompt = clean_text[:idx].strip()
                        after_prompt = clean_text[idx + len(prompt) :].strip()

                        # ถ้าส่วนก่อน prompt มีน้อยกว่า 10 ตัวอักษร และหลัง prompt มีเนื้อหา
                        if len(before_prompt) < 10 and after_prompt:
                            # แยกตัวเลือกเช่นเดียวกับด้านบน
                            choices = []

                            # แยกตามบรรทัด
                            if "\n" in after_prompt:
                                lines = [
                                    line.strip()
                                    for line in after_prompt.split("\n")
                                    if line.strip()
                                ]
                                if lines:
                                    choices = lines

                            # ถ้าไม่มีตัวเลือก ให้ใช้ข้อความทั้งหมดหลัง prompt
                            if not choices:
                                choices = [after_prompt]

                            return True, prompt, choices

            # 4. ตรวจสอบรูปแบบที่อาจเกิดจาก OCR ผิดพลาด
            ocr_variants = [
                "Whatwill you say?",
                "What willyou say?",
                "WhatwilI you say?",
                "What wiIl you say?",
                "Vhat will you say?",
                "VVhat will you say?",
            ]

            for variant in ocr_variants:
                if variant in clean_text or variant.lower() in clean_text.lower():
                    # พบ variant ที่น่าจะเป็น "What will you say?"
                    standard_prompt = "What will you say?"
                    idx = max(clean_text.lower().find(variant.lower()), 0)
                    after_variant = clean_text[idx + len(variant) :].strip()

                    # แยกตัวเลือกเช่นเดียวกับด้านบน
                    choices = []

                    # แยกตามบรรทัด
                    if "\n" in after_variant:
                        lines = [
                            line.strip()
                            for line in after_variant.split("\n")
                            if line.strip()
                        ]
                        if lines:
                            choices = lines

                    # ถ้าไม่มีตัวเลือก ให้ใช้ข้อความทั้งหมดหลัง variant
                    if not choices:
                        choices = [after_variant]

                    return True, standard_prompt, choices

            # ไม่ใช่ choice dialogue
            return False, None, None

        except Exception as e:
            logging.warning(f"Error in is_similar_to_choice_prompt: {str(e)}")
            # กรณีเกิด error ให้ส่งค่าที่ปลอดภัย
            return False, None, None

    def _extract_choices_by_starters(self, text, starters):
        """แยกตัวเลือกจากข้อความโดยใช้คำเริ่มต้นที่กำหนด

        Args:
            text: ข้อความที่ต้องการแยกตัวเลือก
            starters: list ของคำเริ่มต้น เช่น ["1.", "2."]

        Returns:
            list: รายการตัวเลือกที่แยกได้
        """
        try:
            choices = []

            # กรณีไม่มีข้อความ
            if not text:
                return []

            # ตรวจสอบว่ามีคำเริ่มต้นในข้อความหรือไม่
            found_starter = False
            for starter in starters:
                if starter in text:
                    found_starter = True
                    break

            if not found_starter:
                return []

            # วิธีที่ 1: ใช้ regex ที่มีประสิทธิภาพมากขึ้น
            import re

            pattern = "|".join(re.escape(starter) for starter in starters)
            regex = rf"({pattern})\s*(.*?)(?=(?:{pattern})|$)"

            matches = re.findall(regex, text, re.DOTALL)
            if matches:
                for match in matches:
                    starter, choice_text = match
                    if choice_text.strip():
                        choices.append(f"{starter} {choice_text.strip()}")
                return choices

            # วิธีที่ 2: ถ้า regex ล้มเหลว ใช้วิธีแยกแบบดั้งเดิม
            remaining_text = text
            current_choice = ""
            current_starter = None

            for i, starter in enumerate(starters):
                if starter in remaining_text:
                    # ถ้ามี starter ปัจจุบันและเจอ starter ใหม่
                    if current_starter:
                        # เก็บตัวเลือกปัจจุบัน
                        if current_choice:
                            choices.append(
                                f"{current_starter} {current_choice.strip()}"
                            )

                    # แยกข้อความที่ starter
                    parts = remaining_text.split(starter, 1)
                    remaining_text = parts[1] if len(parts) > 1 else ""
                    current_starter = starter
                    current_choice = remaining_text

                    # ตรวจสอบ starter ถัดไป
                    next_starter_pos = float("inf")
                    for next_starter in starters[i + 1 :]:
                        pos = remaining_text.find(next_starter)
                        if pos != -1 and pos < next_starter_pos:
                            next_starter_pos = pos

                    # ถ้ามี starter ถัดไป
                    if next_starter_pos != float("inf"):
                        current_choice = remaining_text[:next_starter_pos]
                        remaining_text = remaining_text[next_starter_pos:]

                    # เก็บตัวเลือกปัจจุบัน
                    if current_choice:
                        choices.append(f"{current_starter} {current_choice.strip()}")

            # เก็บตัวเลือกสุดท้าย
            if (
                current_starter
                and current_choice
                and not any(starter in current_choice for starter in starters)
            ):
                choices.append(f"{current_starter} {current_choice.strip()}")

            return choices

        except Exception as e:
            logging.warning(f"Error extracting choices by starters: {str(e)}")
            return []

    def translate_choice(self, text):
        """แปลข้อความตัวเลือกสำหรับ H-game (ลองแปล Choices เป็นก้อนเดียว)"""
        try:
            # 1. ตรวจสอบและแยกส่วนประกอบ (เหมือนเดิม)
            is_choice, header, choices_raw_list = self.is_similar_to_choice_prompt(text)

            if not is_choice or not header:
                logging.warning(
                    f"translate_choice: Not a recognized choice format: {text[:50]}..."
                )
                # Fallback โดยไม่ recurse - เรียก translate แบบปกติ
                return self.translate(text, is_choice_option=False)

            # 2. กำหนด header ภาษาไทย
            translated_header = "คุณจะพูดว่าอย่างไร?"  # Default header for choice prompts
            # (อาจเพิ่ม Logic แปล Header อื่นๆ ถ้าต้องการ)

            # 3. เตรียม choices_text (ส่วนที่เป็นตัวเลือกทั้งหมด)
            # ดึงมาจาก text ดั้งเดิม หลัง header
            header_len = len(header)
            choices_text = text[
                header_len:
            ].strip()  # เอาเฉพาะส่วนหลัง header และตัดช่องว่าง/ขึ้นบรรทัดใหม่นำหน้า

            if not choices_text:  # ถ้าไม่มีตัวเลือกจริงๆ
                logging.warning(
                    f"Choice detected but no options found after header: '{header}'"
                )
                return translated_header

            logging.debug(
                f"Header: '{header}', Choices Text Block: '{choices_text[:50]}...'"
            )

            # แยกตัวเลือกถ้าไม่มี newlines (เผื่อ OCR รวมประโยคเป็นบรรทัดเดียว)
            if "\n" not in choices_text:
                # ลองแยกประโยคตาม punctuation
                import re

                # แยกตาม ! ? . ที่ตามด้วยช่องว่างและตัวอักษรใหญ่
                sentence_splits = re.split(r"([.!?])\s+(?=[A-Z])", choices_text)
                if len(sentence_splits) > 1:
                    # รวมประโยคกลับและแยกเป็นบรรทัด
                    sentences = []
                    for i in range(0, len(sentence_splits), 2):
                        if i < len(sentence_splits):
                            sentence = sentence_splits[i]
                            if i + 1 < len(sentence_splits):
                                sentence += sentence_splits[
                                    i + 1
                                ]  # เพิ่ม punctuation กลับ
                            sentences.append(sentence.strip())

                    if len(sentences) > 1:
                        choices_text = "\n".join(sentences)
                        logging.info(
                            f"Auto-separated choices into {len(sentences)} sentences"
                        )

            # 4. สร้าง Prompt ใหม่สำหรับแปล Choices ทั้งก้อน
            try:
                choices_block_prompt = (
                    "You are translating game dialogue choices from English to Thai. "
                    "Translate the following block of text containing ONLY the choice options, preserving the meaning and tone of each option. "
                    "Each line represents a separate dialogue choice option. "
                    "DO NOT add any extra information, context, questions like 'What will you say?', or bullet points.\n\n"
                    f'CHOICE OPTIONS BLOCK:\n"""\n{choices_text}\n"""\n\n'
                    "RULES:\n"
                    "1. Translate EACH choice option on its own line.\n"
                    "2. Each line should be a separate, complete choice.\n"
                    "3. Keep translations concise and natural for game choices.\n"
                    "4. Preserve proper names.\n"
                    "5. Return ONLY the Thai translations, one per line.\n"
                )

                # ใช้ Generation Config เดิม หรือปรับเล็กน้อย
                choice_gen_config = {
                    "max_output_tokens": self.max_tokens,  # ให้ token เพียงพอสำหรับทุกตัวเลือก
                    "temperature": max(0.2, self.temperature - 0.2),  # ลด temp ลงอีกนิด
                    "top_p": self.top_p,
                }

                logging.debug("Sending choices block to Gemini for translation...")
                choice_response = self.model.generate_content(
                    choices_block_prompt,
                    generation_config=choice_gen_config,
                    safety_settings=self.safety_settings,
                )

                if hasattr(choice_response, "text") and choice_response.text:
                    translated_choices_block = choice_response.text.strip()
                    logging.debug(
                        f"Raw translated choices block: '{translated_choices_block}'"
                    )

                    # 5. นำผลลัพธ์มาประกอบร่างและทำความสะอาด
                    # แยกบรรทัดผลลัพธ์
                    translated_lines = [
                        line.strip()
                        for line in translated_choices_block.split("\n")
                        if line.strip()
                    ]

                    translated_choices_final = []
                    for line in translated_lines:
                        # ทำความสะอาดแต่ละบรรทัด (เผื่อ AI ยังใส่ prefix มา)
                        patterns_to_remove_prefix = [
                            r"^(คุณจะพูดว่าอย่างไร\??[:：]?)\s*",
                            r"^(What will you say\??[:：]?)\s*",
                            r"^[•\-*◦]\s*",  # ลบ bullet point ที่อาจติดมา
                        ]
                        cleaned_line = line
                        for pattern in patterns_to_remove_prefix:
                            cleaned_line = re.sub(
                                pattern, "", cleaned_line, count=1, flags=re.IGNORECASE
                            ).strip()

                        # เพิ่ม bullet point
                        if cleaned_line:
                            translated_choices_final.append("• " + cleaned_line)

                    if translated_choices_final:
                        # เพิ่มหัวข้อภาษาไทยกลับมา (ตาม V9 approach)
                        result = f"{translated_header}\n" + "\n".join(
                            translated_choices_final
                        )
                        logging.debug(f"Final Choice translation result:\n{result}")
                        return result
                    else:
                        # ถ้าหลังจากการแปลและ clean แล้วไม่มีตัวเลือกเหลือเลย
                        logging.warning(
                            "Translated choices block resulted in empty options."
                        )
                        return translated_header  # คืนแค่ header

                else:
                    logging.warning(f"Failed to translate choices block.")
                    # Fallback: ลองแปลทีละตัวเลือกแบบเดิม (เผื่อวิธีใหม่ใช้ไม่ได้ผล)
                    logging.warning("Falling back to translating choices individually.")
                    translated_choices = []
                    for choice in choices_raw_list:  # ใช้ choices_raw_list ที่แยกไว้ตอนแรก
                        choice = choice.strip()
                        if not choice:
                            continue
                        try:
                            # ใช้ Prompt เดิมสำหรับแปลทีละตัวเลือก
                            choice_prompt_individual = (
                                "You are translating ONLY a single game dialogue choice OPTION provided below from English to Thai. "
                                "Translate ONLY this specific option concisely and naturally.\n\n"
                                f'OPTION TO TRANSLATE: "{choice}"\n\n'
                                "Rules:\n"
                                "1. Translate ONLY the option text provided above.\n"
                                "2. DO NOT include the question or context like 'What will you say?' or '\u0e04\u0e38\u0e13\u0e08\u0e30\u0e1e\u0e39\u0e14\u0e27\u0e48\u0e32\u0e2d\u0e22\u0e48\u0e32\u0e07\u0e44\u0e23?'.\n"
                                "3. Keep the translation concise.\n"
                                "4. Preserve proper names exactly.\n"
                                "5. Return ONLY the Thai translation of the option.\n"
                            )
                            choice_response_fb = self.model.generate_content(
                                choice_prompt_individual
                            )
                            if (
                                hasattr(choice_response_fb, "text")
                                and choice_response_fb.text
                            ):
                                tc = choice_response_fb.text.strip()
                                # Clean fallback result
                                for pattern in [
                                    r"^(คุณจะพูดว่าอย่างไร\??[:：]?)\s*",
                                    r"^[•\-*◦]\s*",
                                ]:
                                    tc = re.sub(
                                        pattern, "", tc, count=1, flags=re.IGNORECASE
                                    ).strip()
                                if tc:
                                    translated_choices.append("• " + tc)
                                else:
                                    translated_choices.append(
                                        f"• {choice} [NC/FB]"
                                    )  # Fallback Clean failed
                            else:
                                translated_choices.append(
                                    f"• {choice} [NT/FB]"
                                )  # Fallback Translate failed
                        except Exception as fb_err:
                            logging.error(
                                f"Error during fallback choice translation for '{choice}': {fb_err}"
                            )
                            translated_choices.append(f"• {choice} [ERR/FB]")

                    if translated_choices:
                        result = f"{translated_header}\n" + "\n".join(
                            translated_choices
                        )
                        return result
                    else:
                        return translated_header  # ถ้า fallback ก็ยังไม่ได้

            except Exception as translate_block_error:
                logging.error(
                    f"Error translating choices block: {translate_block_error}"
                )
                # ถ้าการแปลทั้งก้อนล้มเหลว อาจคืนค่า Error หรือลอง Fallback แปลทีละอัน
                return f"[Error translating choices: {translate_block_error}]"

        except Exception as e:
            logging.error(f"General error in translate_choice: {str(e)}")
            import traceback

            logging.error(traceback.format_exc())
            return f"[Error: {str(e)}]"

    def get_character_info(self, character_name):
        # จัดการกับกรณีพิเศษสำหรับ ??? และ เลข 2
        if character_name in ["???", "2", "22", "222"] or re.match(
            r"^2+$", character_name
        ):
            return {
                "firstName": "???",
                "gender": "unknown",
                "role": "Mystery character",
                "relationship": "Unknown/Mysterious",
                "pronouns": {"subject": "ฉัน", "object": "ฉัน", "possessive": "ของฉัน"},
            }

        # ตรวจสอบเพิ่มเติมด้วย EnhancedNameDetector
        if self.enhanced_detector:
            try:
                # ถ้าชื่อเป็นตัวเลขหรือมีรูปแบบคล้าย ??? ให้แก้ไขเป็น ???
                if re.match(r"^[2\?]+\??$", character_name):
                    return {
                        "firstName": "???",
                        "gender": "unknown",
                        "role": "Mystery character",
                        "relationship": "Unknown/Mysterious",
                        "pronouns": {
                            "subject": "ฉัน",
                            "object": "ฉัน",
                            "possessive": "ของฉัน",
                        },
                    }
            except Exception as e:
                logging.warning(f"Error in enhanced checking for character name: {e}")

        # ค้นหาข้อมูลตัวละครตามปกติ
        for char in self.character_data:
            if (
                character_name == char["firstName"]
                or character_name == f"{char['firstName']} {char['lastName']}".strip()
            ):
                return char
        return None

    def batch_translate(self, texts, batch_size=10):
        """แปลข้อความเป็นชุด"""
        translated_texts = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            translated_batch = [self.translate(text) for text in batch]
            translated_texts.extend(translated_batch)
        return translated_texts

    def analyze_translation_quality(self, original_text, translated_text):
        """วิเคราะห์คุณภาพการแปล"""
        # มีการเปลี่ยนแปลงในส่วนที่เรียกใช้ API
        prompt = (
            "As a translation quality assessor, evaluate the following translation from English to Thai. "
            "Consider factors such as accuracy, naturalness, and preservation of the original tone and style. "
            f"Original (English): {original_text}\n"
            f"Translation (Thai): {translated_text}\n"
            "Provide a brief assessment and a score out of 10."
        )

        try:
            # ส่งคำขอไปยัง Gemini API
            response = self.model.generate_content(
                [{"role": "user", "parts": [prompt]}]
            )
            return response.text.strip()
        except Exception as e:
            logging.error(f"Error in translation quality analysis: {str(e)}")
            return "Unable to assess translation quality due to an error."

    def reload_data(self):
        """โหลดข้อมูลใหม่และล้าง cache"""
        print("TranslatorGemini: Reloading NPC data...")
        self.load_npc_data()
        self.load_example_translations()
        self.cache.clear_session()
        self.last_translations.clear()
        print("TranslatorGemini: Data reloaded successfully")

    def analyze_custom_prompt(self, prompt_with_text):
        """Process a custom prompt with AI"""
        try:
            # มีการเปลี่ยนแปลงในส่วนที่เรียกใช้ API
            response = self.model.generate_content(
                [{"role": "user", "parts": [prompt_with_text]}],
                generation_config={
                    "max_output_tokens": self.max_tokens * 2,
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                },
            )
            return response.text.strip()

        except Exception as e:
            logging.error(f"Error in custom prompt analysis: {e}")
            raise ValueError(f"Failed to process text with AI: {str(e)}")


    def get_name_cache_stats(self):
        """Return cache statistics for monitoring character name consistency"""
        total_requests = self.cache_hits + self.cache_misses
        hit_ratio = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "cached_names": len(self.session_character_names),
            "session_speakers": self.session_speaker_count,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_ratio_percent": round(hit_ratio, 2),
            "memory_usage_kb": len(str(self.session_character_names)) // 1024,
            "cache_entries": list(self.session_character_names.items())[:5] if self.session_character_names else []
        }
