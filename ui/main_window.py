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
        
        # 使用底层的主布局，将站场图放在最底层
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. 站场图形核心区 (占据整个背景)
        self.station_view = StationWidget(central_widget)
        
        # 2. 悬浮按钮层 (直接浮动在 station_view 上方)
        # 我们通过设置按钮的 parent 为 station_view 来实现悬浮
        
        btn_style = """
            QPushButton { 
                background-color: rgba(51, 51, 51, 180); color: white; border: 1px solid #555; 
                padding: 10px 15px; font-weight: bold; font-size: 20px;
                min-width: 120px; min-height: 60px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: rgba(68, 68, 68, 220); border: 1px solid #888; }
            QPushButton:pressed { background-color: #111; }
        """
        
        # 左侧悬浮控制组
        self.left_floating_area = QFrame(self.station_view)
        left_grid = QGridLayout(self.left_floating_area)
        left_grid.setSpacing(25)
        
        self.btn_cancel = QPushButton("总 取 消")
        self.btn_human_release = QPushButton("总 人 解")
        self.btn_guide = QPushButton("引 导")
        self.btn_guide_lock = QPushButton("引导总锁")
        
        for btn in [self.btn_cancel, self.btn_human_release, self.btn_guide, self.btn_guide_lock]:
            btn.setStyleSheet(btn_style)
            
        left_grid.addWidget(self.btn_cancel, 0, 0)
        left_grid.addWidget(self.btn_human_release, 0, 1)
        left_grid.addWidget(self.btn_guide, 1, 0)
        left_grid.addWidget(self.btn_guide_lock, 1, 1)
        self.btn_cancel.clicked.connect(self.handle_cancel)
        
        # 右侧悬浮控制组
        self.right_floating_area = QFrame(self.station_view)
        right_grid = QGridLayout(self.right_floating_area)
        right_grid.setSpacing(25)
        
        for i in range(1, 6):
            btn_dn = QPushButton(f"{i}# 定")
            btn_rev = QPushButton(f"{i}# 反")
            btn_dn.setStyleSheet(btn_style)
            btn_rev.setStyleSheet(btn_style)
            sw_id = str(i)
            btn_dn.clicked.connect(lambda checked, s=sw_id: self.simulator.move_switch(s, SwitchPosition.NORMAL))
            btn_rev.clicked.connect(lambda checked, s=sw_id: self.simulator.move_switch(s, SwitchPosition.REVERSE))
            row = 0 if i <= 3 else 1
            col = (i - 1) % 3 * 2
            right_grid.addWidget(btn_dn, row, col)
            right_grid.addWidget(btn_rev, row, col + 1)

        # 初始位置定位 (会在 resizeEvent 中动态调整)
        self.left_floating_area.move(40, 40)
        
        self.main_layout.addWidget(self.station_view, 1)

        # 3. 底部状态与日志区 (保持固定在底部)
        bottom_panel = QFrame()
        bottom_panel.setFixedHeight(220)
        bottom_panel.setStyleSheet("background-color: #111; border-top: 2px solid #555;")
        bottom_layout = QHBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(20, 10, 20, 10)
        
        # 日志
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("background-color: black; color: #00FF00; border: 1px solid #333; font-family: 'Consolas'; font-size: 18px;")
        bottom_layout.addWidget(self.log_view, 3)
        
        # 状态信息
        status_info = QVBoxLayout()
        self.lbl_hint = QLabel("提示: 系统就绪")
        self.lbl_hint.setStyleSheet("color: yellow; font-size: 20px; font-weight: bold;")
        self.lbl_time = QLabel()
        self.lbl_time.setStyleSheet("font-size: 28px; font-family: 'Consolas'; color: white;")
        
        status_info.addWidget(self.lbl_hint)
        status_info.addWidget(self.lbl_time)
        
        # 模拟控制按钮
        sim_btns = QHBoxLayout()
        self.btn_occ_jxg = QPushButton("模拟JXG占用")
        self.btn_occ_jsg = QPushButton("模拟JSG占用")
        sim_btn_style = btn_style + "QPushButton { font-size: 16px; min-height: 40px; min-width: 100px; }"
        for b in [self.btn_occ_jxg, self.btn_occ_jsg]:
            b.setStyleSheet(sim_btn_style)
        self.btn_occ_jxg.clicked.connect(lambda: self.toggle_occupancy("JXG"))
        self.btn_occ_jsg.clicked.connect(lambda: self.toggle_occupancy("JSG"))
        sim_btns.addWidget(self.btn_occ_jxg)
        sim_btns.addWidget(self.btn_occ_jsg)
        status_info.addLayout(sim_btns)
        
        bottom_layout.addLayout(status_info, 1)
        self.main_layout.addWidget(bottom_panel)

    def resizeEvent(self, event):
        # 当窗口大小变化时，重新定位悬浮按钮区域
        margin = 40
        
        if hasattr(self, 'left_floating_area'):
            # 强制让布局计算出大小
            self.left_floating_area.adjustSize()
            self.left_floating_area.move(margin, margin)
            
        if hasattr(self, 'right_floating_area'):
            # 强制让布局计算出大小
            self.right_floating_area.adjustSize()
            # 重新计算右侧位置：窗口宽度 - 区域宽度 - 边距
            self.right_floating_area.move(self.width() - self.right_floating_area.width() - margin, margin)
            
        super().resizeEvent(event)

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
