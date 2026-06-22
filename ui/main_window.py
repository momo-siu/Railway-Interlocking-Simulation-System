from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTextEdit, QLabel, QGroupBox, QGridLayout)
from PyQt5.QtCore import Qt
from ui.station_widget import StationWidget
from utils.state_manager import StateManager
from utils.models import SignalColor, SwitchPosition
from logic.interlocking_engine import InterlockingEngine
from simulation.device_simulator import DeviceSimulator

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("计算机联锁模拟仿真系统")
        self.state_manager = StateManager()
        self.simulator = DeviceSimulator()
        self.engine = InterlockingEngine(self.simulator)
        
        self.route_start = None
        
        self.init_ui()
        self.state_manager.log_signal.connect(self.add_log)
        self.station_view.device_clicked.connect(self.handle_device_click)

    def handle_device_click(self, dtype, did):
        if dtype == "SIGNAL":
            if not self.route_start:
                self.route_start = did
                self.update_hint(f"已选择始端: {did}，请选择终端信号机")
                self.state_manager.log(f"选择进路始端: {did}")
            else:
                start = self.route_start
                end = did
                self.route_start = None
                self.update_hint("正在办理进路...")
                self.engine.try_set_route(start, end)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. 站场图形区
        self.station_view = StationWidget()
        main_layout.addWidget(self.station_view)

        # 2. 控制区
        control_layout = QHBoxLayout()
        
        # 进路操作
        route_group = QGroupBox("进路操作")
        route_layout = QGridLayout()
        self.btn_cancel = QPushButton("总取消")
        self.btn_human_release = QPushButton("总人解")
        self.btn_guide = QPushButton("引导进路")
        self.btn_guide_lock = QPushButton("引导总锁")
        
        self.btn_cancel.clicked.connect(self.handle_cancel)
        
        route_layout.addWidget(self.btn_cancel, 0, 0)
        route_layout.addWidget(self.btn_human_release, 0, 1)
        route_layout.addWidget(self.btn_guide, 1, 0)
        route_layout.addWidget(self.btn_guide_lock, 1, 1)
        route_group.setLayout(route_layout)
        control_layout.addWidget(route_group)

        # 道岔单操
        switch_group = QGroupBox("道岔单操")
        switch_layout = QGridLayout()
        for i in range(1, 6):
            sw_id = str(i)
            btn_dn = QPushButton(f"{i}# 定")
            btn_rev = QPushButton(f"{i}# 反")
            btn_lock = QPushButton(f"{i}# 锁")
            
            btn_dn.clicked.connect(lambda checked, s=sw_id: self.simulator.move_switch(s, SwitchPosition.NORMAL))
            btn_rev.clicked.connect(lambda checked, s=sw_id: self.simulator.move_switch(s, SwitchPosition.REVERSE))
            
            switch_layout.addWidget(btn_dn, i-1, 0)
            switch_layout.addWidget(btn_rev, i-1, 1)
            switch_layout.addWidget(btn_lock, i-1, 2)
        switch_group.setLayout(switch_layout)
        control_layout.addWidget(switch_group)

        # 仿真控制
        sim_group = QGroupBox("仿真模拟")
        sim_layout = QVBoxLayout()
        self.btn_occ_jxg = QPushButton("JXG 占用/出清")
        self.btn_occ_jsg = QPushButton("JSG 占用/出清")
        self.btn_occ_jxg.clicked.connect(lambda: self.toggle_occupancy("JXG"))
        self.btn_occ_jsg.clicked.connect(lambda: self.toggle_occupancy("JSG"))
        sim_layout.addWidget(self.btn_occ_jxg)
        sim_layout.addWidget(self.btn_occ_jsg)
        sim_group.setLayout(sim_layout)
        control_layout.addWidget(sim_group)

        main_layout.addLayout(control_layout)

        # 3. 日志与状态区
        info_layout = QHBoxLayout()
        
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(150)
        info_layout.addWidget(self.log_view, 2)
        
        status_panel = QVBoxLayout()
        self.lbl_timer = QLabel("解锁倒计时: --")
        self.lbl_op_hint = QLabel("提示: 请选择进路始端信号机")
        status_panel.addWidget(self.lbl_timer)
        status_panel.addWidget(self.lbl_op_hint)
        info_layout.addLayout(status_panel, 1)
        
        main_layout.addLayout(info_layout)

    def handle_cancel(self):
        self.route_start = None
        self.update_hint("请选择进路始端信号机")
        # 实际应调用 engine.cancel_all_routes() 或类似逻辑
        self.state_manager.log("执行总取消操作")
        # 简单实现：将所有设备解锁，信号关闭
        for sid in self.state_manager.signals:
            self.simulator.set_signal(sid, SignalColor.RED if not sid.startswith("D") else SignalColor.BLUE)
        for tid in self.state_manager.tracks:
            self.state_manager.update_track(tid, is_locked=False)
        for swid in self.state_manager.switches:
            self.state_manager.update_switch(swid, is_locked=False)

    def toggle_occupancy(self, tid):
        is_occ = self.state_manager.tracks[tid].is_occupied
        self.simulator.set_track_occupancy(tid, not is_occ)

    def add_log(self, level, message):
        self.log_view.append(f"[{level}] {message}")

    def update_hint(self, text):
        self.lbl_op_hint.setText(f"提示: {text}")
