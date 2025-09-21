#!/usr/bin/env python3
"""
Text Hook Simulator
จำลองการส่งข้อความจาก Dalamud text hook เพื่อทดสอบฟีเจอร์ italic text
"""

import os
import sys
import json
import time
import threading
import logging
from datetime import datetime
import win32pipe
import win32file
import win32api

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

class TextHookSimulator:
    """จำลองการทำงานของ Dalamud text hook"""

    def __init__(self):
        self.pipe_name = r'\\.\pipe\mbb_dalamud_bridge'
        self.running = False
        self.test_messages = []
        self.current_index = 0

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

        # Initialize test messages
        self.init_test_messages()

    def init_test_messages(self):
        """เตรียมข้อความทดสอบที่หลากหลาย"""

        self.test_messages = [
            {
                "Type": "dialogue",
                "Speaker": "Alphinaud",
                "Message": "We must *proceed* with caution.",
                "Context": "Basic italic test"
            },
            {
                "Type": "dialogue",
                "Speaker": "Wuk Lamat",
                "Message": "ถึงเวลาจบเรื่องนี้แล้ว Calyx จะไม่หยุด จนกว่าพวก*เรา*จะหยุดเขาเอง",
                "Context": "Thai with italic"
            },
            {
                "Type": "dialogue",
                "Speaker": "Y'shtola",
                "Message": "The *ancient* magic is *powerful* indeed.",
                "Context": "Multiple italic words"
            },
            {
                "Type": "dialogue",
                "Speaker": "Thancred",
                "Message": "*Everything* depends on our next move.",
                "Context": "Entire word italic"
            },
            {
                "Type": "narrative",
                "Speaker": "",
                "Message": "The *mysterious* figure approaches you with *urgent* news.",
                "Context": "Narrative with italic"
            },
            {
                "Type": "dialogue",
                "Speaker": "Krile",
                "Message": "ข้อความ *สำคัญ* มากที่ต้อง *จดจำ* ไว้",
                "Context": "Thai dialogue with multiple italic"
            },
            {
                "Type": "dialogue",
                "Speaker": "Gulool Ja",
                "Message": "Normal text without any special formatting at all.",
                "Context": "Control test - no italic"
            },
            {
                "Type": "dialogue",
                "Speaker": "Estinien",
                "Message": "Mix of *English* and *ไทย* text together.",
                "Context": "Mixed language italic"
            },
            {
                "Type": "choice",
                "Speaker": "",
                "Message": "Choose: *Accept* the quest or *decline* politely?",
                "Context": "Choice dialog with italic"
            },
            {
                "Type": "dialogue",
                "Speaker": "Test Character",
                "Message": "Edge case: **double asterisk** and *normal* and ***triple***",
                "Context": "Edge case testing"
            }
        ]

        self.logger.info(f"📝 Initialized {len(self.test_messages)} test messages")

    def create_named_pipe_server(self):
        """สร้าง Named Pipe Server เพื่อจำลอง Dalamud Bridge"""

        try:
            self.logger.info(f"🔧 Creating named pipe: {self.pipe_name}")

            # สร้าง named pipe
            pipe_handle = win32pipe.CreateNamedPipe(
                self.pipe_name,
                win32pipe.PIPE_ACCESS_DUPLEX,
                win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                1,  # max instances
                65536,  # out buffer size
                65536,  # in buffer size
                0,  # default timeout
                None  # security attributes
            )

            if pipe_handle == win32file.INVALID_HANDLE_VALUE:
                self.logger.error("❌ Failed to create named pipe")
                return None

            self.logger.info("✅ Named pipe created successfully")
            return pipe_handle

        except Exception as e:
            self.logger.error(f"❌ Named pipe creation error: {e}")
            return None

    def wait_for_connection(self, pipe_handle):
        """รอการเชื่อมต่อจาก MBB client"""

        try:
            self.logger.info("⏳ Waiting for MBB client connection...")

            # รอการเชื่อมต่อ
            win32pipe.ConnectNamedPipe(pipe_handle, None)
            self.logger.info("✅ MBB client connected!")
            return True

        except Exception as e:
            self.logger.error(f"❌ Connection wait error: {e}")
            return False

    def send_message(self, pipe_handle, message_data):
        """ส่งข้อความผ่าน named pipe"""

        try:
            # Convert to JSON
            json_data = json.dumps(message_data, ensure_ascii=False)
            message_bytes = json_data.encode('utf-8')

            # ส่งข้อความ
            win32file.WriteFile(pipe_handle, message_bytes)
            self.logger.info(f"📤 Sent: {message_data['Message'][:50]}...")

            return True

        except Exception as e:
            self.logger.error(f"❌ Send message error: {e}")
            return False

    def run_simulation(self, auto_mode=False, delay=3):
        """รันการจำลอง text hook"""

        self.running = True
        self.logger.info("🚀 Starting Text Hook Simulation...")

        # สร้าง named pipe
        pipe_handle = self.create_named_pipe_server()
        if not pipe_handle:
            return

        try:
            # รอการเชื่อมต่อ
            if not self.wait_for_connection(pipe_handle):
                return

            if auto_mode:
                self.run_auto_simulation(pipe_handle, delay)
            else:
                self.run_manual_simulation(pipe_handle)

        except KeyboardInterrupt:
            self.logger.info("⏹️ Simulation stopped by user")

        except Exception as e:
            self.logger.error(f"❌ Simulation error: {e}")

        finally:
            # ปิด pipe
            try:
                win32file.CloseHandle(pipe_handle)
                self.logger.info("🔒 Named pipe closed")
            except:
                pass

            self.running = False

    def run_auto_simulation(self, pipe_handle, delay):
        """รันการจำลองแบบอัตโนมัติ"""

        self.logger.info(f"🔄 Auto simulation mode (delay: {delay}s)")

        for i, message in enumerate(self.test_messages):
            if not self.running:
                break

            self.logger.info(f"📨 Sending message {i+1}/{len(self.test_messages)}")
            self.logger.info(f"🎯 Context: {message['Context']}")

            if not self.send_message(pipe_handle, message):
                break

            if i < len(self.test_messages) - 1:  # ไม่รอหลังข้อความสุดท้าย
                time.sleep(delay)

        self.logger.info("✅ Auto simulation completed")

    def run_manual_simulation(self, pipe_handle):
        """รันการจำลองแบบ manual"""

        self.logger.info("🎮 Manual simulation mode")
        self.logger.info("Commands: 'next', 'prev', 'send', 'list', 'quit'")

        while self.running:
            try:
                command = input(f"\n[{self.current_index+1}/{len(self.test_messages)}] > ").strip().lower()

                if command == 'quit' or command == 'q':
                    break

                elif command == 'next' or command == 'n':
                    self.current_index = (self.current_index + 1) % len(self.test_messages)
                    self.show_current_message()

                elif command == 'prev' or command == 'p':
                    self.current_index = (self.current_index - 1) % len(self.test_messages)
                    self.show_current_message()

                elif command == 'send' or command == 's':
                    message = self.test_messages[self.current_index]
                    self.send_message(pipe_handle, message)

                elif command == 'list' or command == 'l':
                    self.list_all_messages()

                elif command == 'help' or command == 'h':
                    self.show_help()

                elif command == '':
                    self.show_current_message()

                else:
                    print(f"Unknown command: {command}")

            except KeyboardInterrupt:
                break

            except EOFError:
                break

    def show_current_message(self):
        """แสดงข้อความปัจจุบัน"""
        message = self.test_messages[self.current_index]
        print(f"\n--- Message {self.current_index+1}/{len(self.test_messages)} ---")
        print(f"Context: {message['Context']}")
        print(f"Speaker: {message['Speaker']}")
        print(f"Message: {message['Message']}")
        print(f"Type: {message['Type']}")

    def list_all_messages(self):
        """แสดงรายการข้อความทั้งหมด"""
        print("\n--- All Test Messages ---")
        for i, message in enumerate(self.test_messages):
            marker = ">" if i == self.current_index else " "
            print(f"{marker} {i+1:2d}. [{message['Type']}] {message['Context']}")

    def show_help(self):
        """แสดงความช่วยเหลือ"""
        print("\n--- Commands ---")
        print("next/n    - Next message")
        print("prev/p    - Previous message")
        print("send/s    - Send current message")
        print("list/l    - List all messages")
        print("help/h    - Show this help")
        print("quit/q    - Quit simulation")
        print("Enter     - Show current message")

