from PyQt5.QtCore import QObject, QTimer
from utils.state_manager import StateManager
from utils.models import SwitchPosition, SignalColor, RouteModel
from simulation.device_simulator import DeviceSimulator

class InterlockingEngine(QObject):
    def __init__(self, simulator: DeviceSimulator):
        super().__init__()
        self.state_manager = StateManager()
        self.simulator = simulator
        self.active_routes = {}  # start_node -> route_model
        
        # 预定义进路表
        self.route_table = {
            # 下行接车进路
            ("X", "XII"): {
                "tracks": ["IIAG", "IIG"],
                "switches": {"1": SwitchPosition.NORMAL, "4": SwitchPosition.NORMAL},
                "type": "TRAIN"
            },
            ("X", "X3"): {
                "tracks": ["IIAG", "3G"],
                "switches": {"1": SwitchPosition.REVERSE, "3": SwitchPosition.REVERSE},
                "type": "TRAIN"
            },
            ("X", "X1"): {
                "tracks": ["IIAG", "1G"],
                "switches": {"1": SwitchPosition.REVERSE, "5": SwitchPosition.REVERSE},
                "type": "TRAIN"
            },
            # 下行发车进路
            ("XII", "JSG"): {
                "tracks": ["IIBG"],
                "switches": {"4": SwitchPosition.NORMAL},
                "type": "TRAIN"
            },
            ("X3", "JSG"): {
                "tracks": ["IIBG"],
                "switches": {"4": SwitchPosition.REVERSE},
                "type": "TRAIN"
            },
            ("X1", "JSG"): {
                "tracks": ["IIBG"],
                "switches": {"2": SwitchPosition.REVERSE},
                "type": "TRAIN"
            },
            # 上行接车进路
            ("S", "SII"): {
                "tracks": ["IIBG", "IIG"],
                "switches": {"4": SwitchPosition.NORMAL, "1": SwitchPosition.NORMAL},
                "type": "TRAIN"
            },
            # 调车进路示例
            ("D1", "3G"): {
                "tracks": ["3G"],
                "switches": {"1": SwitchPosition.REVERSE, "3": SwitchPosition.REVERSE},
                "type": "SHUNTING"
            }
        }

    def try_set_route(self, start: str, end: str):
        """尝试办理进路"""
        route_key = (start, end)
        if route_key not in self.route_table:
            self.state_manager.log(f"错误: 未定义的进路 {start} -> {end}", "ERROR")
            return

        config = self.route_table[route_key]
        
        # 1. 联锁检查
        # a) 检查区段是否空闲
        for tid in config["tracks"]:
            if self.state_manager.tracks[tid].is_occupied:
                self.state_manager.log(f"进路冲突: 区段 {tid} 占用", "ERROR")
                return
            if self.state_manager.tracks[tid].is_locked:
                self.state_manager.log(f"进路冲突: 区段 {tid} 已锁闭", "ERROR")
                return

        # b) 检查道岔是否可用（未锁闭）
        for swid in config["switches"]:
            if self.state_manager.switches[swid].is_locked:
                self.state_manager.log(f"进路冲突: 道岔 {swid}# 已锁闭", "ERROR")
                return

        self.state_manager.log(f"进路 {start} -> {end} 检查通过，开始办理...")

        # 2. 道岔转换
        for swid, pos in config["switches"].items():
            self.simulator.move_switch(swid, pos)

        # 3. 锁闭与开放信号
        # 这里使用延时模拟道岔转动完成后再锁闭和开放
        QTimer.singleShot(2500, lambda: self._finish_route_setting(start, end, config))

    def _finish_route_setting(self, start, end, config):
        # 检查道岔是否到位
        for swid, pos in config["switches"].items():
            if self.state_manager.switches[swid].position != pos:
                self.state_manager.log(f"进路办理失败: 道岔 {swid}# 未能转换到位", "ERROR")
                return

        # 锁闭设备
        for tid in config["tracks"]:
            self.state_manager.update_track(tid, is_locked=True)
        for swid in config["switches"]:
            self.state_manager.update_switch(swid, is_locked=True)

        # 开放信号
        color = SignalColor.GREEN if config["type"] == "TRAIN" else SignalColor.WHITE
        self.simulator.set_signal(start, color)
        
        self.state_manager.log(f"进路 {start} -> {end} 已锁闭，信号开放", "SUCCESS")

    def cancel_route(self, start):
        """取消进路"""
        # 简化版：直接解锁（实际需检查接近占用情况）
        self.state_manager.log(f"取消进路: 信号机 {start}")
        self.simulator.set_signal(start, SignalColor.RED if not start.startswith("D") else SignalColor.BLUE)
        
        # 查找该信号机作为始端的进路并解锁
        # (此处逻辑待完善，需存储当前激活进路)
        self.state_manager.log("进路已人工取消", "INFO")
