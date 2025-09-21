"""
🎭 NPC Dialogue Simulator - Real Translation Comparison
แสดงการเปรียบเทียบการแปลจริงระหว่าง ใช้แค่ชื่อ vs ใช้บริบทเต็มรูปแบบ
Version: 2.0
"""

import tkinter as tk
from tkinter import ttk, font
import json
import os
import threading
import time
from datetime import datetime
from npc_file_utils import get_npc_file_path

class DialogueSimulator:
    def __init__(self, parent=None, translator=None):
        self.parent = parent
        self.window = None
        self.current_character = None
        self.translator = translator
        self.font_family = "IBM Plex Sans Thai"
        self.font_size = 14
        
        # โหลดการตั้งค่าฟอนต์จาก settings.json
        self.load_font_settings()
        
        # ตัวอย่างบทสนทนาจำลอง
        self.dialogue_scenarios = {
            "scholarly": {
                "title": "📚 นักปราชญ์",
                "dialogues": [
                    "This is no different from the teleportation magicks to which we are all accustomed─magicks that allow for the transportation of those inanimate objects one considers to be an extension of oneself.",
                    "A facility for processing souls... As distressing as the very concept is, I confess I'm curious to see the technology employed.",
                    "It was forsaken in the wake of the Flood, but a certain Nu Mou chose to make their home there soon after."
                ]
            },
            "surprised": {
                "title": "😮 ความประหลาดใจ", 
                "dialogues": [
                    "Excuse me, but...you're Wuk Lamat, are you not? I hadn't thought to encounter one of the Dawn's Promise here of all places..."
                ]
            },
            "mystical": {
                "title": "✨ เวทมนตร์",
                "dialogues": [
                    "The aether here flows differently... as if guided by an unseen hand.",
                    "I sense a disturbance in the very fabric of reality itself.",
                    "These ancient magicks speak of powers beyond mortal comprehension."
                ]
            }
        }
        
        self.current_scenario = "scholarly"
        self.current_dialogue_index = 0
        self.translation_results = {}
        
    def load_font_settings(self):
        """โหลดการตั้งค่าฟอนต์จาก settings.json"""
        try:
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
                font_file = settings.get("font", "IBM Plex Sans Thai Medium.ttf")
                self.font_family = font_file.replace(".ttf", "").replace("Medium", "").strip()
                self.font_size = int(settings.get("font_size", 24) * 0.6)
        except:
            pass
            
    def show(self, character_name=None, translator=None):
        """แสดงหน้าต่าง Dialogue Simulator"""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return
            
        # โหลดข้อมูลตัวละครจาก npc.json โดยตรง
        self.current_character = None
        if character_name:
            self.current_character = self.load_character_from_npc(character_name)
            
        if translator:
            self.translator = translator
            
        self.create_window()
        
    def load_character_from_npc(self, character_name):
        """โหลดข้อมูลตัวละครจาก npc.json"""
        try:
            npc_path = get_npc_file_path()
            if not npc_path or not os.path.exists(npc_path):
                # ถ้าไม่เจอจาก utils ลองหาในโฟลเดอร์ปัจจุบัน
                npc_path = "npc.json"
                
            print(f"Loading character from: {npc_path}")
            
            with open(npc_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # ค้นหาตัวละครจากชื่อ (ข้อมูลอยู่ใน main_characters)
            for char in data.get("main_characters", []):
                if char.get("firstName") == character_name:
                    print(f"✓ Found character in npc.json: {character_name}")
                    
                    # เพิ่ม style จาก character_roles
                    character_roles = data.get("character_roles", {})
                    if character_name in character_roles:
                        char["style"] = character_roles[character_name]
                        print(f"✓ Found character style: {char['style']}")
                    
                    return char
                    
            print(f"✗ Character not found in npc.json: {character_name}")
            return None
            
        except Exception as e:
            print(f"Error loading character from npc.json: {e}")
            return None
        
    def create_window(self):
        """สร้างหน้าต่างหลัก"""
        self.window = tk.Toplevel(self.parent if self.parent else None)
        self.window.title("🎭 NPC Dialogue Simulator - Real Translation Test")
        self.window.geometry("1200x1040")  # ปรับขนาดให้พอดีจอ
        self.window.configure(bg="#1e1e1e")
        
        # ตั้งค่าสไตล์
        self.setup_styles()
        
        # สร้าง UI
        self.create_ui()
        
        # เริ่มการแปลอัตโนมัติ
        if self.current_character and self.translator:
            self.start_translation()
        
    def setup_styles(self):
        """ตั้งค่าสไตล์สำหรับ ttk widgets"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # สไตล์สำหรับ Frame
        style.configure("Dark.TFrame", background="#1e1e1e")
        style.configure("Card.TFrame", background="#2d2d30", relief="flat", borderwidth=1)
        
        # สไตล์สำหรับ Label (ปรับขนาดให้พอดีจอ)
        style.configure("Title.TLabel", background="#1e1e1e", foreground="#ffffff", 
                       font=(self.font_family, 20, "bold"))  # ลดขนาด
        style.configure("Subtitle.TLabel", background="#2d2d30", foreground="#cccccc",
                       font=(self.font_family, 14))  # ลดขนาด
        style.configure("Info.TLabel", background="#1e1e1e", foreground="#38bdf8",
                       font=(self.font_family, 12))  # ลดขนาด
        style.configure("CharName.TLabel", background="#1e1e1e", foreground="#38bdf8",
                       font=(self.font_family, 28, "bold"))  # ลดขนาดชื่อตัวละคร
                       
    def create_ui(self):
        """สร้าง UI หลัก"""
        # Header พร้อมข้อมูลตัวละคร
        header_frame = ttk.Frame(self.window, style="Dark.TFrame")
        header_frame.pack(fill="x", padx=15, pady=(15, 8))
        
        # สร้าง frame สำหรับ title และชื่อตัวละคร
        title_char_frame = tk.Frame(header_frame, bg="#1e1e1e")
        title_char_frame.pack(fill="x")
        
        # Title ทางซ้าย
        title_label = tk.Label(title_char_frame, text="🎭 การเปรียบเทียบการแปลด้วยระบบจริง", 
                            font=(self.font_family, 18, "bold"), fg="#ffffff", bg="#1e1e1e")
        title_label.pack(side="left")
        
        # ชื่อตัวละครทางขวา (ปรับขนาดลง)
        if self.current_character:
            char_name = self.current_character.get('firstName', self.current_character.get('name', 'ไม่ระบุ'))
            if self.current_character.get('lastName'):
                char_name += f" {self.current_character['lastName']}"
            char_name_label = tk.Label(title_char_frame, text=char_name, 
                                     font=(self.font_family, 24, "bold"), fg="#38bdf8", bg="#1e1e1e")
            char_name_label.pack(side="right")
        
        # ข้อมูลตัวละครละเอียด
        if self.current_character:
            char_info = f"เพศ: {self.current_character.get('gender', '')}"
            if self.current_character.get('role'):
                char_info += f" | บทบาท: {self.current_character['role']}"
            if self.current_character.get('relationship'):
                char_info += f" | ความสัมพันธ์: {self.current_character['relationship']}"
            
            char_info_label = tk.Label(header_frame, text=char_info, 
                                     font=(self.font_family, 11), fg="#38bdf8", bg="#1e1e1e")
            char_info_label.pack(anchor="w", pady=(3, 0))
            
            # แสดง style ด้านล่างแยกบรรทัด
            if self.current_character.get('style'):
                style_info = f"📝 สไตล์การพูด: {self.current_character['style']}"
                style_label = tk.Label(header_frame, text=style_info, 
                                     font=(self.font_family, 11), fg="#38bdf8", bg="#1e1e1e")
                style_label.pack(anchor="w", pady=(1, 0))
        else:
            no_char_label = tk.Label(header_frame, text="⚠️ ไม่มีตัวละครที่เลือก - จะแสดงเฉพาะการแปลพื้นฐาน", 
                                 font=(self.font_family, 11), fg="#38bdf8", bg="#1e1e1e")
            no_char_label.pack(anchor="w", pady=(3, 0))
        
        # Scenario selector
        scenario_frame = ttk.Frame(self.window, style="Dark.TFrame")
        scenario_frame.pack(fill="x", padx=15, pady=8)
        
        ttk.Label(scenario_frame, text="เลือกประเภทบทสนทนา:", 
                 style="Subtitle.TLabel").pack(side="left", padx=(0, 8))
        
        # เก็บ reference ของปุ่มเพื่ออัพเดตสี
        self.scenario_buttons = {}
        
        for key, scenario in self.dialogue_scenarios.items():
            # นับจำนวนบทสนทนาในแต่ละประเภท
            dialogue_count = len(scenario["dialogues"])
            button_text = f"{scenario['title']}\n({dialogue_count} dialogs)"
            
            btn = tk.Button(
                scenario_frame,
                text=button_text,
                font=(self.font_family, 8),  # ลดขนาดเล็กน้อยเพื่อให้พอดี 2 บรรทัด
                bg="#8B5CF6" if key == self.current_scenario else "#3d3d40",
                fg="white",
                bd=0,
                padx=10,
                pady=6,
                justify="center",  # จัดข้อความตรงกลาง
                activebackground="#9F7AEA",  # เพิ่มสีเมื่อ hover
                command=lambda k=key: self.switch_scenario(k)
            )
            btn.pack(side="left", padx=2)
            self.scenario_buttons[key] = btn  # เก็บ reference
        
        # Navigation buttons
        nav_frame = ttk.Frame(scenario_frame, style="Dark.TFrame")
        nav_frame.pack(side="right")
        
        self.prev_btn = tk.Button(
            nav_frame,
            text="◀ ก่อนหน้า",
            font=(self.font_family, 9),  # ลดขนาด
            bg="#3d3d40",
            fg="white",
            bd=0,
            padx=8,
            pady=4,
            activebackground="#4a4a4a",  # เพิ่มสีเมื่อ hover
            command=self.previous_dialogue
        )
        self.prev_btn.pack(side="left", padx=2)
        
        self.next_btn = tk.Button(
            nav_frame,
            text="ถัดไป ▶",
            font=(self.font_family, 9),  # ลดขนาด
            bg="#3d3d40",
            fg="white",
            bd=0,
            padx=8,
            pady=4,
            activebackground="#4a4a4a",  # เพิ่มสีเมื่อ hover
            command=self.next_dialogue
        )
        self.next_btn.pack(side="left", padx=2)
        
        # Main content area
        self.content_frame = ttk.Frame(self.window, style="Dark.TFrame")
        self.content_frame.pack(fill="both", expand=True, padx=15, pady=8)
        
        # สร้างพื้นที่แสดงผล
        self.create_comparison_area()
        
        # Status bar
        self.status_frame = ttk.Frame(self.window, style="Dark.TFrame")
        self.status_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        self.status_label = ttk.Label(
            self.status_frame,
            text="พร้อมแปล...",
            style="Info.TLabel"
        )
        self.status_label.pack(anchor="w")
        
    def create_comparison_area(self):
        """สร้างพื้นที่เปรียบเทียบการแปล"""
        # Clear existing content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Original text section
        original_frame = ttk.Frame(self.content_frame, style="Card.TFrame")
        original_frame.pack(fill="x", pady=(0, 8))
        
        tk.Label(original_frame, text="📝 ต้นฉบับภาษาอังกฤษ",
                font=(self.font_family, 14, "bold"),  # ลดขนาด
                bg="#2d2d30", fg="#ffffff").pack(anchor="w", padx=15, pady=(8, 3))
        
        current_dialogue = self.get_current_dialogue()
        
        # เพิ่มชื่อตัวละครสีฟ้าเป็นหัวข้อ
        if self.current_character:
            char_name = self.current_character.get('firstName', self.current_character.get('name', ''))
            if self.current_character.get('lastName'):
                char_name += f" {self.current_character['lastName']}"
            if char_name:
                char_header = tk.Label(original_frame, text=f"{char_name}:",
                                     font=(self.font_family, 16, "bold"),  # ลดขนาดชื่อ
                                     bg="#2d2d30", fg="#38bdf8")
                char_header.pack(anchor="w", padx=15, pady=(3, 3))
        
        self.original_text = tk.Label(
            original_frame,
            text=f'"{current_dialogue}"',
            font=(self.font_family, 13),  # ลดขนาดข้อความ
            bg="#2d2d30",
            fg="#ffffff",
            wraplength=1150,
            justify="left"
        )
        self.original_text.pack(anchor="w", padx=15, pady=(3, 10))
        
        # Comparison grid
        compare_frame = ttk.Frame(self.content_frame, style="Dark.TFrame")
        compare_frame.pack(fill="both", expand=True)
        
        # Configure grid
        compare_frame.grid_columnconfigure(0, weight=1)
        compare_frame.grid_columnconfigure(1, weight=1)
        
        # BEFORE - แปลแบบใช้แค่ชื่อ
        before_frame = tk.Frame(compare_frame, bg="#3d2d2d", highlightthickness=1,
                               highlightbackground="#ff6b6b")
        before_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 3), pady=3)
        
        tk.Label(before_frame, text="❌ แปลแบบใช้แค่ชื่อตัวละคร",
                font=(self.font_family, 14, "bold"),  # ลดขนาด
                bg="#3d2d2d", fg="#ff6b6b").pack(anchor="w", padx=15, pady=(8, 3))
        
        tk.Label(before_frame, text="(ไม่มีข้อมูลเพศ, บทบาท, บุคลิก)",
                font=(self.font_family, 10),  # ลดขนาด
                bg="#3d2d2d", fg="#999999").pack(anchor="w", padx=15, pady=(0, 5))
        
        # เพิ่ม Scrollbar สำหรับ Text
        text_frame_before = tk.Frame(before_frame, bg="#3d2d2d")
        text_frame_before.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self.before_text = tk.Text(
            text_frame_before,
            font=(self.font_family, 24),  # ปรับขนาดข้อความเป็น 24
            bg="#3d2d2d",
            fg="#ffffff",
            wrap="word",
            height=8,  # ลดความสูงให้เห็น scrollbar ชัดเจน
            padx=10,
            pady=8,
            relief="flat",
            bd=0
        )
        
        scrollbar_before = tk.Scrollbar(text_frame_before, command=self.before_text.yview,
                                       bg="#3d2d2d", troughcolor="#2d2d2d", 
                                       activebackground="#ff6b6b", width=15)
        self.before_text.config(yscrollcommand=scrollbar_before.set)
        
        self.before_text.pack(side="left", fill="both", expand=True)
        scrollbar_before.pack(side="right", fill="y")
        self.before_text.insert("1.0", "กำลังแปล...")
        self.before_text.config(state="disabled")
        
        # AFTER - แปลแบบใช้บริบทเต็ม
        after_frame = tk.Frame(compare_frame, bg="#2d3d2d", highlightthickness=1,
                              highlightbackground="#4ade80")
        after_frame.grid(row=0, column=1, sticky="nsew", padx=(3, 0), pady=3)
        
        tk.Label(after_frame, text="✅ แปลแบบใช้ข้อมูลบริบทเต็มรูปแบบ",
                font=(self.font_family, 14, "bold"),  # ลดขนาด
                bg="#2d3d2d", fg="#4ade80").pack(anchor="w", padx=15, pady=(8, 3))
        
        context_info = "(มีข้อมูลครบถ้วน)"
        if self.current_character:
            context_items = []
            if self.current_character.get('gender'):
                context_items.append("เพศ")
            if self.current_character.get('role'):
                context_items.append("บทบาท")
            if self.current_character.get('notes'):
                context_items.append("บุคลิก")
            if context_items:
                context_info = f"(มี: {', '.join(context_items)})"
        
        tk.Label(after_frame, text=context_info,
                font=(self.font_family, 10),
                bg="#2d3d2d", fg="#999999").pack(anchor="w", padx=15, pady=(0, 5))
        
        # เพิ่ม Scrollbar สำหรับ Text ฝั่งขวา
        text_frame_after = tk.Frame(after_frame, bg="#2d3d2d")
        text_frame_after.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self.after_text = tk.Text(
            text_frame_after,
            font=(self.font_family, 24),  # ปรับขนาดข้อความเป็น 24
            bg="#2d3d2d",
            fg="#ffffff",
            wrap="word",
            height=8,  # ลดความสูงให้เห็น scrollbar ชัดเจน
            padx=10,
            pady=8,
            relief="flat",
            bd=0
        )
        
        scrollbar_after = tk.Scrollbar(text_frame_after, command=self.after_text.yview,
                                      bg="#2d3d2d", troughcolor="#1d2d1d", 
                                      activebackground="#4ade80", width=15)
        self.after_text.config(yscrollcommand=scrollbar_after.set)
        
        self.after_text.pack(side="left", fill="both", expand=True)
        scrollbar_after.pack(side="right", fill="y")
        self.after_text.insert("1.0", "กำลังแปล...")
        self.after_text.config(state="disabled")
        
    def get_current_dialogue(self):
        """ดึงบทสนทนาปัจจุบัน"""
        dialogues = self.dialogue_scenarios[self.current_scenario]["dialogues"]
        return dialogues[self.current_dialogue_index]
        
    def switch_scenario(self, scenario_key):
        """เปลี่ยนประเภทบทสนทนา"""
        self.current_scenario = scenario_key
        self.current_dialogue_index = 0
        
        # อัพเดตสีปุ่มให้แสดง highlight ปุ่มที่เลือก
        if hasattr(self, 'scenario_buttons'):
            for key, btn in self.scenario_buttons.items():
                if key == scenario_key:
                    btn.config(bg="#8B5CF6")  # สีม่วงเข้มสำหรับปุ่มที่เลือก
                else:
                    btn.config(bg="#3d3d40")  # สีเทาเข้มสำหรับปุ่มที่ไม่ได้เลือก
        
        self.create_comparison_area()
        self.start_translation()
        
    def next_dialogue(self):
        """ไปบทสนทนาถัดไป"""
        dialogues = self.dialogue_scenarios[self.current_scenario]["dialogues"]
        self.current_dialogue_index = (self.current_dialogue_index + 1) % len(dialogues)
        self.create_comparison_area()
        self.start_translation()
        
    def previous_dialogue(self):
        """กลับบทสนทนาก่อนหน้า"""
        dialogues = self.dialogue_scenarios[self.current_scenario]["dialogues"]
        self.current_dialogue_index = (self.current_dialogue_index - 1) % len(dialogues)
        self.create_comparison_area()
        self.start_translation()
        
    def start_translation(self):
        """เริ่มการแปลแบบ async"""
        if not self.translator:
            self.update_status("❌ ไม่พบ Translator - ต้องเปิดจาก NPC Manager")
            return
            
        # แปลใน thread แยกเพื่อไม่ให้ UI ค้าง
        thread = threading.Thread(target=self.perform_translation)
        thread.daemon = True
        thread.start()
        
    def perform_translation(self):
        """ทำการแปลจริง"""
        dialogue = self.get_current_dialogue()
        char_name = self.current_character.get('name', '') if self.current_character else ''
        
        # Prepare dialogue with character name
        if char_name:
            dialogue_with_name = f"{char_name}: {dialogue}"
        else:
            dialogue_with_name = dialogue
            
        try:
            self.update_status("🔄 กำลังแปลแบบใช้แค่ชื่อ...")
            
            # การแปลแบบ BEFORE (ใช้แค่ชื่อ)
            # สร้าง minimal context
            minimal_context = {
                "text": dialogue_with_name,
                "character_names": [char_name] if char_name else [],
                "use_minimal": True  # flag สำหรับบอกว่าใช้ context น้อยที่สุด
            }
            
            # Mock translation for BEFORE (เพราะต้องการแสดงผลต่าง)
            # ในระบบจริงจะเรียก translator แบบไม่ใส่ context
            before_translation = self.translate_minimal(dialogue_with_name)
            
            self.update_translation_display("before", before_translation)
            
            self.update_status("🔄 กำลังแปลแบบใช้บริบทเต็มรูปแบบ...")
            
            # การแปลแบบ AFTER (ใช้บริบทเต็ม)
            if self.current_character:
                # สร้าง full context
                full_context = self.build_full_context(dialogue, self.current_character)
                after_translation = self.translate_with_context(dialogue_with_name, full_context)
            else:
                after_translation = before_translation  # ถ้าไม่มีข้อมูลก็แปลเหมือนกัน
                
            self.update_translation_display("after", after_translation)
            
            self.update_status("✅ แปลเสร็จสิ้น - ดูความแตกต่างได้เลย!")
            
        except Exception as e:
            self.update_status(f"❌ เกิดข้อผิดพลาด: {str(e)}")
            print(f"Translation error: {e}")
            
    def translate_minimal(self, text):
        """แปลแบบใช้ context น้อยที่สุด (แค่ชื่อ)"""
        if self.translator and hasattr(self.translator, 'translate'):
            try:
                # เรียกใช้ translator จริงแบบไม่ใส่ context NPC
                # แต่ใส่แค่ชื่อตัวละคร
                result = self.translator.translate(text)
                return result if result else "ไม่สามารถแปลได้"
            except Exception as e:
                print(f"Error in minimal translation: {e}")
                return self._get_fallback_translation(text, "minimal")
        else:
            # Fallback translation ถ้าไม่มี translator
            return self._get_fallback_translation(text, "minimal")
            
    def translate_with_context(self, text, context):
        """แปลแบบใช้บริบทเต็มรูปแบบ"""
        if self.translator and hasattr(self.translator, 'translate'):
            try:
                # สร้าง enhanced prompt ที่มีบริบทตัวละครเต็ม
                gender = context.get("gender", "")
                role = context.get("role", "")
                style = context.get("style", "")  # ใช้ style จาก character_roles
                relationship = context.get("relationship", "")
                
                # สร้าง context prompt สำหรับการแปล
                context_prompt = f"แปลบทสนทนานี้ให้เหมาะกับตัวละคร: "
                if gender:
                    context_prompt += f"เพศ{gender} "
                if role:
                    context_prompt += f"บทบาท: {role} "
                if relationship:
                    context_prompt += f"ความสัมพันธ์: {relationship} "
                if style:
                    context_prompt += f"สไตล์การพูด: {style} "
                
                # เรียกใช้ translator พร้อม context
                enhanced_text = f"{context_prompt}\n{text}"
                result = self.translator.translate(enhanced_text)
                return result if result else "ไม่สามารถแปลได้"
                
            except Exception as e:
                print(f"Error in context translation: {e}")
                return self._get_fallback_translation(text, "context", context)
        else:
            # Fallback translation ถ้าไม่มี translator
            return self._get_fallback_translation(text, "context", context)
            
    def _get_fallback_translation(self, text, mode="minimal", context=None):
        """Fallback translation เมื่อไม่มี translator API"""
        # Mock translations for demonstration
        if mode == "minimal":
            if "Good morning" in text:
                return "สวัสดีตอนเช้า! อากาศดีจังวันนี้"
            elif "You dare stand" in text:
                return "เจ้ากล้ามาขวางทางข้าหรือ? เตรียมตัวไว้!"
            elif "cannot believe" in text:
                return "ฉันไม่อยากเชื่อเลยว่านี่กำลังเกิดขึ้น... หลังจากทุกอย่างที่เราผ่านมาด้วยกัน!"
            else:
                return "คำแปลพื้นฐาน..."
        
        elif mode == "context" and context:
            gender = context.get("gender", "").lower()
            role = context.get("role", "").lower()
            notes = context.get("notes", "").lower()
            
            # ปรับคำแปลตาม context
            if "Good morning" in text:
                if gender == "female":
                    if "noble" in role or "princess" in role:
                        return "อรุณสวัสดิ์ค่ะ~ วันนี้ท้องฟ้าช่างสดใสเหลือเกิน ✨"
                    else:
                        return "สวัสดีค่ะ! อากาศวันนี้ดีจริงๆ เลยนะคะ"
                elif gender == "male":
                    if "knight" in role or "warrior" in role:
                        return "ขอคารวะ อากาศในยามเช้าช่างแจ่มใสยิ่งนัก"
                    else:
                        return "อรุณสวัสดิ์ครับ! วันนี้อากาศดีมากเลย"
                        
            elif "You dare stand" in text:
                if gender == "female":
                    if "villain" in role or "antagonist" in notes:
                        return "เจ้ากล้าดียิ่งนักที่มาขวางทางข้า... จงเตรียมพบกับจุดจบของเจ้า! 💀"
                    else:
                        return "ท่านคิดจะขวางทางดิฉันหรือคะ? โปรดเตรียมตัวด้วย!"
                elif gender == "male":
                    if "knight" in role:
                        return "เจ้าผู้ไร้เกียรติ กล้ามาขัดขวางหนทางของข้า? จงเตรียมพบกับดาบแห่งความยุติธรรม!"
                    else:
                        return "กล้ามาขวางทางข้าหรือ? เตรียมตัวรับมือไว้!"
                        
            elif "cannot believe" in text:
                if gender == "female":
                    if "emotional" in notes or "sensitive" in notes:
                        return "ดิฉัน... ไม่อยากจะเชื่อเลยค่ะ... ทำไมต้องเป็นแบบนี้... หลังจากทุกสิ่งที่เราเคยผ่านมาด้วยกัน... 💔"
                    else:
                        return "ไม่อยากเชื่อเลยค่ะว่านี่กำลังเกิดขึ้นจริง... หลังจากทุกอย่างที่เราผ่านมา!"
                elif gender == "male":
                    if "stoic" in notes or "serious" in notes:
                        return "ข้าไม่คิดว่าสิ่งนี้จะเกิดขึ้น... แม้จะผ่านการต่อสู้มามากมายด้วยกัน"
                    else:
                        return "ผมไม่อยากจะเชื่อเลยว่านี่กำลังเกิดขึ้น... หลังจากทุกอย่างที่เราผ่านมาด้วยกัน!"
        
        return "คำแปลสำรอง..."
        
    def build_full_context(self, dialogue, character_data):
        """สร้าง context เต็มรูปแบบสำหรับการแปล"""
        context = {
            "name": character_data.get("name", ""),
            "gender": character_data.get("gender", ""),
            "role": character_data.get("role", ""),
            "notes": character_data.get("notes", ""),
            "location": character_data.get("location", ""),
            "scenario": self.current_scenario
        }
        return context
        
    def update_translation_display(self, panel, text):
        """อัพเดตข้อความในพาเนลแปล"""
        def update():
            if panel == "before":
                self.before_text.config(state="normal")
                self.before_text.delete("1.0", "end")
                self.before_text.insert("1.0", text)
                # เลื่อนไปยังด้านบน
                self.before_text.see("1.0")
                self.before_text.config(state="disabled")
            else:
                self.after_text.config(state="normal")
                self.after_text.delete("1.0", "end")
                self.after_text.insert("1.0", text)
                # เลื่อนไปยังด้านบน
                self.after_text.see("1.0")
                self.after_text.config(state="disabled")
                
        if self.window:
            self.window.after(0, update)
            
    def update_status(self, message):
        """อัพเดต status bar"""
        def update():
            if hasattr(self, 'status_label'):
                self.status_label.config(text=message)
                
        if self.window:
            self.window.after(0, update)


# ฟังก์ชันสำหรับทดสอบ
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    
    # ตัวอย่างข้อมูลตัวละคร
    sample_character = {
        "name": "Y'shtola",
        "gender": "Female",
        "role": "Archon, Scholar",
        "notes": "Intelligent, serious, caring but stern",
        "location": "Sharlayan"
    }
    
    simulator = DialogueSimulator()
    simulator.show(sample_character)
    
    root.mainloop()