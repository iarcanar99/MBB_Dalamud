import os
import openai
import time
import json
import logging
from dotenv import load_dotenv

class APIManager:
    def __init__(self):
        # ตั้งค่า logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        self.config_file = 'api_config.json'
        self.load_config()
        self.initialize_openai()

    def load_config(self):
        """โหลดหรือสร้าง config file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except Exception as e:
                logging.error(f"Error loading config: {e}")
                self.config = self._create_default_config()
        else:
            self.config = self._create_default_config()
            self.save_config()

    def _create_default_config(self):
        """สร้าง config เริ่มต้น"""
        return {
            'last_reset': time.time(),
            'api_key': os.getenv('OPENAI_API_KEY', ''),
            'status': 'unknown'
        }

    def save_config(self):
        """บันทึก config"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Failed to save config: {e}")

    def initialize_openai(self):
        """เริ่มต้นการใช้งาน OpenAI"""
        load_dotenv()
        current_key = os.getenv('OPENAI_API_KEY')
        if current_key:
            openai.api_key = current_key
            self.config['api_key'] = current_key
            self.save_config()

    def reset_api_key(self):
        """รีเซ็ต API key โดยโหลดจาก .env ใหม่"""
        print("\nกำลังรีเซ็ต API key...")
        try:
            # รีโหลด .env file
            load_dotenv()
            new_key = os.getenv('OPENAI_API_KEY')
            
            if not new_key:
                raise ValueError("ไม่พบ API key ใน .env file")
            
            if new_key != self.config['api_key']:
                openai.api_key = new_key
                self.config['api_key'] = new_key
                self.config['last_reset'] = time.time()
                self.save_config()
                print("✓ รีเซ็ต API key สำเร็จ")
                return True
            else:
                print("! API key ไม่มีการเปลี่ยนแปลง (key เดิม)")
                return False
                
        except Exception as e:
            print(f"✗ ไม่สามารถรีเซ็ต API key: {e}")
            return False

    def check_api_status(self):
        """ตรวจสอบสถานะ API key"""
        print("\nกำลังตรวจสอบ API key...")
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            self.config['status'] = 'active'
            self.save_config()
            print("✓ API key ใช้งานได้")
            return True
        except Exception as e:
            error_msg = str(e)
            if 'insufficient_quota' in error_msg:
                status = "insufficient quota"
                print("✗ API key เครดิตหมด")
            elif 'invalid_api_key' in error_msg:
                status = "invalid key"
                print("✗ API key ไม่ถูกต้อง")
            else:
                status = "error"
                print(f"✗ เกิดข้อผิดพลาด: {error_msg}")
            
            self.config['status'] = status
            self.save_config()
            return False

    def show_status(self):
        """แสดงข้อมูลสถานะทั้งหมด"""
        print("\n=== สถานะ API ===")
        print(f"สถานะ: {self.config.get('status', 'unknown')}")
        last_reset = time.ctime(self.config.get('last_reset', 0))
        print(f"รีเซ็ตล่าสุด: {last_reset}")
        
        # แสดงส่วนท้ายของ API key
        api_key = self.config.get('api_key', '')
        if api_key:
            visible_part = f"...{api_key[-4:]}"
            print(f"API key: {visible_part}")
        else:
            print("API key: ไม่พบ key")

def main():
    api_manager = APIManager()
    
    while True:
        print("\n=== จัดการ OpenAI API ===")
        print("1. รีเซ็ต API key")
        print("2. ตรวจสอบสถานะ API")
        print("3. แสดงข้อมูลสถานะ")
        print("0. ออกจากโปรแกรม")
        
        choice = input("\nเลือกคำสั่ง (0-3): ").strip()
        
        if choice == '1':
            api_manager.reset_api_key()
        elif choice == '2':
            api_manager.check_api_status()
        elif choice == '3':
            api_manager.show_status()
        elif choice == '0':
            print("\nจบการทำงาน")
            break
        else:
            print("\n! โปรดเลือกคำสั่งที่ถูกต้อง")

if __name__ == "__main__":
    main()