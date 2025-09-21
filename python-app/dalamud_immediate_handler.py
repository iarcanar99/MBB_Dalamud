"""
Dalamud IMMEDIATE Handler - แสดงคำแปลทันทีเมื่อได้รับข้อความ
Display translations immediately when messages are received
"""

import logging
from typing import Dict, Any, Optional
import time
import threading

# Text Hook Filtering - Block unnecessary messages
BLOCKED_CHAT_TYPES = {
    # 🔥 CRITICAL FIX: Real ChatTypes from actual game logs
    2092,   # Player actions (You use a bowl of mesquite soup)
    2857,   # Combat damage (You hit Necron for X damage)
    12457,  # Enemy damage (Necron hits you for X damage)
    4139,   # Ability casting (Krile begins casting, uses abilities)
    4777,   # Damage taken (Necron takes X damage)
    2729,   # Critical hits (Critical! You hit X for Y damage)
    4398,   # Status gained (gains the effect of)
    4400,   # Status lost (loses the effect of)
    4269,   # HP recovery (You recover X HP)

    # 🆕 v1.4.8.1 ADDITIONS: Equipment and System Messages
    # 71 REMOVED - CONTAINS CUTSCENE TEXT! ("Or was it a gift─the terminal's parting miracle?")
    2105,   # Equipment unequip messages (Ceremonial bangle of aiming unequipped) - RE-ADDED AFTER VERIFICATION

    # v1.4.8.4 ADDITIONS: Combat Text Filtering
    2221,   # HP absorption messages (You absorb 3711 HP)
    2735,   # Status effect messages (The asterodia suffers the effect of Stun)
    10283,  # Spell casting/interruption messages (The asterodia's Bombination is interrupted)
    2874,   # Combat victory messages (You defeat the asterodia)

    # v1.4.8.5 ADDITIONS: Job/Gear Change Messages
    57,     # Gear/job change messages (Gear recommended for a viper equipped)

    # v1.4.8.6 ADDITIONS: NPC/Monster Casting Messages
    12331,  # NPC/Monster spell casting (The asterodia begins casting Bombination)

    # v1.4.8.7 ADDITIONS: Hunt/Party Messages
    11,     # Hunt board notifications and party status messages

    # v1.4.8.9 ADDITIONS: Combat Zone Filtering (from live testing)
    9001,   # Combat damage messages (The striking dummy takes X damage, Critical!)
    10929,  # Status recovery messages (recovers from the effect of)
    29,     # Other player actions/emotes (gives enthusiastic Lali-ho!)

    # v1.4.10.1 ADDITIONS: Additional Combat Zone Filtering
    9002,   # Combat immunity messages (The striking dummy is unaffected)
    9007,   # Status effect application (suffers the effect of)
    13105,  # Status effect recovery (recovers from the effect of)

    # Legacy combat types (keep for safety)
    2091, 2110, 2218, 2219, 2220, 2222, 2224, 2233, 2235, 2240, 2241, 2242,
    2265, 2266, 2267, 2283, 2284, 2285, 2317, 2318, 2730, 2731, 3001,
    8235, 8745, 8746, 8747, 8748, 8749, 8750, 8752, 8754,
    10409, 10410, 10411, 10412, 10413
}

ALLOWED_CHAT_TYPES = {
    61,     # Dialogue
    0x0047,  # Cutscene text (TalkSubtitle addon) - decimal: 71
}

def should_translate_message(message_data):
    """
    Determine if a message should be translated based on ChatType filtering
    ตัดสินใจว่าข้อความควรถูกแปลหรือไม่ตาม ChatType
    """
    chat_type = message_data.get('ChatType', 0)

    # ข้อความที่ห้ามแปล - Block immediately
    if chat_type in BLOCKED_CHAT_TYPES:
        return False

    # ข้อความที่อนุญาต - Allow dialogue
    if chat_type in ALLOWED_CHAT_TYPES:
        return True

    # ตรวจสอบเพิ่มเติมสำหรับ cutscene (จำเป็นต้องเก็บไว้)
    if message_data.get('Type') == 'cutscene':
        return True

    # Default: Allow other message types that aren't explicitly blocked
    return True


