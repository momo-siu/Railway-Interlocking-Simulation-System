import os
import sys
from PyQt5.QtMultimedia import QSound
from PyQt5.QtCore import QUrl

class SoundManager:
    _instance = None
    
    # 处理 PyInstaller 封装后的路径
    if getattr(sys, 'frozen', False):
        BASE_DIR = sys._MEIPASS
    else:
        BASE_DIR = os.path.dirname(os.path.dirname(__file__))
        
    SOUND_DIR = os.path.join(BASE_DIR, "assets", "sounds")

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SoundManager, cls).__new__(cls)
        return cls._instance

    def play(self, sound_name):
        """
        播放指定名称的音效，自动匹配 .wav 或 .WAV 后缀
        """
        # 尝试几种可能的命名方式
        names_to_try = [
            sound_name,
            sound_name.upper(),
            sound_name.lower(),
            sound_name + ".wav",
            sound_name + ".WAV"
        ]
        
        for name in names_to_try:
            path = os.path.join(self.SOUND_DIR, name)
            if os.path.exists(path):
                QSound.play(path)
                return True
        
        print(f"Warning: Sound file {sound_name} not found in {self.SOUND_DIR}")
        return False

    def play_alert(self):
        self.play("BEEBOO")

    def play_ding(self):
        self.play("DING")

    def play_switch_move(self):
        self.play("DSDS")
