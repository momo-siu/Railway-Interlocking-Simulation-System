from PyQt5.QtCore import QObject, QTimer
from utils.state_manager import StateManager
from utils.models import SwitchPosition, SignalColor, SignalAspect
from utils.sound_manager import SoundManager
import random

class DeviceSimulator(QObject):
    def __init__(self):
        super().__init__()
        self.state_manager = StateManager()
        self.sound_manager = SoundManager()
        self._manual_unlock_timers = {}  # route_id -> QTimer
        
    def move_switch(self, swid: str, target_pos: SwitchPosition):
        """道岔转换（仅仿真物理延时，不做联锁校验）"""
        sw = self.state_manager.switches.get(swid)
        if not sw or sw.position == target_pos:
            return

        prev_pos = sw.position
        self.state_manager.log(f"道岔 {swid}# 开始向 {target_pos.value} 转换...")
        self.state_manager.update_switch(swid, position=SwitchPosition.MOVING, target_position=target_pos, last_move_failed=False)
        self.sound_manager.play_switch_move()
        
        move_ms = random.randint(3000, 5000)
        QTimer.singleShot(move_ms, lambda: self._finish_move_switch(swid, target_pos, prev_pos))

    def _finish_move_switch(self, swid: str, target_pos: SwitchPosition, prev_pos: SwitchPosition):
        sw = self.state_manager.switches.get(swid)
        if not sw:
            return
        if sw.is_blocked or sw.is_fault:
            self.state_manager.log(f"道岔 {swid}# 转换失败（封锁/故障），保持: {prev_pos.value}", "ERROR")
            self.state_manager.update_switch(swid, position=prev_pos, target_position=None, last_move_failed=True)
            return

        self.state_manager.log(f"道岔 {swid}# 转换完毕，当前位置: {target_pos.value}")
        self.state_manager.update_switch(swid, position=target_pos, target_position=None, last_move_failed=False)

    def set_signal_aspect(self, sid: str, aspect: SignalAspect):
        """信号点灯（仅仿真显示，不做联锁校验）"""
        sig = self.state_manager.signals.get(sid)
        if not sig:
            return
        if sig.is_blocked or sig.is_fault:
            self.state_manager.log(f"信号机 {sid} 封锁/故障，禁止点灯", "ERROR")
            return
        if sig.is_filament_fault:
            self.state_manager.log(f"信号机 {sid} 灯丝断丝，禁止开放", "ERROR")
            return

        if sid.startswith("D"):
            if aspect == SignalAspect.STOP:
                color = SignalColor.BLUE
            else:
                color = SignalColor.WHITE
        else:
            if aspect == SignalAspect.STOP:
                color = SignalColor.RED
            elif aspect == SignalAspect.PROCEED:
                color = SignalColor.GREEN
            elif aspect in (SignalAspect.CAUTION, SignalAspect.DOUBLE_CAUTION):
                color = SignalColor.YELLOW
            elif aspect == SignalAspect.GUIDE:
                color = SignalColor.MOON_WHITE
            else:
                color = SignalColor.OFF

        self.state_manager.update_signal(sid, aspect=aspect, color=color)
        self.state_manager.log(f"信号机 {sid} 点灯: {aspect.value}")

    def set_track_occupancy(self, tid: str, is_occupied: bool, delay_ms: int = 0):
        """轨道区段占用/出清（仅仿真显示，不做联锁校验）"""
        def apply():
            self.state_manager.update_track(tid, is_occupied=is_occupied)
            status = "占用" if is_occupied else "出清"
            self.state_manager.log(f"轨道区段 {tid} {status}")

        if delay_ms and delay_ms > 0:
            QTimer.singleShot(delay_ms, apply)
        else:
            apply()

    def start_manual_unlock_countdown(self, route_id: str, seconds: int):
        """人解倒计时（延时托管在仿真层）"""
        if route_id in self._manual_unlock_timers:
            self._manual_unlock_timers[route_id].stop()
            self._manual_unlock_timers[route_id].deleteLater()
            del self._manual_unlock_timers[route_id]

        if seconds <= 0:
            self.state_manager.update_route(route_id, manual_unlock_remaining_s=0)
            return

        self.state_manager.update_route(route_id, manual_unlock_required=True, manual_unlock_remaining_s=seconds)
        timer = QTimer(self)
        timer.setInterval(1000)

        def tick():
            rt = self.state_manager.routes.get(route_id)
            if not rt:
                timer.stop()
                return
            remaining = max(0, int(rt.manual_unlock_remaining_s) - 1)
            self.state_manager.update_route(route_id, manual_unlock_remaining_s=remaining)
            if remaining == 0:
                timer.stop()
                self.state_manager.log(f"人解倒计时结束: {route_id}", "SUCCESS")

        timer.timeout.connect(tick)
        timer.start()
        self._manual_unlock_timers[route_id] = timer