def main():
    """ฟังก์ชั่นหลัก"""

    print("=" * 60)
    print("🎣 TEXT HOOK SIMULATOR")
    print("=" * 60)
    print("This simulator acts as a Dalamud text hook sender")
    print("It creates a named pipe and sends test messages to MBB")
    print("=" * 60)

    simulator = TextHookSimulator()

    # เช็คพารามิเตอร์จาก command line
    if len(sys.argv) > 1:
        if sys.argv[1] == 'auto':
            delay = 3
            if len(sys.argv) > 2:
                try:
                    delay = int(sys.argv[2])
                except ValueError:
                    print(f"Invalid delay value: {sys.argv[2]}, using default: 3")

            print(f"🔄 Running in AUTO mode (delay: {delay}s)")
            print("🎯 Make sure MBB is running first!")
            input("Press Enter when MBB is ready...")

            simulator.run_simulation(auto_mode=True, delay=delay)

        else:
            print(f"Unknown parameter: {sys.argv[1]}")
            print("Usage: python text_hook_simulator.py [auto [delay]]")

    else:
        print("🎮 Running in MANUAL mode")
        print("🎯 Make sure MBB is running first!")
        input("Press Enter when MBB is ready...")

        simulator.run_simulation(auto_mode=False)

    print("👋 Text Hook Simulator finished")

if __name__ == "__main__":
    main()