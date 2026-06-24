from PyQt5.QtCore import QObject, pyqtSignal
from utils.models import (
    SignalAspect,
    SignalColor,
    SignalModel,
    SwitchModel,
    SwitchPosition,
    TrackModel,
    RouteModel,
    RouteStage,
)
from typing import Dict, Optional
import json
import os

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
        config_path = os.path.join(os.path.dirname(__file__), "station_config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        self.signals.clear()
        self.switches.clear()
        self.tracks.clear()
        self.routes.clear()

        for s in cfg.get("signals", []):
            sid = s["id"]
            name = s.get("name", sid)
            default_aspect = SignalAspect(s.get("default_aspect", "STOP"))
            sig_type = s.get("type", "TRAIN")

            if sig_type == "SHUNT":
                default_color = SignalColor.BLUE if default_aspect == SignalAspect.STOP else SignalColor.WHITE
            else:
                default_color = SignalColor.RED if default_aspect == SignalAspect.STOP else SignalColor.GREEN

            self.signals[sid] = SignalModel(id=sid, name=name, color=default_color, aspect=default_aspect)

        for sw in cfg.get("switches", []):
            swid = sw["id"]
            name = sw.get("name", f"{swid}#")
            default_pos = SwitchPosition(sw.get("default_position", "NORMAL"))
            self.switches[swid] = SwitchModel(id=swid, name=name, position=default_pos)

        for t in cfg.get("tracks", []):
            tid = t["id"]
            name = t.get("name", tid)
            self.tracks[tid] = TrackModel(id=tid, name=name)

        for r in cfg.get("routes", []):
            rid = r["id"]
            start = r["start"]
            end = r["end"]
            route_type = r.get("type", "TRAIN")
            path_tracks = list(r.get("path_tracks", []))
            approach_tracks = list(r.get("approach_tracks", []))
            departure_tracks = list(r.get("departure_tracks", []))
            start_aspect = SignalAspect(r.get("start_aspect", "STOP"))

            path_switches = {k: SwitchPosition(v) for k, v in r.get("switches", {}).items()}
            flank_switches = {k: SwitchPosition(v) for k, v in r.get("flank_switches", {}).items()}
            conflicts = list(r.get("conflicts", []))

            self.routes[rid] = RouteModel(
                id=rid,
                start_signal=start,
                end_signal=end,
                type=route_type,
                path_tracks=path_tracks,
                approach_tracks=approach_tracks,
                departure_tracks=departure_tracks,
                path_switches=path_switches,
                flank_switches=flank_switches,
                conflicting_routes=conflicts,
                stage=RouteStage.IDLE,
                start_aspect=start_aspect,
                is_active=False,
            )

    def update_signal(self, sid: str, **kwargs):
        if sid in self.signals:
            sig = self.signals[sid]
            changed = False
            for key, value in kwargs.items():
                if getattr(sig, key) != value:
                    setattr(sig, key, value)
                    changed = True
            if changed:
                self.state_changed.emit(sid, sig)

    def update_switch(self, swid: str, **kwargs):
        if swid in self.switches:
            sw = self.switches[swid]
            changed = False
            for key, value in kwargs.items():
                if getattr(sw, key) != value:
                    setattr(sw, key, value)
                    changed = True
            if changed:
                self.state_changed.emit(swid, sw)

    def update_track(self, tid: str, **kwargs):
        if tid in self.tracks:
            tk = self.tracks[tid]
            changed = False
            for key, value in kwargs.items():
                if getattr(tk, key) != value:
                    setattr(tk, key, value)
                    changed = True
            if changed:
                self.state_changed.emit(tid, tk)

    def update_route(self, rid: str, **kwargs):
        if rid in self.routes:
            rt = self.routes[rid]
            changed = False
            for key, value in kwargs.items():
                if getattr(rt, key) != value:
                    setattr(rt, key, value)
                    changed = True
            if changed:
                self.state_changed.emit(rid, rt)

    def find_route(self, start_signal: str, end_signal: str, route_type: Optional[str] = None) -> Optional[RouteModel]:
        for r in self.routes.values():
            if r.start_signal != start_signal or r.end_signal != end_signal:
                continue
            if route_type and r.type != route_type:
                continue
            return r
        return None

    def list_routes_from_start(self, start_signal: str, route_type: Optional[str] = None):
        routes = []
        for r in self.routes.values():
            if r.start_signal != start_signal:
                continue
            if route_type and r.type != route_type:
                continue
            routes.append(r)
        return routes

    def log(self, message: str, level: str = "INFO"):
        self.log_signal.emit(level, message)