class DalamudImmediateHandler:
    def __init__(self, translator=None, ui_updater=None, main_app=None):
        self.translator = translator
        self.ui_updater = ui_updater
        self.main_app = main_app  # 🔧 Reference to main app for force translate
        self.main_app_ref = main_app  # 🔧 CRITICAL FIX: Also store as main_app_ref for compatibility
        self.translated_logs = None  # เพิ่มการเก็บ reference ไปที่ translated_logs


        # Control flags
        self.is_running = False
        self.is_translating = False

        # Translation cache for speed
        self.translation_cache = {}
        self.cache_max_size = 100

        # Store original text for force translate
        self.last_original_text = None  # Store last original text
        self.last_message_data = None   # Store last message data for force translate

        # Current translation tracking
        self.current_translation_thread = None
        self.translating_messages = set()  # Track messages being translated

        # Statistics
        self.stats = {
            'messages_received': 0,
            'messages_translated': 0,
            'cache_hits': 0,
            'immediate_displays': 0,
            'errors': 0
        }

        # Logger
        self.logger = logging.getLogger('DalamudImmediateHandler')

    def start(self):
        """Start the handler"""
        if self.is_running:
            return

        self.is_running = True
        self.logger.info("Dalamud IMMEDIATE Handler started - แสดงทันที!")

    def stop(self):
        """Stop the handler"""
        self.is_running = False
        self.is_translating = False
        self.logger.info("Dalamud IMMEDIATE Handler stopped")

    def set_translation_active(self, active: bool):
        """Set translation active state"""
        self.is_translating = active
        self.logger.info(f"Translation active: {active}")

    def set_translator(self, translator):
        """Set the translator instance"""
        self.translator = translator
        self.logger.info("Translator set")

    def set_ui_updater(self, ui_updater):
        """Set the UI updater function"""
        self.ui_updater = ui_updater
        self.logger.info("UI updater set")

    def set_translated_logs(self, translated_logs):
        """Set the translated logs instance for history logging"""
        self.translated_logs = translated_logs
        self.logger.info("Translated logs instance set")

    def process_message(self, message_data: Dict[str, Any]):
        """
        Process message with IMMEDIATE display
        แสดงคำแปลทันทีเมื่อได้รับข้อความ
        """
        # Input validation - ensure message_data is a dict
        if not isinstance(message_data, dict):
            self.logger.error(f"[SECURITY] Invalid message_data type: {type(message_data)}")
            return

        try:
            # 🚫 TEXT HOOK FILTERING: Check if message should be translated
            chat_type = message_data.get('ChatType', 0)
            self.logger.info(f"[DEBUG FILTER] Checking ChatType {chat_type}")

            if not should_translate_message(message_data):
                self.logger.info(f"[FILTERED] ChatType {chat_type} blocked - not translating")
                return

            # Create message text with input sanitization
            speaker = str(message_data.get('Speaker', '')).strip()[:100]  # Limit speaker name length
            message = str(message_data.get('Message', '')).strip()[:5000]  # Limit message length
            message_text = f"{speaker}: {message}" if speaker else message

            if not message_text.strip():
                return

            # IMPORTANT: Store original text and data BEFORE checking translation state
            # This ensures force translate always has text to work with
            self.last_original_text = message_text
            self.last_message_data = message_data

            # 📝 ORIGINAL TEXT DISPLAY: Send original text to MBB for status display
            if hasattr(self, 'main_app_ref') and self.main_app_ref:
                try:
                    # Update original text display on status line
                    self.main_app_ref.update_original_text_display(message_text)
                except Exception:
                    pass  # Silently ignore errors to avoid breaking translation flow

            # Force translate functionality has been removed - replaced by previous dialog system

            # Now check if we should process for translation
            if not self.is_running or not self.is_translating:
                return

            if not self.translator or not self.ui_updater:
                return

            self.stats['messages_received'] += 1
            cache_key = hash(message_text)

            self.logger.info(f"[รับข้อความ] #{self.stats['messages_received']}: {message_text[:50]}...")

            # Check cache first - if found, show IMMEDIATELY
            if cache_key in self.translation_cache:
                self.logger.info(f"[CACHE HIT] แสดงคำแปลจาก cache ทันที!")
                self.stats['cache_hits'] += 1
                self._show_immediately(self.translation_cache[cache_key])
                return

            # Check if already translating this message
            if cache_key in self.translating_messages:
                self.logger.info(f"[กำลังแปล] ข้อความนี้กำลังแปลอยู่")
                return

            # Start immediate translation
            self.logger.info(f"[เริ่มแปล] เริ่มแปลข้อความใหม่...")
            self.translating_messages.add(cache_key)

            def translate_and_show_immediately():
                try:
                    start_time = time.time()

                    # Update status to show TRANSLATING
                    if hasattr(self, 'main_app_ref') and self.main_app_ref:
                        try:
                            # Set temporary translating state for UI
                            self.main_app_ref._translating_in_progress = True
                            self.main_app_ref.root.after(0, self.main_app_ref.update_info_label_with_model_color)
                        except Exception:
                            pass

                    # Translate
                    translated_text = self.translator.translate(message_text)

                    translation_time = time.time() - start_time
                    self.logger.info(f"[แปลเสร็จ] ใช้เวลา {translation_time:.2f}s: {translated_text[:50]}...")

                    # Cache result
                    self.translation_cache[cache_key] = translated_text
                    if len(self.translation_cache) > self.cache_max_size:
                        first_key = next(iter(self.translation_cache))
                        del self.translation_cache[first_key]

                    self.stats['messages_translated'] += 1

                    # CRITICAL: Show IMMEDIATELY if still translating
                    if self.is_translating and self.is_running:
                        self.logger.info(f"[แสดงทันที] แสดงคำแปลทันที!")
                        self._show_immediately(translated_text)

                        # *** ADD TO HISTORY: เพิ่มข้อความแปลจริงลงใน history สำหรับ Previous Dialog ***
                        if hasattr(self, 'main_app_ref') and self.main_app_ref:
                            try:
                                if hasattr(self.main_app_ref, 'add_to_dialog_history'):
                                    # Extract speaker and message from original
                                    speaker = message_data.get('Speaker', 'Unknown')
                                    self.main_app_ref.add_to_dialog_history(
                                        original_text=message_text,
                                        translated_text=translated_text,
                                        speaker=speaker,
                                        chat_type=message_data.get('ChatType')
                                    )
                                    self.logger.info(f"📄 [REAL HISTORY] Added real translation for '{speaker}'")
                            except Exception as e:
                                self.logger.error(f"❌ [REAL HISTORY] Error adding to history: {e}")

                        # TUI AUTO-SHOW: Trigger directly after successful translation
                        if hasattr(self, 'main_app_ref') and self.main_app_ref:
                            try:
                                if hasattr(self.main_app_ref, '_trigger_tui_auto_show'):
                                    self.main_app_ref._trigger_tui_auto_show()
                            except Exception:
                                pass

                        # 🔧 FORCE STATUS UPDATE: Update main UI status back to READY
                        if hasattr(self, 'main_app_ref') and self.main_app_ref:
                            try:
                                # Clear translating state
                                self.main_app_ref._translating_in_progress = False
                                self.main_app_ref.root.after(0, self.main_app_ref.update_info_label_with_model_color)
                            except:
                                pass  # Fail silently if main app not available
                    else:
                        self.logger.warning(f"[ไม่แสดง] ระบบปิดแล้ว")

                except Exception as e:
                    self.stats['errors'] += 1
                    self.logger.error(f"Translation error: {e}")
                finally:
                    # Clean up tracking
                    self.translating_messages.discard(cache_key)

                    # 🔧 ENSURE CLEANUP: Always clear translating status on completion
                    if hasattr(self, 'main_app_ref') and self.main_app_ref:
                        try:
                            if hasattr(self.main_app_ref, '_translating_in_progress'):
                                self.main_app_ref._translating_in_progress = False
                                self.main_app_ref.root.after(0, self.main_app_ref.update_info_label_with_model_color)
                        except:
                            pass

            # Start translation thread immediately
            thread = threading.Thread(
                target=translate_and_show_immediately,
                daemon=True,
                name=f"ImmediateTranslate-{time.time()}"
            )
            thread.start()

        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Error processing message: {e}")

    def _show_immediately(self, text: str):
        """แสดงข้อความทันทีใน UI โดยไม่มีการหน่วงเวลา"""
        try:
            self.stats['immediate_displays'] += 1
            self.logger.info(f"[UI UPDATE] แสดงใน UI: {text[:50]}...")

            # Call UI updater directly - NO delays!
            if hasattr(self.ui_updater, '__call__'):
                self.ui_updater(text)
                self.logger.info(f"[UI SUCCESS] เรียกฟังก์ชัน UI สำเร็จ")
            else:
                self.ui_updater.update_text(text)
                self.logger.info(f"[UI SUCCESS] เรียกเมธอด update_text สำเร็จ")

            # *** TEXT HOOK INTEGRATION: ส่งข้อมูลไปที่ translated_logs ***
            if self.translated_logs and hasattr(self.translated_logs, 'add_message'):
                try:
                    self.translated_logs.add_message(text)
                    self.logger.info(f"[LOGS SUCCESS] ส่งข้อมูลไป translated_logs สำเร็จ")
                except Exception as logs_error:
                    self.logger.error(f"[LOGS ERROR] ไม่สามารถส่งไป translated_logs: {logs_error}")

            # Force tkinter to update IMMEDIATELY
            if hasattr(self.ui_updater, 'root'):
                self.ui_updater.root.update_idletasks()
                self.ui_updater.root.update()
                self.logger.info(f"[UI FORCED] บังคับอัพเดท tkinter สำเร็จ")

        except Exception as e:
            self.logger.error(f"[UI ERROR] ไม่สามารถแสดง UI: {e}")

    def force_sync(self):
        """
        Force sync - not needed for immediate mode but kept for compatibility
        ไม่จำเป็นในโหมดทันที แต่เก็บไว้เพื่อความเข้ากันได้
        """
        self.logger.info(f"[FORCE SYNC] ไม่จำเป็นในโหมดทันที")
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get handler statistics"""
        return {
            **self.stats,
            'is_running': self.is_running,
            'is_translating': self.is_translating,
            'cache_size': len(self.translation_cache),
            'translating_count': len(self.translating_messages)
        }

    def clear_cache(self):
        """Clear translation cache"""
        self.translation_cache.clear()
        self.translating_messages.clear()
        self.logger.info("Translation cache cleared")

    def force_clear_cache(self):
        """Clear cache specifically for force translate"""
        if self.last_original_text:
            cache_key = hash(self.last_original_text)
            if cache_key in self.translation_cache:
                del self.translation_cache[cache_key]
                self.logger.info(f"[FORCE CLEAR] Cleared cache for force translate")
            # Also remove from translating messages if present
            self.translating_messages.discard(cache_key)
        else:
            self.logger.warning("[FORCE CLEAR] No original text to clear cache for")

    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'messages_received': 0,
            'messages_translated': 0,
            'cache_hits': 0,
            'immediate_displays': 0,
            'errors': 0
        }
        self.logger.info("Statistics reset")


# Factory function
def create_dalamud_immediate_handler(translator=None, ui_updater=None, main_app=None) -> DalamudImmediateHandler:
    """Create and configure a DalamudImmediateHandler instance"""
    handler = DalamudImmediateHandler(translator, ui_updater, main_app)
    return handler