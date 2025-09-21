class DialogueCache:
    """
    คลาสสำหรับจัดการข้อมูล cache ของบทสนทนา การแปลชื่อตัวละคร และรูปแบบการพูด
    """

    def __init__(self):
        self.name_history = []  # เก็บประวัติชื่อที่ validate แล้ว
        self.last_speaker = None  # เก็บชื่อล่าสุดที่ validate แล้ว
        self.MAX_HISTORY = 5
        self.session_speakers = []
        self.name_translations = {}
        self.speaker_styles = {}  # เก็บรูปแบบการพูดของตัวละคร

    def add_validated_name(self, name):
        """เพิ่มชื่อที่ผ่านการ validate แล้วเท่านั้น"""
        if name and name != self.last_speaker:
            self.last_speaker = name
            if name not in self.name_history:
                self.name_history.append(name)
                if len(self.name_history) > self.MAX_HISTORY:
                    self.name_history.pop(0)

    def add_speaker(self, speaker_name, translated_name=None):
        """เพิ่มชื่อผู้พูดในเซสชั่น"""
        if speaker_name:
            if speaker_name not in self.session_speakers:
                self.session_speakers.append(speaker_name)
            self.last_speaker = speaker_name
            if translated_name:
                self.name_translations[speaker_name] = translated_name

    def get_speaker_translation(self, speaker_name):
        """ดึงการแปลชื่อที่เคยแปลไว้"""
        return self.name_translations.get(speaker_name)

    def get_last_speaker(self):
        """ดึงชื่อล่าสุดที่ validate แล้ว"""
        return self.last_speaker

    def get_recent_names(self):
        """ดึงประวัติชื่อที่ validate แล้ว"""
        return self.name_history

    def get_speaker_style(self, speaker_name):
        """ดึงรูปแบบการพูดของตัวละคร"""
        return self.speaker_styles.get(speaker_name, "")

    def set_speaker_style(self, speaker_name, style):
        """กำหนดรูปแบบการพูดของตัวละคร"""
        if speaker_name:
            self.speaker_styles[speaker_name] = style

    def clear(self):
        """ล้าง cache"""
        self.name_history.clear()
        self.last_speaker = None

    def clear_session(self):
        """ล้างข้อมูลเซสชั่น"""
        self.session_speakers.clear()
        self.name_translations.clear()
        self.speaker_styles.clear()
        self.last_speaker = None
