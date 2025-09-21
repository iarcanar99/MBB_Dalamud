import json
import os
import time


def get_files(target_path, extensions):
    """
    รับพาธโฟลเดอร์และรายชื่อสกุลไฟล์ที่ต้องการ เช่น ['.json', '.txt', '.py']
    คืนค่าเป็น list ของ dict ที่มีข้อมูล:
      - 'full_path': พาธไฟล์เต็ม
      - 'name': ชื่อไฟล์
      - 'size': ขนาดไฟล์ (bytes)
      - 'modified': วันที่แก้ไขล่าสุด (timestamp)
    """
    files_info = []
    if not os.path.isdir(target_path):
        return files_info

    for root, dirs, files in os.walk(target_path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in extensions:
                full_path = os.path.join(root, file)
                try:
                    size = os.path.getsize(full_path)
                    modified = os.path.getmtime(full_path)
                except Exception as e:
                    size = 0
                    modified = 0
                files_info.append(
                    {
                        "full_path": full_path,
                        "name": file,
                        "size": size,
                        "modified": modified,
                    }
                )
        # ไม่วนลูปซับโฟลเดอร์ลึกเกินไป (optional)
        break
    return files_info


def rename_file(old_full_path, new_name_without_ext):
    """
    ทำการเปลี่ยนชื่อไฟล์ โดย new_name_without_ext คือชื่อใหม่โดยไม่รวมสกุล
    ดึงสกุลจาก old_full_path มาอัตโนมัติ
    คืนค่า True ถ้าสำเร็จ, False หากมีปัญหา
    """
    dir_path = os.path.dirname(old_full_path)
    base, ext = os.path.splitext(os.path.basename(old_full_path))
    new_full_name = new_name_without_ext + ext
    new_full_path = os.path.join(dir_path, new_full_name)
    try:
        os.rename(old_full_path, new_full_path)
        return True, new_full_path
    except Exception as e:
        print(f"Error renaming file: {e}")
        return False, old_full_path


def format_size(size_bytes):
    """
    ฟังก์ชันช่วยจัดรูปแบบขนาดไฟล์ให้อ่านง่าย
    """
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int((len(str(size_bytes)) - 1) // 3)
    p = 1024**i
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


def format_timestamp(timestamp):
    """
    ฟังก์ชันช่วยจัดรูปแบบเวลาที่แก้ไขล่าสุดให้อ่านง่าย
    """
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))


def read_json_file(filepath):
    """
    อ่านข้อมูลจากไฟล์ JSON
    คืนค่าเป็น dict ของข้อมูล หรือ None ถ้าเกิดข้อผิดพลาด
    """
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return None


