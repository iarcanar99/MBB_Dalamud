"""
MBB Dalamud Bridge - Python Communication Module
เชื่อมต่อระหว่าง Dalamud Plugin กับ MBB Python Application
ใช้ Named Pipes สำหรับการรับข้อมูลจาก FFXIV text hook
"""

import json
import threading
import time
import win32pipe
import win32file
import win32api
from typing import Optional, Dict, Any, Callable
import logging
from dataclasses import dataclass, asdict
from collections import deque

@dataclass
class TextHookData:
    """Data structure for text received from Dalamud plugin"""
    type: str           # "dialogue", "cutscene", "choice", "battle", "system"
    speaker: str        # Character name (empty for narrative)
    message: str        # The actual text content
    timestamp: int      # Unix timestamp
    chat_type: int      # Original XivChatType value

    @classmethod
    def from_dict(cls, data: dict) -> 'TextHookData':
        """Create TextHookData from dictionary"""
        return cls(
            type=data.get('Type', 'unknown'),
            speaker=data.get('Speaker', ''),
            message=data.get('Message', ''),
            timestamp=data.get('Timestamp', 0),
            chat_type=data.get('ChatType', 0)
        )

class DalamudBridge:
    def __init__(self, pipe_name: str = r'\\.\pipe\mbb_dalamud_bridge'):
        self.pipe_name = pipe_name
        self.pipe_handle = None
        self.is_connected = False
        self.is_running = False
        self.text_callback: Optional[Callable] = None
        self.connection_thread = None

        # Message queue for buffering incoming messages
        self.message_queue = deque(maxlen=10)  # Keep last 10 messages
        self.latest_text: Optional[TextHookData] = None
        self.queue_lock = threading.Lock()

        # สำหรับ logging
        self.logger = logging.getLogger('DalamudBridge')
        self.logger.setLevel(logging.DEBUG)

        # 🔧 IMPROVED CONNECTION: Smart reconnection system
        self.consecutive_failures = 0
        self.max_failures_before_backoff = 5  # Fast retries before backing off
        self.max_total_failures = 20  # Total failures before giving up temporarily
        self.base_retry_delay = 2  # Base delay in seconds
        self.max_retry_delay = 30  # Maximum delay between retries
        self.last_connection_attempt = 0
        self.connection_health = "healthy"  # healthy, degraded, failed
        self.backoff_until = 0  # Timestamp when to resume attempts after backoff

        # สถิติการเชื่อมต่อ
        self.stats = {
            'messages_received': 0,
            'connection_attempts': 0,
            'successful_connections': 0,
            'total_failures': 0,
            'last_message_time': None,
            'connection_start_time': None,
            'last_failure_time': None
        }


    def set_text_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """ตั้งค่า callback function สำหรับรับข้อความจาก Dalamud"""
        self.text_callback = callback


    def start(self) -> bool:
        """เริ่มการเชื่อมต่อกับ Dalamud plugin"""
        if self.is_running:
            self.logger.warning("Bridge กำลังทำงานอยู่แล้ว")
            return False

        self.is_running = True
        self.connection_thread = threading.Thread(target=self._connection_loop, daemon=True)
        self.connection_thread.start()

        self.logger.info("Dalamud Bridge started")
        return True

    def stop(self):
        """หยุดการเชื่อมต่อ"""
        self.is_running = False
        self.is_connected = False

        if self.pipe_handle:
            try:
                win32file.CloseHandle(self.pipe_handle)
            except:
                pass
            self.pipe_handle = None

        if self.connection_thread and self.connection_thread.is_alive():
            self.connection_thread.join(timeout=2.0)

        self.logger.info("Dalamud Bridge stopped")

    def _connection_loop(self):
        """🔧 IMPROVED: Smart connection loop with exponential backoff"""
        while self.is_running:
            try:
                # 🔧 SMART RECONNECTION: Check if we should attempt connection
                current_time = time.time()

                # Skip connection attempt if in backoff period
                if current_time < self.backoff_until:
                    time.sleep(1)
                    continue

                # Skip if too many recent failures and not enough time passed
                if (self.consecutive_failures >= self.max_failures_before_backoff and
                    current_time - self.last_connection_attempt < self._get_retry_delay()):
                    time.sleep(1)
                    continue

                # 🔧 IMPROVEMENT: Only attempt connection if not already connected
                if not self.is_connected:
                    self._connect_to_pipe()

                if self.is_connected:
                    # Always call on_success when first connected or recovering
                    if self.consecutive_failures > 0 or self.stats['connection_start_time'] is None:
                        self._on_connection_success()
                    self._read_messages()

            except Exception as e:
                # Only log error if it's not a "file not found" error during normal operation
                if "cannot find the file specified" not in str(e) or self.consecutive_failures < 3:
                    self.logger.error(f"Connection error: {e}")
                self.is_connected = False
                self._on_connection_failure(e)

            # 🔧 IMPROVEMENT: Only attempt reconnection if needed and not in backoff
            if self.is_running and not self.is_connected and current_time >= self.backoff_until:
                retry_delay = self._get_retry_delay()
                self._update_connection_health()

                # Log appropriate message based on health status
                if self.connection_health == "failed":
                    self.logger.warning(f"⚠️ Connection failed - backing off for {retry_delay}s (failures: {self.consecutive_failures}/{self.max_total_failures})")
                    self.backoff_until = time.time() + retry_delay
                elif self.consecutive_failures <= 2:  # Only log debug for first few attempts
                    self.logger.debug(f"Attempting reconnection... ({retry_delay}s)")

                time.sleep(retry_delay)
            elif not self.is_connected:
                # Sleep longer if in backoff to reduce CPU usage
                time.sleep(2)

    def _get_retry_delay(self) -> float:
        """🔧 Calculate exponential backoff delay"""
        if self.consecutive_failures <= self.max_failures_before_backoff:
            # Fast retries for first few failures
            return min(self.base_retry_delay, 2)
        else:
            # Exponential backoff for persistent failures
            backoff_factor = min(2 ** (self.consecutive_failures - self.max_failures_before_backoff), 8)
            return min(self.base_retry_delay * backoff_factor, self.max_retry_delay)

    def _update_connection_health(self):
        """🔧 Update connection health status"""
        if self.consecutive_failures >= self.max_total_failures:
            self.connection_health = "failed"
        elif self.consecutive_failures >= self.max_failures_before_backoff:
            self.connection_health = "degraded"
        else:
            self.connection_health = "healthy"

    def _on_connection_success(self):
        """🔧 Handle successful connection"""
        self.consecutive_failures = 0
        self.connection_health = "healthy"
        self.backoff_until = 0
        self.stats['successful_connections'] += 1
        self.stats['connection_start_time'] = time.time()
        self.logger.info("✅ Connected to Dalamud plugin successfully!")

    def _on_connection_failure(self, error):
        """🔧 Handle connection failure"""
        self.consecutive_failures += 1
        self.stats['total_failures'] += 1
        self.stats['last_failure_time'] = time.time()
        self.last_connection_attempt = time.time()

        # 🔧 IMPROVEMENT: More intelligent logging - less spam for expected failures
        error_str = str(error)
        is_expected_error = "cannot find the file specified" in error_str

        if is_expected_error and self.consecutive_failures > 5:
            # After 5 failed attempts, reduce log frequency for expected errors
            if self.consecutive_failures % 10 == 0:  # Log every 10th failure
                self.logger.info(f"Still waiting for Dalamud plugin... (attempt {self.consecutive_failures})")
        elif self.consecutive_failures <= 3:
            self.logger.debug(f"Connection failed: {error} (attempt {self.consecutive_failures})")
        elif self.consecutive_failures <= self.max_failures_before_backoff:
            self.logger.info(f"Connection failed: {error} (attempt {self.consecutive_failures}) - increasing retry delay")
        else:
            self.logger.warning(f"Connection failed: {error} (attempt {self.consecutive_failures}) - entering backoff mode")

    def _connect_to_pipe(self):
        """เชื่อมต่อกับ named pipe"""
        self.stats['connection_attempts'] += 1

        try:
            # รอ pipe server จาก Dalamud - เพิ่ม timeout สำหรับ stability
            win32pipe.WaitNamedPipe(self.pipe_name, 10000)  # Wait 10 seconds (improved)

            # เปิดการเชื่อมต่อ
            self.pipe_handle = win32file.CreateFile(
                self.pipe_name,
                win32file.GENERIC_READ,
                0,
                None,
                win32file.OPEN_EXISTING,
                0,
                None
            )

            self.is_connected = True
            # Connection success handling is done in _on_connection_success()

        except Exception as e:
            # Connection failure handling is done in _on_connection_failure()
            self.is_connected = False
            raise e  # Re-raise to be handled by connection loop

    def _read_messages(self):
        """อ่านข้อความจาก pipe"""
        buffer = b""

        while self.is_connected and self.is_running:
            try:
                # อ่านข้อมูลจาก pipe
                result, data = win32file.ReadFile(self.pipe_handle, 4096)

                if result == 0 and data:  # สำเร็จ
                    buffer += data
                    self.stats['messages_received'] += 1

                    # แยกข้อความที่สมบูรณ์ (คั่นด้วย \n)
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        if line.strip():
                            # Handle UTF-8 BOM if present
                            try:
                                decoded_line = line.decode('utf-8-sig')  # Auto removes BOM
                            except UnicodeDecodeError:
                                decoded_line = line.decode('utf-8', errors='ignore')
                            self._process_message(decoded_line)

                elif result == 0 and not data:
                    # ไม่มีข้อมูล - รอต่อ (ปรับปรุงความเร็ว: 0.1 → 0.01)
                    time.sleep(0.01)  # Optimized: 10ms instead of 100ms for better response
                    continue

                else:
                    # การเชื่อมต่อขาด
                    self.logger.info("Connection to Dalamud lost")
                    self.is_connected = False
                    break

            except Exception as e:
                self.logger.error(f"Error reading from pipe: {e}")
                self.is_connected = False
                break

        # ปิดการเชื่อมต่อ
        if self.pipe_handle:
            win32file.CloseHandle(self.pipe_handle)
            self.pipe_handle = None

    def _process_message(self, message_str: str):
        """ประมวลผลข้อความที่ได้รับ"""
        try:
            message_data = json.loads(message_str)

            self.stats['messages_received'] += 1
            self.stats['last_message_time'] = time.time()

            self.logger.debug(f"Received message: {message_data.get('Type', 'unknown')} - "
                            f"{message_data.get('Speaker', '')}: {message_data.get('Message', '')[:50]}...")

            # Convert to TextHookData and store
            text_data = TextHookData.from_dict(message_data)

            with self.queue_lock:
                self.message_queue.append(text_data)
                self.latest_text = text_data

            # เรียก callback function (if set)
            if self.text_callback:
                self.logger.debug(f"🔍 DEBUG: Calling text_callback with message_data: {message_data}")
                self.text_callback(message_data)
            else:
                self.logger.warning(f"⚠️ DEBUG: No text_callback set - callback is None")

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
        except Exception as e:
            self.logger.error(f"Message processing error: {e}")

    def get_status(self) -> Dict[str, Any]:
        """ได้รับสถานะปัจจุบันของการเชื่อมต่อ"""
        return {
            'is_connected': self.is_connected,
            'is_running': self.is_running,
            'stats': self.stats.copy(),
            'uptime': time.time() - self.stats['connection_start_time'] if self.stats['connection_start_time'] else 0
        }

    def get_connection_info(self) -> str:
        """ได้รับข้อมูลสถานะในรูปแบบ string"""
        if self.is_connected:
            uptime = time.time() - (self.stats['connection_start_time'] or 0)
            return f"Connected - Received {self.stats['messages_received']} messages - Uptime {uptime:.1f}s"
        elif self.is_running:
            return f"Connecting... (Attempted {self.stats['connection_attempts']} times)"
        else:
            return "Not connected"

    def get_latest_text(self) -> Optional[TextHookData]:
        """Get the latest text received from Dalamud (consumes the message)"""
        with self.queue_lock:
            if self.latest_text:
                text = self.latest_text
                self.latest_text = None  # Consume the message
                return text
        return None

    def get_connection_stats(self) -> Dict[str, Any]:
        """🔧 Get detailed connection statistics"""
        current_time = time.time()
        uptime = (current_time - self.stats['connection_start_time']) if self.stats['connection_start_time'] else 0

        return {
            'health': self.connection_health,
            'is_connected': self.is_connected,
            'consecutive_failures': self.consecutive_failures,
            'total_attempts': self.stats['connection_attempts'],
            'successful_connections': self.stats['successful_connections'],
            'total_failures': self.stats['total_failures'],
            'messages_received': self.stats['messages_received'],
            'uptime_seconds': uptime,
            'last_message_time': self.stats['last_message_time'],
            'success_rate': (self.stats['successful_connections'] / max(self.stats['connection_attempts'], 1)) * 100
        }

    def reset_connection_health(self):
        """🔧 Reset connection health for manual recovery"""
        self.consecutive_failures = 0
        self.connection_health = "healthy"
        self.backoff_until = 0
        self.logger.info("🔄 Connection health manually reset")

    def peek_latest_text(self) -> Optional[TextHookData]:
        """Peek at the latest text without consuming it"""
        with self.queue_lock:
            return self.latest_text

    def get_all_messages(self) -> list[TextHookData]:
        """Get all buffered messages (clears the queue)"""
        with self.queue_lock:
            messages = list(self.message_queue)
            self.message_queue.clear()
            self.latest_text = None
            return messages

    def clear_queue(self):
        """Clear all buffered messages"""
        with self.queue_lock:
            self.message_queue.clear()
            self.latest_text = None


