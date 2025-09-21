import sys
import os
import json  # เพิ่มเพื่อจัดการไฟล์ JSON
import time  # มีอยู่แล้วแต่เพิ่มเพื่อความชัดเจน

# กำหนด path เพื่อให้สามารถนำเข้าโมดูลในโฟลเดอร์เดียวกันได้
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QPushButton,
    QFileDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QDialog,
    QRadioButton,
    QFrame,
    QButtonGroup,
    QTextEdit,
    QScrollArea,
    QSizePolicy,
)
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QColor, QPainter, QBrush, QFont
import tkinter as tk  # Add missing tkinter import

# นำเข้าฟังก์ชันจาก Manager.py
from Manager import (
    get_files,
    rename_file,
    format_size,
    format_timestamp,
    read_json_file,
    write_json_file,
    get_game_info_from_json,
    add_game_info_to_json,
    swap_npc_files,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Manager App")
        self.setGeometry(100, 100, 900, 700)
        self.setWindowFlags(Qt.FramelessWindowHint)  # ไร้ขอบวินโดว์
        self.target_path = ""
        self.extensions = {".json": True}
        self.file_data = []

        # Set application-wide font for Thai support
        from PyQt5.QtGui import QFont
        import locale

        # Set locale for Thai support
        try:
            locale.setlocale(locale.LC_ALL, 'th_TH.UTF-8')
        except:
            try:
                locale.setlocale(locale.LC_ALL, 'Thai_Thailand.874')
            except:
                pass

        # Create font that definitely supports Thai
        font = QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(10)
        font.setStyleHint(QFont.System)
        QApplication.instance().setFont(font)

        self.init_ui()
        self.setup_timer()

        # โหลดไดเร็กทอรีล่าสุด
        self.load_last_directory()

    def init_ui(self):
        # Main container widget
        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
        self.main_widget.setStyleSheet(
            """
            background-color: #2e2e2e;
            color: #ffffff;
            font-family: "Segoe UI", "Tahoma", "MS Sans Serif", sans-serif;
            font-size: 12pt;
        """
        )

        # ปุ่มปิดโปรแกรม (อยู่มุมบนขวาสุด)
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)  # ลดระยะห่างเพื่อให้ปุ่มอยู่ชิดขอบบนขวา
        self.btn_close = QPushButton("", self)
        self.btn_close.setFixedSize(15, 15)
        self.btn_close.setStyleSheet(
            """
            QPushButton {
                background-color: #e74c3c;
                border-radius: 7px;
                border: none;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            """
        )
        self.btn_close.clicked.connect(self.close)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_close)
        self.main_layout.addLayout(top_bar)

        # แถวด้านบนสำหรับปุ่ม Select Folder และ Swap Data
        buttons_row = QHBoxLayout()
        buttons_row.setContentsMargins(10, 5, 10, 5)

        # ปุ่ม Select Folder (เปลี่ยนจาก START)
        self.btn_select_path = QPushButton("Select Folder", self)
        self.btn_select_path.setStyleSheet(
            """
            QPushButton {
                background-color: #4a4a4a;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-size: 16pt;
            }
            QPushButton:hover {
                background-color: #6a6a6a;
            }
            """
        )
        self.btn_select_path.clicked.connect(self.select_path)
        buttons_row.addWidget(self.btn_select_path)

        # เพิ่มปุ่ม Swap Data (มีอยู่แล้ว)
        self.btn_swap_data = QPushButton("Swap Data", self)
        self.btn_swap_data.setStyleSheet(
            """
            QPushButton {
                background-color: #2980b9;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-size: 16pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
            """
        )
        self.btn_swap_data.clicked.connect(self.swap_data_files)
        buttons_row.addWidget(self.btn_swap_data)

        # เพิ่มปุ่ม "เพิ่มเกมส์ใหม่"
        self.btn_new_game = QPushButton("เพิ่มเกมส์ใหม่", self)
        self.btn_new_game.setStyleSheet(
            """
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-size: 16pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            """
        )
        self.btn_new_game.clicked.connect(self.create_new_game)
        buttons_row.addWidget(self.btn_new_game)

        # เพิ่ม stretch เพื่อให้ปุ่มอยู่ชิดซ้าย (มีอยู่แล้ว คงไว้เพื่อความเข้าใจ)
        buttons_row.addStretch()

        self.main_layout.addLayout(buttons_row)

        # แสดง path ที่เลือกเป็นตัวเล็กๆ
        path_layout = QHBoxLayout()
        self.lbl_selected_path = QLabel("", self)
        self.lbl_selected_path.setStyleSheet("font-size: 11pt; color: #cccccc; font-family: 'Segoe UI', sans-serif; padding: 3px;")
        path_layout.addWidget(self.lbl_selected_path)
        self.main_layout.addLayout(path_layout)

        # Info label for JSON only support
        info_layout = QHBoxLayout()
        info_label = QLabel("รองรับเฉพาะไฟล์ JSON เท่านั้น", self)
        info_label.setStyleSheet("font-size: 12pt; color: #1abc9c; font-weight: bold; font-family: 'Segoe UI', sans-serif; padding: 5px;")
        info_layout.addStretch(1)
        info_layout.addWidget(info_label)
        info_layout.addStretch(1)
        self.main_layout.addLayout(info_layout)

        # Scroll area for cards
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(
            """
            QScrollArea {
                background-color: #2e2e2e;
                border: none;
            }
            QScrollBar:vertical {
                background: #2e2e2e;
                width: 14px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #4a4a4a;
                min-height: 24px;
                border-radius: 6px;
            }
            """
        )

        self.cards_widget = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_widget)
        self.cards_layout.setSpacing(15)
        self.cards_layout.setContentsMargins(25, 15, 25, 15)

        self.scroll_area.setWidget(self.cards_widget)
        self.main_layout.addWidget(self.scroll_area)

        # Label สำหรับแสดงข้อความสถานะ (จัดกลาง)
        self.lbl_status = QLabel("", self)
        self.lbl_status.setStyleSheet("color: #00ff00; font-size: 12pt; font-family: 'Segoe UI', sans-serif; padding: 5px;")
        self.main_layout.addWidget(self.lbl_status, alignment=Qt.AlignCenter)

    def setup_timer(self):
        # Timer เพื่อรีเฟรชไฟล์ใน target path ทุก ๆ 10 วินาที
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_file_list)
        self.timer.start(10000)

    def select_path(self):
        path = QFileDialog.getExistingDirectory(self, "เลือกโฟลเดอร์")
        if path:
            self.target_path = path
            self.refresh_file_list()
            # อัปเดตแสดง path ที่เลือก
            self.lbl_selected_path.setText(f"โฟลเดอร์ปัจจุบัน: {path}")
            # บันทึกไดเร็กทอรีล่าสุด
            self.save_last_directory()


    def refresh_file_list(self):
        if not self.target_path:
            return

        active_extensions = [ext for ext, active in self.extensions.items() if active]
        files = get_files(self.target_path, active_extensions)
        self.file_data = files
        self.populate_cards()


    def populate_cards(self):
        # Clear existing cards
        for i in reversed(range(self.cards_layout.count())):
            child = self.cards_layout.itemAt(i).widget()
            if child:
                child.deleteLater()

        # Create cards for each JSON file
        valid_game_count = 0
        for file in self.file_data:
            if file["name"].lower().endswith('.json'):
                # Check if this is a valid game database
                game_info = get_game_info_from_json(file["full_path"])
                game_name = game_info.get("name", "Unknown Game") if game_info else "Unknown Game"

                # Skip files that are not game databases (Unknown Game)
                if game_name != "Unknown Game":
                    card = self.create_game_card(file)
                    self.cards_layout.addWidget(card)
                    valid_game_count += 1

        # Add info if no valid games found
        if valid_game_count == 0:
            no_games_label = QLabel("ไม่พบฐานข้อมูลเกมในโฟลเดอร์นี้")
            no_games_label.setStyleSheet(
                "font-size: 14pt; color: #95a5a6; text-align: center; padding: 20px;"
            )
            no_games_label.setAlignment(Qt.AlignCenter)
            self.cards_layout.addWidget(no_games_label)

        # Add stretch at the end
        self.cards_layout.addStretch()

    def create_game_card(self, file):
        """Create a simple card for each JSON file"""

        # Get game information
        game_info = get_game_info_from_json(file["full_path"])
        game_name = game_info.get("name", "Unknown Game") if game_info else "Unknown Game"
        char_count = self.count_characters_in_json(file["full_path"])

        # Create card with horizontal layout
        card = QFrame()
        card.setStyleSheet(
            """
            QFrame {
                background-color: #3e3e3e;
                padding: 15px 20px;
                margin: 5px;
                border: 1px solid #555555;
                border-radius: 8px;
            }
            QFrame:hover {
                background-color: #4a4a4a;
                border: 1px solid #1abc9c;
            }
            """
        )
        card.setMinimumHeight(50)

        # Create horizontal layout
        layout = QHBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Game name (bold and colored)
        name_label = QLabel(game_name)
        name_label.setStyleSheet(
            """
            QLabel {
                color: #e74c3c;
                font-weight: bold;
                font-size: 13pt;
                border: none;
                background: transparent;
            }
            """
        )
        layout.addWidget(name_label)

        # Separator
        sep1 = QLabel("|")
        sep1.setStyleSheet("color: #7f8c8d; border: none; background: transparent;")
        layout.addWidget(sep1)

        # Character count
        char_label = QLabel(f"{char_count} ตัวละคร")
        char_label.setStyleSheet(
            """
            QLabel {
                color: #ffffff;
                font-size: 12pt;
                border: none;
                background: transparent;
            }
            """
        )
        layout.addWidget(char_label)

        # Separator
        sep2 = QLabel("|")
        sep2.setStyleSheet("color: #7f8c8d; border: none; background: transparent;")
        layout.addWidget(sep2)

        # File name
        file_label = QLabel(file['name'])
        file_label.setStyleSheet(
            """
            QLabel {
                color: #bdc3c7;
                font-size: 11pt;
                border: none;
                background: transparent;
            }
            """
        )
        layout.addWidget(file_label)

        # Separator
        sep3 = QLabel("|")
        sep3.setStyleSheet("color: #7f8c8d; border: none; background: transparent;")
        layout.addWidget(sep3)

        # File size
        size_label = QLabel(format_size(file["size"]))
        size_label.setStyleSheet(
            """
            QLabel {
                color: #95a5a6;
                font-size: 11pt;
                border: none;
                background: transparent;
            }
            """
        )
        layout.addWidget(size_label)

        # Add stretch to push everything to the left
        layout.addStretch()

        # Store file path for click handling
        card.file_path = file["full_path"]
        card.mousePressEvent = lambda event: self.handle_card_click(card.file_path)

        return card

    def count_characters_in_json(self, filepath):
        """Count the number of characters in a JSON file from main_characters"""
        try:
            data = read_json_file(filepath)
            if not data:
                return 0

            # Check if there's a main_characters key
            if isinstance(data, dict) and "main_characters" in data:
                main_chars = data["main_characters"]
                if isinstance(main_chars, list):
                    return len(main_chars)
                else:
                    return 0
            else:
                # Fallback: count all non-metadata entries
                if isinstance(data, dict):
                    filtered_data = {k: v for k, v in data.items() if not k.startswith('_')}
                    return len(filtered_data)
                elif isinstance(data, list):
                    return len(data)
                else:
                    return 0
        except Exception as e:
            print(f"Error counting characters: {e}")
            return 0

    def handle_card_click(self, file_path):
        """Handle clicking on a card"""
        # You can implement editing functionality here if needed
        pass


    def save_last_directory(self):
        """บันทึกไดเร็กทอรีล่าสุดที่ทำงาน"""
        try:
            if self.target_path:
                with open("last_directory.txt", "w", encoding="utf-8") as file:
                    file.write(self.target_path)
        except Exception as e:
            print(f"Error saving last directory: {e}")

    def load_last_directory(self):
        """โหลดไดเร็กทอรีล่าสุดที่ทำงาน"""
        try:
            if os.path.exists("last_directory.txt"):
                with open("last_directory.txt", "r", encoding="utf-8") as file:
                    path = file.read().strip()
                    if os.path.isdir(path):
                        self.target_path = path
                        # อัปเดตแสดง path ที่โหลด
                        self.lbl_selected_path.setText(f"โฟลเดอร์ปัจจุบัน: {path}")
                        self.refresh_file_list()
                        return True
            return False
        except Exception as e:
            print(f"Error loading last directory: {e}")
            return False

    def swap_data_files(self):
        """แสดงหน้าต่างสำหรับสลับไฟล์ข้อมูล NPC"""
        try:
            # ตรวจสอบว่ามีโฟลเดอร์ที่ทำงานอยู่หรือไม่
            if not self.target_path:
                QMessageBox.warning(self, "คำเตือน", "กรุณาเลือกโฟลเดอร์ก่อน")
                return

            # ค้นหาไฟล์ NPC.json และไฟล์ NPC อื่นๆ ในโฟลเดอร์
            npc_files = []
            npc_main_file = None

            # เฉพาะไฟล์ในโฟลเดอร์หลัก (ไม่รวมโฟลเดอร์ย่อย)
            for file in os.listdir(self.target_path):
                # ตรวจสอบว่าเป็นไฟล์ (ไม่ใช่โฟลเดอร์) และเป็น .json ที่มีคำว่า npc ในชื่อ
                if (
                    os.path.isfile(os.path.join(self.target_path, file))
                    and file.lower().endswith(".json")
                    and "npc" in file.lower()
                ):
                    full_path = os.path.join(self.target_path, file)

                    # แยกไฟล์หลัก (NPC.json) กับไฟล์อื่นๆ
                    if file.lower() == "npc.json":
                        npc_main_file = full_path
                    else:
                        npc_files.append(full_path)

            # ตรวจสอบว่าพบไฟล์ NPC.json หรือไม่
            if not npc_main_file:
                QMessageBox.warning(self, "คำเตือน", "ไม่พบไฟล์ NPC.json ในโฟลเดอร์นี้")
                return

            # ตรวจสอบว่าพบไฟล์ NPC อื่นๆ หรือไม่
            if not npc_files:
                QMessageBox.warning(self, "คำเตือน", "ไม่พบไฟล์ NPC อื่นๆ ในโฟลเดอร์นี้")
                return

            # ตรวจสอบ hint ในไฟล์หลักก่อน (ส่วนสำคัญที่ต้องทำงานถูกต้อง)
            print("กำลังตรวจสอบ hint ในไฟล์ NPC.json...")
            main_file_info = get_game_info_from_json(npc_main_file)

            # ★★★ จุดสำคัญ: ถ้าไม่มี hint ในไฟล์หลัก ต้องให้ผู้ใช้ระบุก่อน ★★★
            if not main_file_info:
                print("ไม่พบข้อมูล hint ในไฟล์ NPC.json กำลังแสดงหน้าต่างให้ผู้ใช้ระบุ...")
                result = self._check_and_create_hint(npc_main_file)

                if not result:
                    print("ผู้ใช้ยกเลิกการระบุข้อมูลเกม")
                    return

                # ตรวจสอบอีกครั้งหลังจากผู้ใช้บันทึกข้อมูล
                main_file_info = get_game_info_from_json(npc_main_file)
                if not main_file_info:
                    QMessageBox.critical(
                        self, "ข้อผิดพลาด", "ไม่สามารถอ่านหรือเพิ่มข้อมูลเกมในไฟล์ NPC.json ได้"
                    )
                    return

            # ตรวจสอบไฟล์อื่นๆ
            valid_files = []
            for file_path in npc_files:
                file_info = get_game_info_from_json(file_path)

                # ★★★ จุดสำคัญ: หากไม่มี hint ให้แสดงหน้าต่างให้ผู้ใช้ระบุ ★★★
                if not file_info:
                    # เก็บชื่อไฟล์เพื่อแสดงให้ผู้ใช้เห็น
                    file_name = os.path.basename(file_path)

                    # แสดงหน้าต่างให้ผู้ใช้ยืนยันการเพิ่ม hint
                    reply = QMessageBox.question(
                        self,
                        "ไม่พบข้อมูลเกม",
                        f"ไฟล์ {file_name} ไม่มีข้อมูลเกม ต้องการระบุข้อมูลเกมหรือไม่?",
                        QMessageBox.Yes | QMessageBox.No,
                    )

                    if reply == QMessageBox.Yes:
                        # เรียกหน้าต่างให้ผู้ใช้ระบุข้อมูลเกม
                        success = self._check_and_create_hint(file_path)
                        if success:
                            # ตรวจสอบอีกครั้ง
                            file_info = get_game_info_from_json(file_path)

                # เฉพาะไฟล์ที่มี hint เท่านั้นที่จะใช้ได้
                if file_info:
                    valid_files.append(file_path)

            # ตรวจสอบว่ามีไฟล์ที่สลับได้หรือไม่
            if not valid_files:
                QMessageBox.warning(self, "คำเตือน", "ไม่มีไฟล์ NPC ที่มีข้อมูลเกมที่สลับได้")
                return

            # ทุกไฟล์มี hint แล้ว เราจึงค่อยแสดงหน้าต่างสลับไฟล์
            self._show_swap_dialog(npc_main_file, valid_files)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"เกิดข้อผิดพลาดในการสลับไฟล์: {str(e)}")

    def _show_swap_dialog(self, current_file, available_files):
        """
        แสดงหน้าต่างสำหรับเลือกไฟล์ที่จะสลับกับไฟล์ปัจจุบัน

        Args:
            current_file: พาธของไฟล์ปัจจุบัน (NPC.json)
            available_files: รายการพาธของไฟล์ที่มีให้เลือก
        """
        # อ่านข้อมูลจากไฟล์ปัจจุบัน (ควรมี hint แล้วจากการตรวจสอบใน swap_data_files)
        current_info = get_game_info_from_json(current_file)
        if not current_info:
            QMessageBox.critical(
                self, "ข้อผิดพลาด", "ไฟล์ NPC.json ไม่มีข้อมูลเกม กรุณาลองใหม่อีกครั้ง"
            )
            return

        current_game = current_info.get("name", "Unknown Game")

        # สร้างหน้าต่างใหม่โดยใช้ QDialog
        swap_dialog = QDialog(self)
        swap_dialog.setWindowTitle("สลับฐานข้อมูล")
        swap_dialog.setFixedSize(400, 450)
        dialog_layout = QVBoxLayout(swap_dialog)

        # สร้าง UI
        header_label = QLabel(f"ขณะนี้ใช้ข้อมูลของเกม: {current_game}", swap_dialog)
        header_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        dialog_layout.addWidget(header_label)

        instruction_label = QLabel("เลือกฐานข้อมูลที่ต้องการเปลี่ยนไปใช้:", swap_dialog)
        instruction_label.setStyleSheet("font-size: 14pt; text-align: left;")
        dialog_layout.addWidget(instruction_label)

        # สร้างเฟรมสำหรับใส่ตัวเลือก
        options_frame = QWidget(swap_dialog)
        options_layout = QVBoxLayout(options_frame)
        dialog_layout.addWidget(options_frame)

        # เพิ่มคำอธิบายว่ารองรับทุกเกมที่มีข้อมูล
        note_label = QLabel(
            "สามารถเลือกฐานข้อมูลของเกมใดก็ได้ที่มีข้อมูล _game_info",
            swap_dialog,
        )
        note_label.setStyleSheet("font-size: 12pt; color: #555555;")
        dialog_layout.addWidget(note_label)

        # ตรวจสอบและกรองเฉพาะไฟล์ที่มี hint
        valid_files = []
        for file_path in available_files:
            # อ่านข้อมูล hint
            file_info = get_game_info_from_json(file_path)

            # เฉพาะไฟล์ที่มี hint เท่านั้น (ไม่จำกัดรหัสเกม)
            if file_info and "name" in file_info:
                valid_files.append(file_path)

        # สร้างกลุ่มปุ่มตัวเลือก
        button_group = QButtonGroup(swap_dialog)
        selected_file = None

        # เพิ่มตัวเลือกลงในหน้าต่าง
        if valid_files:
            for i, file_path in enumerate(valid_files):
                # อ่านข้อมูลจากไฟล์
                file_info = get_game_info_from_json(file_path)
                game_name = file_info.get("name", os.path.basename(file_path))

                # สร้างตัวเลือก
                option_frame = QFrame(options_frame)
                option_layout = QHBoxLayout(option_frame)

                rb = QRadioButton(game_name, option_frame)
                rb.file_path = file_path  # เก็บพาธไว้ใน property ของปุ่ม
                rb.setStyleSheet("font-size: 14pt;")
                button_group.addButton(rb)
                option_layout.addWidget(rb)

                # แสดงชื่อไฟล์
                file_label = QLabel(f"({os.path.basename(file_path)})", option_frame)
                file_label.setStyleSheet("font-size: 12pt; color: #555555;")
                option_layout.addWidget(file_label)

                options_layout.addWidget(option_frame)

                # หากเป็นปุ่มแรก ให้เลือกเริ่มต้น
                if i == 0:
                    rb.setChecked(True)
                    selected_file = file_path

        else:
            # ถ้าไม่มีไฟล์ที่รองรับ
            warning_label = QLabel(
                "ไม่พบไฟล์ NPC อื่นๆ ที่มีข้อมูลเกมในโฟลเดอร์นี้",
                options_frame,
            )
            warning_label.setStyleSheet("font-size: 14pt; color: #FF3333;")
            options_layout.addWidget(warning_label)

        # สร้างปุ่มสำหรับยกเลิกและยืนยัน
        button_frame = QWidget(swap_dialog)
        button_layout = QHBoxLayout(button_frame)
        dialog_layout.addWidget(button_frame)

        cancel_btn = QPushButton("ยกเลิก", button_frame)
        cancel_btn.setStyleSheet("font-size: 14pt;")
        cancel_btn.clicked.connect(swap_dialog.reject)
        button_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("สลับข้อมูล", button_frame)
        confirm_btn.setStyleSheet(
            "font-size: 14pt; font-weight: bold; background-color: #4CAF50; color: white;"
        )
        button_layout.addWidget(confirm_btn)

        # เก็บข้อมูลเลือกเมื่อมีการคลิก
        def on_button_clicked():
            for button in button_group.buttons():
                if button.isChecked():
                    nonlocal selected_file
                    selected_file = button.file_path
                    self._confirm_swap(current_file, selected_file, swap_dialog)
                    break

        confirm_btn.clicked.connect(on_button_clicked)

        # ถ้าไม่มีไฟล์ที่รองรับ ปิดปุ่มยืนยัน
        if not valid_files:
            confirm_btn.setEnabled(False)

        # แสดงหน้าต่าง
        swap_dialog.exec_()

    def _ensure_file_has_hint(self, file_path, game_name=None, game_code=None):
        """
        ตรวจสอบว่าไฟล์มี hint หรือไม่

        Args:
            file_path: พาธของไฟล์ที่ต้องการตรวจสอบ
            game_name: ชื่อเกม (ถ้าไม่ระบุจะไม่เพิ่ม hint)
            game_code: รหัสเกม (ถ้าไม่ระบุจะไม่เพิ่ม hint)

        Returns:
            bool: True ถ้ามี hint หรือเพิ่ม hint สำเร็จ, False ถ้าไม่มีและไม่ได้เพิ่ม
        """
        try:
            # อ่านข้อมูลจากไฟล์
            file_info = get_game_info_from_json(file_path)

            # ถ้าพบข้อมูล hint แล้ว คืนค่า True
            if file_info:
                return True

            # ถ้าไม่พบและมีการระบุชื่อเกมและรหัสเกมที่ชัดเจน
            if game_name and game_code:
                # เพิ่มข้อมูลเกมลงในไฟล์
                return add_game_info_to_json(file_path, game_name, game_code)

            # ถ้าไม่พบและไม่มีข้อมูลเพียงพอ ไม่ดำเนินการเพิ่ม hint
            return False
        except Exception as e:
            print(f"Error checking file hint: {e}")
            return False

    def _check_and_create_hint(self, file_path):
        """
        ตรวจสอบว่าไฟล์มี hint หรือไม่ ถ้าไม่มีให้แสดงหน้าต่างให้ผู้ใช้กรอกข้อมูลเกม

        Args:
            file_path: พาธของไฟล์ที่ต้องการตรวจสอบ

        Returns:
            bool: True ถ้าไฟล์มี hint หรือได้เพิ่ม hint แล้ว, False หากผู้ใช้ยกเลิก
        """
        # ตรวจสอบว่าไฟล์มี hint หรือไม่
        print(f"กำลังตรวจสอบ hint ในไฟล์: {file_path}")
        file_info = get_game_info_from_json(file_path)

        # ถ้ามี hint แล้ว ไม่ต้องทำอะไร
        if file_info:
            print(f"พบข้อมูล hint แล้ว: {file_info}")
            return True

        print("ไม่พบข้อมูล hint กำลังแสดงหน้าต่างให้ผู้ใช้กรอกข้อมูล...")

        # ถ้ายังไม่มี hint ให้แสดงหน้าต่างถามผู้ใช้
        dialog = QDialog(self)
        dialog.setWindowTitle("ระบุข้อมูลเกม")
        dialog.setFixedSize(800, 500)  # ขนาดกว้างขึ้นเพื่อรองรับทั้งสองส่วน

        # สร้าง layout หลัก (แนวนอน) เพื่อแบ่งเป็นสองส่วน
        main_layout = QHBoxLayout(dialog)

        # ส่วนซ้าย (A, B, C)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # ส่วน A: คำถามและคำแนะนำ
        question_label = QLabel("กรุณาระบุว่าไฟล์ NPC.json นี้เป็นข้อมูลของเกมใด")
        question_label.setStyleSheet("font-size: 14pt; font-weight: bold;")

        instruction_label = QLabel("โปรดตรวจสอบเนื้อหาไฟล์ในส่วนขวามือเพื่อยืนยันประเภทของเกม")
        instruction_label.setStyleSheet("font-size: 12pt; color: #555;")
        instruction_label.setWordWrap(True)

        left_layout.addWidget(question_label)
        left_layout.addWidget(instruction_label)
        left_layout.addSpacing(20)

        # ส่วน B: กรอกชื่อเกม
        game_layout = QVBoxLayout()
        game_label = QLabel("ชื่อเกม:")
        game_label.setStyleSheet("font-size: 12pt;")

        # เปลี่ยนจากปุ่มเลือกเป็นกล่องข้อความให้ผู้ใช้กรอกชื่อเกมเอง
        game_name_input = QLineEdit()
        game_name_input.setStyleSheet("font-size: 12pt; padding: 5px;")
        game_name_input.setPlaceholderText("กรุณาระบุชื่อเกม")

        game_layout.addWidget(game_label)
        game_layout.addWidget(game_name_input)
        left_layout.addLayout(game_layout)

        # สร้าง note
        note_label = QLabel(
            "หมายเหตุ: ระบุชื่อเกมตามที่ต้องการ เช่น Monster Hunter, FFXIV, PERSONA, ฯลฯ"
        )
        note_label.setStyleSheet("font-size: 10pt; color: #777;")
        left_layout.addWidget(note_label)

        left_layout.addStretch()

        # ส่วน C: ปุ่มบันทึกและยกเลิก
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("ยกเลิก")
        cancel_btn.setFixedWidth(120)
        cancel_btn.clicked.connect(dialog.reject)

        save_btn = QPushButton("บันทึก")
        save_btn.setFixedWidth(120)
        save_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold;"
        )

        # ปุ่มบันทึกจะทำงานเมื่อมีการกรอกชื่อเกมเท่านั้น
        save_btn.setEnabled(False)

        # เมธอดเพื่อเปิดใช้งานปุ่มบันทึก
        def enable_save_button():
            save_btn.setEnabled(bool(game_name_input.text().strip()))

        # เชื่อมต่อเมธอดกับกล่องข้อความ
        game_name_input.textChanged.connect(enable_save_button)

        # ฟังก์ชันเมื่อกดปุ่มบันทึก
        def on_save_clicked():
            game_name = game_name_input.text().strip()
            if not game_name:
                QMessageBox.warning(dialog, "คำเตือน", "กรุณาระบุชื่อเกมก่อนบันทึก")
                return

            # สร้างรหัสเกม (game_code) จากชื่อเกม
            game_code = game_name.lower().replace(" ", "_")
            if len(game_code) > 10:
                game_code = game_code[:10]

            # บันทึก hint ลงในไฟล์
            result = add_game_info_to_json(file_path, game_name, game_code)

            if result:
                QMessageBox.information(
                    dialog,
                    "สำเร็จ",
                    f"บันทึกข้อมูลเกม {game_name} ลงในไฟล์เรียบร้อยแล้ว",
                )
                dialog.accept()
            else:
                QMessageBox.critical(dialog, "ล้มเหลว", "ไม่สามารถบันทึกข้อมูลลงในไฟล์ได้")

        save_btn.clicked.connect(on_save_clicked)

        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)

        left_layout.addLayout(button_layout)

        # ส่วนขวา: แสดงเนื้อหาไฟล์
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        file_content_label = QLabel("เนื้อหาไฟล์ NPC.json:")
        file_content_label.setStyleSheet("font-size: 12pt; font-weight: bold;")

        # สร้าง text editor สำหรับแสดงเนื้อหาไฟล์ (อ่านอย่างเดียว)
        text_editor = QTextEdit()
        text_editor.setReadOnly(True)
        text_editor.setStyleSheet(
            "font-family: Consolas, Courier New, monospace; font-size: 11pt; background-color: #f5f5f5;"
        )

        # อ่านเนื้อหาไฟล์
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
                # แสดงเฉพาะ 50 บรรทัดแรกเพื่อไม่ให้หน้าต่างโตเกินไป
                lines = content.split("\n")[:50]
                if len(lines) >= 50:
                    lines.append("...")
                text_editor.setText("\n".join(lines))
        except Exception as e:
            text_editor.setText(f"ไม่สามารถอ่านไฟล์ได้: {str(e)}")

        right_layout.addWidget(file_content_label)
        right_layout.addWidget(text_editor)

        # เพิ่มทั้งสองส่วนลงใน layout หลัก
        main_layout.addWidget(left_panel, 1)  # สัดส่วน 40%
        main_layout.addWidget(right_panel, 2)  # สัดส่วน 60%

        # แสดงหน้าต่าง
        result = dialog.exec_()

        # คืนค่า True ถ้าผู้ใช้กดบันทึก, False ถ้าผู้ใช้ยกเลิก
        return result == QDialog.Accepted

    def _confirm_swap(self, current_file, target_file, dialog):
        """
        ยืนยันการสลับไฟล์

        Args:
            current_file: พาธของไฟล์ปัจจุบัน
            target_file: พาธของไฟล์เป้าหมาย
            dialog: หน้าต่างที่แสดงตัวเลือก (QDialog)
        """
        try:
            # ตรวจสอบว่าเลือกไฟล์เป้าหมายหรือไม่
            if not target_file:
                QMessageBox.warning(self, "คำเตือน", "กรุณาเลือกฐานข้อมูลที่ต้องการเปลี่ยนไปใช้")
                return

            # อ่านข้อมูลจากไฟล์ปัจจุบันและไฟล์เป้าหมาย
            current_info = get_game_info_from_json(current_file)
            target_info = get_game_info_from_json(target_file)

            current_game = (
                current_info.get("name", "Unknown Game")
                if current_info
                else "Unknown Game"
            )
            target_game = (
                target_info.get("name", "Unknown Game")
                if target_info
                else "Unknown Game"
            )

            # แสดงข้อความยืนยัน
            confirm_msg = f"คุณแน่ใจหรือไม่ที่จะเปลี่ยนจากข้อมูลของเกม {current_game} ไปใช้ข้อมูลของเกม {target_game}?"
            reply = QMessageBox.question(
                self, "ยืนยันการสลับข้อมูล", confirm_msg, QMessageBox.Yes | QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # ดำเนินการสลับไฟล์
            success, error_msg = swap_npc_files(current_file, target_file)

            # ปิดหน้าต่าง
            dialog.accept()

            if success:
                # รีเฟรชรายการไฟล์
                self.refresh_file_list()

                # แสดงข้อความสำเร็จ
                QMessageBox.information(
                    self,
                    "สำเร็จ",
                    f"สลับข้อมูลเรียบร้อยแล้ว\nตอนนี้กำลังใช้ข้อมูลของเกม {target_game}",
                )

                # แสดงสถานะ
                self.lbl_status.setText(f"สลับข้อมูลเป็น {target_game} เรียบร้อยแล้ว")
                self.lbl_status.setStyleSheet(
                    "color: #00AA00; font-size: 14.4pt;"
                )  # สีเขียว
            else:
                # แสดงข้อความล้มเหลว
                QMessageBox.critical(self, "ล้มเหลว", f"ไม่สามารถสลับข้อมูลได้\n{error_msg}")

                # แสดงสถานะ
                self.lbl_status.setText("ไม่สามารถสลับข้อมูลได้")
                self.lbl_status.setStyleSheet(
                    "color: #AA0000; font-size: 14.4pt;"
                )  # สีแดง

            # ลบข้อความสถานะหลัง 3 วินาที
            QTimer.singleShot(
                3000,
                lambda: self.lbl_status.setStyleSheet(
                    "color: #00ff00; font-size: 14.4pt;"
                ),
            )
            QTimer.singleShot(3000, lambda: self.lbl_status.setText(""))

        except Exception as e:
            # ปิดหน้าต่าง
            dialog.reject()

            # แสดงข้อความล้มเหลว
            QMessageBox.critical(self, "Error", f"เกิดข้อผิดพลาดในการสลับไฟล์: {str(e)}")

    def create_new_game(self):
        """
        แสดงหน้าต่างสำหรับสร้างเกมใหม่และสร้างไฟล์ NPC.json ใหม่
        """
        try:
            # ตรวจสอบว่ามีโฟลเดอร์ที่ทำงานอยู่หรือไม่
            if not self.target_path:
                QMessageBox.warning(self, "คำเตือน", "กรุณาเลือกโฟลเดอร์ก่อน")
                return

            # ตรวจสอบว่ามีไฟล์ NPC.json ในโฟลเดอร์หรือไม่
            current_npc_file = os.path.join(self.target_path, "npc.json")
            if not os.path.exists(current_npc_file):
                QMessageBox.warning(self, "คำเตือน", "ไม่พบไฟล์ NPC.json ในโฟลเดอร์ปัจจุบัน")
                return

            # ตรวจสอบว่าไฟล์ปัจจุบันมี hint หรือไม่
            current_info = get_game_info_from_json(current_npc_file)
            if not current_info:
                result = self._check_and_create_hint(current_npc_file)
                if not result:
                    return
                current_info = get_game_info_from_json(current_npc_file)

            # สร้างหน้าต่างใหม่โดยใช้ QDialog
            dialog = QDialog(self)
            dialog.setWindowTitle("เพิ่มเกมใหม่")
            dialog.setFixedSize(400, 280)
            dialog_layout = QVBoxLayout(dialog)

            # คำอธิบาย
            info_label = QLabel(
                f"ขณะนี้คุณกำลังใช้ข้อมูลของเกม: {current_info.get('name', 'Unknown')}\n\n"
                f"การเพิ่มเกมใหม่จะทำให้:"
                f"\n - ข้อมูลเกมปัจจุบันจะถูกเปลี่ยนชื่อเป็น npc_{current_info.get('code', 'unknown')}.json"
                f"\n - สร้างไฟล์ npc.json ใหม่สำหรับเกมที่ระบุ"
                f"\n\nกรุณาระบุชื่อเกมใหม่:"
            )
            info_label.setWordWrap(True)
            info_label.setStyleSheet("font-size: 12pt;")
            dialog_layout.addWidget(info_label)

            # ช่องกรอกชื่อเกม
            game_name_input = QLineEdit(dialog)
            game_name_input.setStyleSheet("font-size: 14pt; padding: 5px;")
            game_name_input.setPlaceholderText("ชื่อเกมใหม่")
            dialog_layout.addWidget(game_name_input)

            # เพิ่มคำแนะนำเล็กน้อย
            tip_label = QLabel(
                "หมายเหตุ: ชื่อเกมจะถูกใช้สร้างรหัสเกมโดยอัตโนมัติ "
                'เช่น "My New Game" จะมีรหัสเป็น "my_new_ga"'
            )
            tip_label.setWordWrap(True)
            tip_label.setStyleSheet("font-size: 10pt; color: #777777;")
            dialog_layout.addWidget(tip_label)

            dialog_layout.addSpacing(10)

            # ปุ่มยกเลิกและยืนยัน
            button_layout = QHBoxLayout()
            cancel_btn = QPushButton("ยกเลิก", dialog)
            cancel_btn.setStyleSheet("font-size: 12pt;")
            cancel_btn.clicked.connect(dialog.reject)

            confirm_btn = QPushButton("สร้างเกมใหม่", dialog)
            confirm_btn.setStyleSheet(
                "font-size: 12pt; background-color: #4CAF50; color: white;"
            )
            button_layout.addWidget(cancel_btn)
            button_layout.addWidget(confirm_btn)
            dialog_layout.addLayout(button_layout)

            # ฟังก์ชันเมื่อกดปุ่มยืนยัน
            def on_confirm():
                game_name = game_name_input.text().strip()
                if not game_name:
                    QMessageBox.warning(dialog, "คำเตือน", "กรุณาระบุชื่อเกม")
                    return

                # เปลี่ยนชื่อไฟล์ปัจจุบัน
                current_code = current_info.get("code", "unknown")
                new_current_filename = f"npc_{current_code}.json"
                new_current_filepath = os.path.join(
                    self.target_path, new_current_filename
                )

                # ตรวจสอบว่ามีไฟล์ชื่อนี้อยู่แล้วหรือไม่
                if os.path.exists(new_current_filepath):
                    QMessageBox.warning(
                        dialog,
                        "คำเตือน",
                        f"มีไฟล์ชื่อ {new_current_filename} อยู่แล้ว กรุณาเปลี่ยนชื่อก่อนสร้างเกมใหม่",
                    )
                    return

                try:
                    # เปลี่ยนชื่อไฟล์ปัจจุบัน
                    os.rename(current_npc_file, new_current_filepath)

                    # สร้างไฟล์ใหม่
                    from Manager import create_new_npc_file

                    success, message = create_new_npc_file(current_npc_file, game_name)

                    if success:
                        dialog.accept()
                        QMessageBox.information(self, "สำเร็จ", message)
                        self.refresh_file_list()
                    else:
                        # ถ้าสร้างไฟล์ใหม่ไม่สำเร็จ ให้เปลี่ยนชื่อไฟล์เดิมกลับ
                        os.rename(new_current_filepath, current_npc_file)
                        QMessageBox.critical(self, "ล้มเหลว", message)

                except Exception as e:
                    QMessageBox.critical(
                        dialog, "ข้อผิดพลาด", f"เกิดข้อผิดพลาดในการสร้างเกมใหม่: {str(e)}"
                    )

                    # พยายามเปลี่ยนชื่อไฟล์กลับ ถ้าจำเป็น
                    if not os.path.exists(current_npc_file) and os.path.exists(
                        new_current_filepath
                    ):
                        try:
                            os.rename(new_current_filepath, current_npc_file)
                        except:
                            pass

            confirm_btn.clicked.connect(on_confirm)

            # แสดงหน้าต่าง
            result = dialog.exec_()
            if result == QDialog.Accepted:
                # รีเฟรชรายการไฟล์
                self.refresh_file_list()
                self.lbl_status.setText("สร้างเกมใหม่เรียบร้อยแล้ว")
                # ตั้ง timer ลบข้อความสถานะหลัง 3 วินาที
                QTimer.singleShot(3000, lambda: self.lbl_status.setText(""))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"เกิดข้อผิดพลาดในการสร้างเกมใหม่: {str(e)}")

    def create_new_game(self):
        """
        แสดงหน้าต่างสำหรับสร้างเกมใหม่และสร้างไฟล์ NPC.json ใหม่
        """
        try:
            # ตรวจสอบว่ามีโฟลเดอร์ที่ทำงานอยู่หรือไม่
            if not self.target_path:
                QMessageBox.warning(self, "คำเตือน", "กรุณาเลือกโฟลเดอร์ก่อน")
                return

            # ตรวจสอบว่ามีไฟล์ NPC.json ในโฟลเดอร์หรือไม่
            current_npc_file = os.path.join(self.target_path, "npc.json")
            if not os.path.exists(current_npc_file):
                QMessageBox.warning(self, "คำเตือน", "ไม่พบไฟล์ NPC.json ในโฟลเดอร์ปัจจุบัน")
                return

            # ตรวจสอบว่าไฟล์ปัจจุบันมี hint หรือไม่
            current_info = get_game_info_from_json(current_npc_file)
            if not current_info:
                result = self._check_and_create_hint(current_npc_file)
                if not result:
                    return
                current_info = get_game_info_from_json(current_npc_file)

            # สร้างหน้าต่างใหม่โดยใช้ QDialog
            dialog = QDialog(self)
            dialog.setWindowTitle("เพิ่มเกมใหม่")
            dialog.setFixedSize(400, 280)
            dialog_layout = QVBoxLayout(dialog)

            # คำอธิบาย
            info_label = QLabel(
                f"ขณะนี้คุณกำลังใช้ข้อมูลของเกม: {current_info.get('name', 'Unknown')}\n\n"
                f"การเพิ่มเกมใหม่จะทำให้:"
                f"\n - ข้อมูลเกมปัจจุบันจะถูกเปลี่ยนชื่อเป็น npc_{current_info.get('code', 'unknown')}.json"
                f"\n - สร้างไฟล์ npc.json ใหม่สำหรับเกมที่ระบุ"
                f"\n\nกรุณาระบุชื่อเกมใหม่:"
            )
            info_label.setWordWrap(True)
            info_label.setStyleSheet("font-size: 12pt;")
            dialog_layout.addWidget(info_label)

            # ช่องกรอกชื่อเกม
            game_name_input = QLineEdit(dialog)
            game_name_input.setStyleSheet("font-size: 14pt; padding: 5px;")
            game_name_input.setPlaceholderText("ชื่อเกมใหม่")
            dialog_layout.addWidget(game_name_input)

            # เพิ่มคำแนะนำเล็กน้อย
            tip_label = QLabel(
                "หมายเหตุ: ชื่อเกมจะถูกใช้สร้างรหัสเกมโดยอัตโนมัติ "
                'เช่น "My New Game" จะมีรหัสเป็น "my_new_ga"'
            )
            tip_label.setWordWrap(True)
            tip_label.setStyleSheet("font-size: 10pt; color: #777777;")
            dialog_layout.addWidget(tip_label)

            dialog_layout.addSpacing(10)

            # ปุ่มยกเลิกและยืนยัน
            button_layout = QHBoxLayout()
            cancel_btn = QPushButton("ยกเลิก", dialog)
            cancel_btn.setStyleSheet("font-size: 12pt;")
            cancel_btn.clicked.connect(dialog.reject)

            confirm_btn = QPushButton("สร้างเกมใหม่", dialog)
            confirm_btn.setStyleSheet(
                "font-size: 12pt; background-color: #4CAF50; color: white;"
            )
            button_layout.addWidget(cancel_btn)
            button_layout.addWidget(confirm_btn)
            dialog_layout.addLayout(button_layout)

            # ฟังก์ชันเมื่อกดปุ่มยืนยัน
            def on_confirm():
                game_name = game_name_input.text().strip()
                if not game_name:
                    QMessageBox.warning(dialog, "คำเตือน", "กรุณาระบุชื่อเกม")
                    return

                # เปลี่ยนชื่อไฟล์ปัจจุบัน
                current_code = current_info.get("code", "unknown")
                new_current_filename = f"npc_{current_code}.json"
                new_current_filepath = os.path.join(
                    self.target_path, new_current_filename
                )

                # ตรวจสอบว่ามีไฟล์ชื่อนี้อยู่แล้วหรือไม่
                if os.path.exists(new_current_filepath):
                    QMessageBox.warning(
                        dialog,
                        "คำเตือน",
                        f"มีไฟล์ชื่อ {new_current_filename} อยู่แล้ว กรุณาเปลี่ยนชื่อก่อนสร้างเกมใหม่",
                    )
                    return

                try:
                    # เปลี่ยนชื่อไฟล์ปัจจุบัน
                    os.rename(current_npc_file, new_current_filepath)

                    # สร้างไฟล์ใหม่
                    from Manager import create_new_npc_file

                    success, message = create_new_npc_file(current_npc_file, game_name)

                    if success:
                        dialog.accept()
                        QMessageBox.information(self, "สำเร็จ", message)
                        self.refresh_file_list()
                    else:
                        # ถ้าสร้างไฟล์ใหม่ไม่สำเร็จ ให้เปลี่ยนชื่อไฟล์เดิมกลับ
                        os.rename(new_current_filepath, current_npc_file)
                        QMessageBox.critical(self, "ล้มเหลว", message)

                except Exception as e:
                    QMessageBox.critical(
                        dialog, "ข้อผิดพลาด", f"เกิดข้อผิดพลาดในการสร้างเกมใหม่: {str(e)}"
                    )

                    # พยายามเปลี่ยนชื่อไฟล์กลับ ถ้าจำเป็น
                    if not os.path.exists(current_npc_file) and os.path.exists(
                        new_current_filepath
                    ):
                        try:
                            os.rename(new_current_filepath, current_npc_file)
                        except:
                            pass

            confirm_btn.clicked.connect(on_confirm)

            # แสดงหน้าต่าง
            result = dialog.exec_()
            if result == QDialog.Accepted:
                # รีเฟรชรายการไฟล์
                self.refresh_file_list()
                self.lbl_status.setText("สร้างเกมใหม่เรียบร้อยแล้ว")
                # ตั้ง timer ลบข้อความสถานะหลัง 3 วินาที
                QTimer.singleShot(3000, lambda: self.lbl_status.setText(""))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"เกิดข้อผิดพลาดในการสร้างเกมใหม่: {str(e)}")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    # วาดเงาเล็กน้อยรอบๆหน้าต่าง (ถ้าต้องการ)
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        brush = QBrush(QColor(46, 46, 46))
        painter.fillRect(self.rect(), brush)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
