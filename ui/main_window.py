from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTextEdit, QLabel, QFrame, QGridLayout)
from PyQt5.QtCore import Qt, QTimer, QDateTime
from ui.station_widget import StationWidget
from utils.state_manager import StateManager
from utils.models import SignalColor, SwitchPosition
from utils.sound_manager import SoundManager
from logic.interlocking_engine import InterlockingEngine
from simulation.device_simulator import DeviceSimulator

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("计算机联锁模拟仿真系统 - 通号模式")
        self.state_manager = StateManager()
        self.simulator = DeviceSimulator()
        self.engine = InterlockingEngine(self.simulator)
        self.sound_manager = SoundManager()
        
        self.route_start = None
        self.init_ui()
        
        # 信号连接
        self.state_manager.log_signal.connect(self.add_log)
        self.station_view.device_clicked.connect(self.handle_device_click)
        
        # 定时更新时间
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        
        # 设为全屏
        self.showFullScreen()

    def init_ui(self):
        self.setStyleSheet("background-color: black; color: white;")
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. 顶部按钮工具栏 (参考专业UI)
        top_bar = QFrame()
        top_bar.setFixedHeight(60)
        top_bar.setStyleSheet("background-color: #222; border-bottom: 1px solid #444;")
        top_layout = QHBoxLayout(top_bar)
        
        btn_style = """
            QPushButton { 
                background-color: #333; color: white; border: 1px solid #555; 
                padding: 5px 10px; font-weight: bold; 
            }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #222; }
        """
        
        self.btn_cancel = QPushButton("总 取 消")
        self.btn_human_release = QPushButton("总 人 解")
        self.btn_cancel.setStyleSheet(btn_style)
        self.btn_human_release.setStyleSheet(btn_style)
        self.btn_cancel.clicked.connect(self.handle_cancel)
        
        top_layout.addWidget(self.btn_cancel)
        top_layout.addWidget(self.btn_human_release)
        top_layout.addStretch()
        
        # 道岔单操按钮组
        for i in range(1, 6):
            btn_dn = QPushButton(f"{i}# 定")
            btn_rev = QPushButton(f"{i}# 反")
            btn_dn.setStyleSheet(btn_style)
            btn_rev.setStyleSheet(btn_style)
            sw_id = str(i)
            btn_dn.clicked.connect(lambda checked, s=sw_id: self.simulator.move_switch(s, SwitchPosition.NORMAL))
            btn_rev.clicked.connect(lambda checked, s=sw_id: self.simulator.move_switch(s, SwitchPosition.REVERSE))
            top_layout.addWidget(btn_dn)
            top_layout.addWidget(btn_rev)

        main_layout.addWidget(top_bar)

        # 2. 站场图形核心区
        self.station_view = StationWidget()
        main_layout.addWidget(self.station_view, 1)

        # 3. 底部状态与日志区
        bottom_panel = QFrame()
        bottom_panel.setFixedHeight(150)
        bottom_panel.setStyleSheet("background-color: #111; border-top: 1px solid #444;")
        bottom_layout = QHBoxLayout(bottom_panel)
        
        # 日志
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("background-color: black; color: #00FF00; border: none; font-family: 'Consolas';")
        bottom_layout.addWidget(self.log_view, 3)
        
        # 状态信息
        status_info = QVBoxLayout()
        self.lbl_hint = QLabel("提示: 系统就绪")
        self.lbl_hint.setStyleSheet("color: yellow; font-size: 14px; font-weight: bold;")
        self.lbl_time = QLabel()
        self.lbl_time.setStyleSheet("font-size: 24px; font-family: 'Consolas'; color: white;")
        
        status_info.addWidget(self.lbl_hint)
        status_info.addWidget(self.lbl_time)
        
        # 模拟控制按钮
        sim_btns = QHBoxLayout()
        self.btn_occ_jxg = QPushButton("模拟JXG占用")
        self.btn_occ_jsg = QPushButton("模拟JSG占用")
        for b in [self.btn_occ_jxg, self.btn_occ_jsg]:
            b.setStyleSheet(btn_style)
        self.btn_occ_jxg.clicked.connect(lambda: self.toggle_occupancy("JXG"))
        self.btn_occ_jsg.clicked.connect(lambda: self.toggle_occupancy("JSG"))
        sim_btns.addWidget(self.btn_occ_jxg)
        sim_btns.addWidget(self.btn_occ_jsg)
        status_info.addLayout(sim_btns)
        
        bottom_layout.addLayout(status_info, 1)
        main_layout.addWidget(bottom_panel)

    def update_time(self):
        self.lbl_time.setText(QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss"))

    def handle_device_click(self, dtype, did):
        if dtype == "SIGNAL":
            self.sound_manager.play_ding()
            if not self.route_start:
                self.route_start = did
                self.update_hint(f"已选择始端: {did}，请选择终端信号机")
            else:
                start = self.route_start
                end = did
                self.route_start = None
                self.update_hint(f"正在办理进路: {start} -> {end}")
                self.engine.try_set_route(start, end)

    def handle_cancel(self):
        self.sound_manager.play_ding()
        self.route_start = None
        self.update_hint("执行总取消")
        for sid in self.state_manager.signals:
            self.simulator.set_signal(sid, SignalColor.RED if not sid.startswith("D") else SignalColor.BLUE)
        for tid in self.state_manager.tracks:
            self.state_manager.update_track(tid, is_locked=False)
        for swid in self.state_manager.switches:
            self.state_manager.update_switch(swid, is_locked=False)

    def toggle_occupancy(self, tid):
        self.sound_manager.play_ding()
        is_occ = self.state_manager.tracks[tid].is_occupied
        self.simulator.set_track_occupancy(tid, not is_occ)
        if not is_occ:
            self.sound_manager.play_alert()

    def add_log(self, level, message):
        color = "#00FF00" if level == "SUCCESS" else "white"
        if level == "ERROR": color = "red"
        self.log_view.append(f"<span style='color:{color}'>[{level}] {message}</span>")
        if level == "ERROR":
            self.sound_manager.play_alert()

    def update_hint(self, text):
        self.lbl_hint.setText(f"提示: {text}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.showNormal()  # 按 Esc 退出全屏
