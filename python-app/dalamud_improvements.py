"""
Dalamud Bridge Improvements Module
Provides enhanced functionality for handling text hook messages
"""

import time
import threading
from typing import Optional, Callable, Any
from collections import deque
from dataclasses import dataclass, field

@dataclass
class MessageBuffer:
    """Enhanced message buffer with debouncing and priority handling"""
    max_size: int = 20
    debounce_time: float = 0.3  # seconds to wait for message stability
    messages: deque = field(default_factory=lambda: deque(maxlen=20))
    last_message_time: float = 0
    last_processed_message: str = ""
    lock: threading.Lock = field(default_factory=threading.Lock)

    def add_message(self, message: str, message_type: str = "dialogue"):
        """Add a message with debouncing logic"""
        with self.lock:
            current_time = time.time()

            # Skip if duplicate of last processed
            if message == self.last_processed_message:
                return False

            # Add to buffer
            self.messages.append({
                'text': message,
                'type': message_type,
                'timestamp': current_time
            })

            self.last_message_time = current_time
            return True

    def get_stable_message(self) -> Optional[dict]:
        """Get message if stable (no new messages for debounce_time)"""
        with self.lock:
            if not self.messages:
                return None

            current_time = time.time()
            if current_time - self.last_message_time >= self.debounce_time:
                # Message is stable, return the latest
                message = self.messages[-1]
                self.last_processed_message = message['text']
                self.messages.clear()
                return message

            return None

    def force_get_latest(self) -> Optional[dict]:
        """Force get the latest message without waiting for stability"""
        with self.lock:
            if self.messages:
                message = self.messages[-1]
                self.last_processed_message = message['text']
                self.messages.clear()
                return message
            return None


class DalamudMessageHandler:
    """Enhanced message handler with intelligent processing"""

    def __init__(self, translation_callback: Callable[[str], Any]):
        self.translation_callback = translation_callback
        self.message_buffer = MessageBuffer()
        self.dialogue_history = deque(maxlen=10)
        self.is_in_cutscene = False
        self.rapid_message_mode = False
        self.last_speaker = ""

    def process_text_hook(self, text_data) -> bool:
        """Process incoming text hook with intelligent handling"""

        # Determine message type and priority
        message_type = text_data.type if hasattr(text_data, 'type') else 'unknown'
        speaker = text_data.speaker if hasattr(text_data, 'speaker') else ''
        message = text_data.message if hasattr(text_data, 'message') else ''

        # Format the full message
        if speaker and speaker.strip():
            full_message = f"{speaker}: {message}"
        else:
            full_message = message

        # Detect rapid dialogue (cutscene mode)
        self._detect_rapid_mode(speaker)

        # Add to buffer
        added = self.message_buffer.add_message(full_message, message_type)

        if not added:
            return False  # Duplicate message

        # Decide processing strategy
        if self.rapid_message_mode:
            # In rapid mode, use longer debounce
            self.message_buffer.debounce_time = 0.5
        else:
            # Normal mode, shorter debounce
            self.message_buffer.debounce_time = 0.3

        return True

    def get_ready_message(self) -> Optional[str]:
        """Get a message that's ready for translation"""

        # Check for stable message
        stable_msg = self.message_buffer.get_stable_message()
        if stable_msg:
            self._add_to_history(stable_msg['text'])
            return stable_msg['text']

        return None

    def force_process(self) -> Optional[str]:
        """Force process the latest message immediately"""
        latest = self.message_buffer.force_get_latest()
        if latest:
            self._add_to_history(latest['text'])
            return latest['text']
        return None

    def _detect_rapid_mode(self, speaker: str):
        """Detect if we're in rapid dialogue mode (cutscene)"""
        if speaker != self.last_speaker:
            # Speaker changed, might be rapid dialogue
            self.rapid_message_mode = True
            threading.Timer(2.0, self._reset_rapid_mode).start()
        self.last_speaker = speaker

    def _reset_rapid_mode(self):
        """Reset rapid mode after timeout"""
        self.rapid_message_mode = False

    def _add_to_history(self, message: str):
        """Add message to history for context"""
        self.dialogue_history.append({
            'text': message,
            'timestamp': time.time()
        })


class ReconnectionManager:
    """Manages automatic reconnection for Dalamud Bridge"""

    def __init__(self, bridge, max_retries: int = 5, retry_delay: float = 5.0):
        self.bridge = bridge
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_count = 0
        self.is_reconnecting = False
        self.reconnect_thread = None

    def monitor_connection(self):
        """Monitor connection and trigger reconnection if needed"""
        if not self.bridge.is_connected and not self.is_reconnecting:
            self.start_reconnection()

    def start_reconnection(self):
        """Start reconnection process"""
        if self.is_reconnecting:
            return

        self.is_reconnecting = True
        self.reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
        self.reconnect_thread.start()

    def _reconnect_loop(self):
        """Reconnection loop with exponential backoff"""
        while self.retry_count < self.max_retries and not self.bridge.is_connected:
            self.retry_count += 1
            delay = self.retry_delay * (1.5 ** (self.retry_count - 1))  # Exponential backoff

            print(f"[Dalamud] Reconnection attempt {self.retry_count}/{self.max_retries} in {delay:.1f}s...")
            time.sleep(delay)

            try:
                self.bridge.stop()
                time.sleep(1)
                self.bridge.start()

                # Wait a bit to see if connection succeeds
                time.sleep(3)

                if self.bridge.is_connected:
                    print("[Dalamud] Reconnection successful!")
                    self.retry_count = 0
                    break

            except Exception as e:
                print(f"[Dalamud] Reconnection error: {e}")

        self.is_reconnecting = False

        if not self.bridge.is_connected:
            print(f"[Dalamud] Failed to reconnect after {self.max_retries} attempts")


def create_enhanced_dalamud_handler(mbb_instance):
    """Factory function to create enhanced Dalamud handler for MBB"""

    def translation_callback(text):
        """Callback to trigger translation in MBB"""
        if hasattr(mbb_instance, 'translate_and_display_directly'):
            mbb_instance.translate_and_display_directly(text)

    handler = DalamudMessageHandler(translation_callback)
    return handler