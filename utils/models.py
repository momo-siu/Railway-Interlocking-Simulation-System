from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional

class SignalColor(Enum):
    RED = "RED"
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    BLUE = "BLUE"
    WHITE = "WHITE"
    OFF = "OFF"

class SwitchPosition(Enum):
    NORMAL = "NORMAL"  # 定位
    REVERSE = "REVERSE"  # 反位
    MOVING = "MOVING"  # 转换中

class DeviceStatus(Enum):
    IDLE = "IDLE"
    LOCKED = "LOCKED"
    OCCUPIED = "OCCUPIED"
    FAULT = "FAULT"

@dataclass
class SignalModel:
    id: str
    name: str
    color: SignalColor = SignalColor.RED
    is_locked: bool = False
    is_broken: bool = False

@dataclass
class SwitchModel:
    id: str
    name: str
    position: SwitchPosition = SwitchPosition.NORMAL
    is_locked: bool = False  # 进路锁闭
    is_individual_locked: bool = False  # 单锁
    is_blocked: bool = False  # 封锁
    is_fault: bool = False
    target_position: Optional[SwitchPosition] = None

@dataclass
class TrackModel:
    id: str
    name: str
    is_occupied: bool = False
    is_locked: bool = False
    is_blocked: bool = False

@dataclass
class RouteModel:
    id: str
    start_signal: str
    end_signal: str
    type: str  # 'TRAIN' or 'SHUNTING'
    path_tracks: List[str] = field(default_factory=list)
    path_switches: Dict[str, SwitchPosition] = field(default_factory=dict)
    status: str = "IDLE"  # IDLE, SETTING, LOCKED, OPENED, RELEASING
