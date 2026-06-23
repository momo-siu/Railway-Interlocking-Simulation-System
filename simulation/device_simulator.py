from PyQt5.QtCore import QObject, QTimer
from utils.state_manager import StateManager
from utils.models import SwitchPosition, SignalColor
from utils.sound_manager import SoundManager

class DeviceSimulator(QObject):
    def __init__(self):
        super().__init__()
        self.state_manager = StateManager()
        self.sound_manager = SoundManager()
        
    def move_switch(self, swid: str, target_pos: SwitchPosition):
        """模拟道岔转动，带延时"""
        sw = self.state_manager.switches.get(swid)
        if not sw or sw.position == target_pos:
            return

        self.state_manager.log(f"道岔 {swid}# 开始向 {target_pos.value} 转换...")
        self.state_manager.update_switch(swid, position=SwitchPosition.MOVING)
        self.sound_manager.play_switch_move()
        
        # 模拟 2秒转动时间
        QTimer.singleShot(2000, lambda: self._finish_move_switch(swid, target_pos))

    def _finish_move_switch(self, swid, target_pos):
        self.state_manager.update_switch(swid, position=target_pos)
        self.state_manager.log(f"道岔 {swid}# 转换完毕，当前位置: {target_pos.value}")

    def set_signal(self, sid: str, color: SignalColor):
        """模拟信号机状态切换"""
        self.state_manager.update_signal(sid, color=color)
        self.state_manager.log(f"信号机 {sid} 状态变更为: {color.value}")

    def set_track_occupancy(self, tid: str, is_occupied: bool):
        """模拟轨道占用/出清"""
        self.state_manager.update_track(tid, is_occupied=is_occupied)
        status = "占用" if is_occupied else "出清"
        self.state_manager.log(f"轨道区段 {tid} {status}")