def write_json_file(filepath, data):
    """
    เขียนข้อมูลลงไฟล์ JSON
    คืนค่า True ถ้าสำเร็จ, False ถ้าเกิดข้อผิดพลาด
    """
    try:
        with open(filepath, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error writing JSON file: {e}")
        return False


def get_game_info_from_json(filepath):
    """
    อ่านข้อมูลเกมจาก hint ในไฟล์ JSON
    คืนค่าเป็น dict ของข้อมูลเกม หรือ None ถ้าไม่พบข้อมูล
    """
    try:
        data = read_json_file(filepath)
        if data and "_game_info" in data:
            return data["_game_info"]
        return None
    except Exception as e:
        print(f"Error getting game info: {e}")
        return None


def add_game_info_to_json(filepath, game_name, game_code, description=None):
    """
    เพิ่มข้อมูลเกมลงในไฟล์ JSON
    คืนค่า True ถ้าสำเร็จ, False ถ้าเกิดข้อผิดพลาด
    """
    try:
        data = read_json_file(filepath)
        if not data:
            return False

        game_info = {
            "name": game_name,
            "code": game_code,
            "description": description or f"ข้อมูล NPC จากเกม {game_name}",
        }

        # อัพเดทข้อมูลเกม
        data["_game_info"] = game_info

        # เขียนข้อมูลกลับไปยังไฟล์
        return write_json_file(filepath, data)
    except Exception as e:
        print(f"Error adding game info: {e}")
        return False


def swap_npc_files(current_filepath, target_filepath):
    """
    สลับไฟล์ NPC โดยใช้ข้อมูล hint ในไฟล์
    คืนค่า (success, error_message)
    """
    try:
        # อ่านข้อมูล hint จากทั้งสองไฟล์
        current_info = get_game_info_from_json(current_filepath)
        target_info = get_game_info_from_json(target_filepath)

        # ตรวจสอบว่าทั้งสองไฟล์มี hint หรือไม่
        if not current_info:
            return False, "ไฟล์ NPC.json ปัจจุบันไม่มีข้อมูลเกม กรุณาระบุก่อนสลับไฟล์"

        if not target_info:
            return False, "ไฟล์เป้าหมายไม่มีข้อมูลเกม กรุณาระบุก่อนสลับไฟล์"

        # ตรวจสอบว่าไม่เป็นรหัสเกม "unknown"
        if current_info.get("code") == "unknown":
            return False, "ไฟล์ NPC.json มีรหัสเกมไม่ชัดเจน (unknown) กรุณาระบุข้อมูลเกมที่ถูกต้อง"

        if target_info.get("code") == "unknown":
            return False, "ไฟล์เป้าหมายมีรหัสเกมไม่ชัดเจน (unknown) กรุณาระบุข้อมูลเกมที่ถูกต้อง"

        # สร้างชื่อไฟล์ตามข้อมูล hint
        current_dir = os.path.dirname(current_filepath)
        current_code = current_info.get("code")

        # ชื่อไฟล์ใหม่สำหรับไฟล์ปัจจุบัน (NPC.json)
        new_current_filename = f"npc_{current_code}.json"
        new_current_filepath = os.path.join(current_dir, new_current_filename)

        # ตรวจสอบว่ามีไฟล์ชื่อนี้อยู่แล้วหรือไม่
        if (
            os.path.exists(new_current_filepath)
            and new_current_filepath != target_filepath
        ):
            # มีไฟล์อยู่แล้ว และไม่ใช่ไฟล์เป้าหมาย - ป้องกันการทับไฟล์อื่น
            return False, f"มีไฟล์ชื่อ {new_current_filename} อยู่แล้ว กรุณาเปลี่ยนชื่อก่อนสลับไฟล์"

        # ใช้ไฟล์ temp เพื่อสลับ
        temp_filepath = current_filepath + ".temp"

        print(f"สลับไฟล์: {current_filepath} <-> {target_filepath}")
        print(f"ชื่อใหม่: {new_current_filepath}")

        # เปลี่ยนชื่อไฟล์ปัจจุบันเป็นไฟล์ชั่วคราว
        os.rename(current_filepath, temp_filepath)

        # เปลี่ยนชื่อไฟล์เป้าหมายเป็นไฟล์ปัจจุบัน
        os.rename(target_filepath, current_filepath)

        # เปลี่ยนชื่อไฟล์ชั่วคราวเป็นไฟล์ตามโค้ดเกม
        os.rename(temp_filepath, new_current_filepath)

        return True, ""
    except Exception as e:
        error_msg = f"เกิดข้อผิดพลาดในการสลับไฟล์: {str(e)}"
        print(error_msg)
        return False, error_msg


def create_new_npc_file(filepath, game_name):
    """
    สร้างไฟล์ NPC.json ใหม่สำหรับเกมที่ระบุ

    Args:
        filepath: พาธของไฟล์ NPC.json เป้าหมาย
        game_name: ชื่อเกมที่ต้องการสร้าง

    Returns:
        tuple: (bool, str) - สถานะความสำเร็จและข้อความ
    """
    try:
        # สร้างรหัสเกมอัตโนมัติจากชื่อเกม
        game_code = game_name.lower().replace(" ", "_")
        if len(game_code) > 10:
            game_code = game_code[:10]

        # สร้างโครงสร้างไฟล์ NPC ใหม่ตามตัวอย่าง Monster Hunter ที่ใช้งานได้
        new_npc_data = {
            "main_characters": [
                {
                    "firstName": f"Main Character",
                    "lastName": "",
                    "gender": "Unknown",
                    "role": "Protagonist",
                    "relationship": "Player",
                }
            ],
            "npcs": [
                {
                    "name": "Sample NPC",
                    "role": "Villager",
                    "description": "A sample NPC for your new game",
                }
            ],
            "lore": {"Game World": f"World of {game_name}"},
            "character_roles": {"Main Character": "พูดจาสุภาพ เป็นกันเอง"},
            "word_fixes": {},
            "_game_info": {
                "name": game_name,
                "code": game_code,
                "description": f"ข้อมูล NPC จากเกม {game_name}",
            },
        }

        # เขียนไฟล์ใหม่
        success = write_json_file(filepath, new_npc_data)

        if success:
            return True, f"สร้างไฟล์ NPC สำหรับเกม {game_name} เรียบร้อยแล้ว"
        else:
            return False, "ไม่สามารถสร้างไฟล์ NPC ใหม่ได้"

    except Exception as e:
        error_msg = f"เกิดข้อผิดพลาดในการสร้างไฟล์ NPC ใหม่: {str(e)}"
        print(error_msg)
        return False, error_msg
