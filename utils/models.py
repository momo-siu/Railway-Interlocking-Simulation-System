from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional

class SignalColor(Enum):
    RED = "RED"
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    BLUE = "BLUE"
    WHITE = "WHITE"
    MOON_WHITE = "MOON_WHITE"
    OFF = "OFF"

class SignalAspect(Enum):
    STOP = "STOP"
    PROCEED = "PROCEED"  # 绿灯/允许
    CAUTION = "CAUTION"  # 黄灯/预告
    DOUBLE_CAUTION = "DOUBLE_CAUTION"  # UU/双黄
    SHUNT_PROCEED = "SHUNT_PROCEED"  # 调车允许（月白/白）
    GUIDE = "GUIDE"  # 引导（红+月白，在本项目用 MOON_WHITE 表示）

class SwitchPosition(Enum):
    NORMAL = "NORMAL"  # 定位
    REVERSE = "REVERSE"  # 反位
    MOVING = "MOVING"  # 转换中

class RouteStage(Enum):
    IDLE = "IDLE"
    SELECTED = "SELECTED"  # 选排/征用
    PRELOCKED = "PRELOCKED"  # 预先锁闭
    OPENED = "OPENED"  # 信号开放
    APPROACH_LOCKED = "APPROACH_LOCKED"  # 接近锁闭/压入后
    RELEASING = "RELEASING"  # 解锁中（分段/延时）
    RELEASED = "RELEASED"  # 已解锁完成

@dataclass
class SignalModel:
    id: str
    name: str
    color: SignalColor = SignalColor.RED
    aspect: SignalAspect = SignalAspect.STOP
    is_locked: bool = False
    is_blocked: bool = False  # 封锁
    is_filament_fault: bool = False  # 灯丝断丝
    is_fault: bool = False  # 设备故障

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
    last_move_failed: bool = False

@dataclass
class TrackModel:
    id: str
    name: str
    is_occupied: bool = False
    is_locked: bool = False
    is_blocked: bool = False
    is_shunt_failure: bool = False  # 分路不良
    is_fault: bool = False  # 区段故障

@dataclass
class RouteModel:
    id: str
    start_signal: str
    end_signal: str
    type: str  # 'TRAIN' | 'SHUNTING' | 'THROUGH'
    path_tracks: List[str] = field(default_factory=list)
    approach_tracks: List[str] = field(default_factory=list)
    departure_tracks: List[str] = field(default_factory=list)
    path_switches: Dict[str, SwitchPosition] = field(default_factory=dict)
    flank_switches: Dict[str, SwitchPosition] = field(default_factory=dict)
    conflicting_routes: List[str] = field(default_factory=list)
    stage: RouteStage = RouteStage.IDLE
    start_aspect: SignalAspect = SignalAspect.STOP
    is_active: bool = False
    manual_unlock_required: bool = False
    manual_unlock_remaining_s: int = 0