def create_test_callback():
    """สร้าง callback function สำหรับทดสอบ"""
    def test_callback(message_data):
        print(f"[TEST] {message_data.get('Type', 'unknown').upper()}")
        print(f"       Speaker: {message_data.get('Speaker', 'N/A')}")
        print(f"       Message: {message_data.get('Message', 'N/A')}")
        print(f"       Time: {message_data.get('Timestamp', 'N/A')}")
        print("-" * 50)
    return test_callback


if __name__ == "__main__":
    # ทดสอบ bridge แยกต่างหาก
    import sys

    # ตั้งค่า logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("🌉 MBB Dalamud Bridge Test")
    print("=" * 50)
    print("1. เปิด FFXIV และ XIVLauncher")
    print("2. ติดตั้ง DalamudMBBBridge plugin")
    print("3. กด Enter เพื่อเริ่มทดสอบ...")
    input()

    # สร้าง bridge instance
    bridge = DalamudBridge()
    bridge.set_text_callback(create_test_callback())

    try:
        bridge.start()
        print(f"🚀 Bridge เริ่มทำงานแล้ว - รอการเชื่อมต่อจาก Dalamud...")
        print("📝 พิมพ์ 'status' เพื่อดูสถานะ หรือ 'quit' เพื่อออก")

        while True:
            command = input().strip().lower()
            if command == 'quit':
                break
            elif command == 'status':
                print(f"📊 สถานะ: {bridge.get_connection_info()}")
            elif command == '':
                continue
            else:
                print("คำสั่ง: 'status' หรือ 'quit'")

    except KeyboardInterrupt:
        pass
    finally:
        print("\n🛑 กำลังหยุด bridge...")
        bridge.stop()
        print("✅ หยุดแล้ว")