from PyQt5.QtCore import QObject, pyqtSignal
from utils.models import SignalModel, SwitchModel, TrackModel, RouteModel, SignalColor, SwitchPosition
from typing import Dict

class StateManager(QObject):
    # 定义信号，用于 UI 更新
    state_changed = pyqtSignal(str, object)  # device_id, new_state
    log_signal = pyqtSignal(str, str)  # level, message

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StateManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self.signals: Dict[str, SignalModel] = {}
        self.switches: Dict[str, SwitchModel] = {}
        self.tracks: Dict[str, TrackModel] = {}
        self.routes: Dict[str, RouteModel] = {}
        self._initialized = True
        self.init_station_data()

    def init_station_data(self):
        # 初始化信号机
        signal_ids = ["X", "S", "X3", "XII", "X1", "S3", "SII", "S1", "D1", "D2"]
        for sid in signal_ids:
            color = SignalColor.RED
            if sid.startswith("D"):
                color = SignalColor.BLUE
            self.signals[sid] = SignalModel(id=sid, name=sid, color=color)

        # 初始化道岔
        switch_ids = ["1", "2", "3", "4", "5"]
        for swid in switch_ids:
            self.switches[swid] = SwitchModel(id=swid, name=f"{swid}#")

        # 初始化轨道区段
        track_ids = ["JXG", "IIAG", "3G", "IIG", "1G", "安全线", "IIBG", "JSG"]
        for tid in track_ids:
            self.tracks[tid] = TrackModel(id=tid, name=tid)

    def update_signal(self, sid: str, **kwargs):
        if sid in self.signals:
            sig = self.signals[sid]
            for key, value in kwargs.items():
                setattr(sig, key, value)
            self.state_changed.emit(sid, sig)

    def update_switch(self, swid: str, **kwargs):
        if swid in self.switches:
            sw = self.switches[swid]
            for key, value in kwargs.items():
                setattr(sw, key, value)
            self.state_changed.emit(swid, sw)

    def update_track(self, tid: str, **kwargs):
        if tid in self.tracks:
            tk = self.tracks[tid]
            for key, value in kwargs.items():
                setattr(tk, key, value)
            self.state_changed.emit(tid, tk)

    def log(self, message: str, level: str = "INFO"):
        self.log_signal.emit(level, message)
