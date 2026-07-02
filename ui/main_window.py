from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTextEdit, QLabel, QFrame, QGridLayout)
from PyQt5.QtCore import Qt, QTimer, QDateTime
from ui.station_widget import StationWidget
from utils.state_manager import StateManager
from utils.models import SwitchPosition
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
        self._last_sound_ms = {}
        
        self.route_start = None
        self._guide_lock_enabled = False
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
        self.btn_show_signal_labels = QPushButton("信号名")
        self.btn_show_track_labels = QPushButton("区段名")
        self.btn_show_switch_labels = QPushButton("道岔名")
        self.btn_show_route_highlight = QPushButton("进路高亮")
        self.btn_clear_log = QPushButton("清日志")
        
        for btn in [self.btn_cancel, self.btn_human_release, self.btn_guide, self.btn_guide_lock]:
            btn.setStyleSheet(btn_style)
            
        left_grid.addWidget(self.btn_cancel, 0, 0)
        left_grid.addWidget(self.btn_human_release, 0, 1)
        left_grid.addWidget(self.btn_guide, 1, 0)
        left_grid.addWidget(self.btn_guide_lock, 1, 1)

        small_btn_style = """
            QPushButton {
                background-color: rgba(51, 51, 51, 160); color: white; border: 1px solid #555;
                padding: 6px 10px; font-weight: bold; font-size: 14px;
                min-width: 90px; min-height: 36px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: rgba(68, 68, 68, 210); border: 1px solid #888; }
            QPushButton:pressed { background-color: #111; }
            QPushButton:checked { border: 2px solid #00ff00; }
        """
        for btn in [
            self.btn_show_signal_labels,
            self.btn_show_track_labels,
            self.btn_show_switch_labels,
            self.btn_show_route_highlight,
            self.btn_clear_log,
        ]:
            btn.setStyleSheet(small_btn_style)

        for btn in [
            self.btn_show_signal_labels,
            self.btn_show_track_labels,
            self.btn_show_switch_labels,
            self.btn_show_route_highlight,
        ]:
            btn.setCheckable(True)
            btn.setChecked(True)

        left_grid.addWidget(self.btn_show_signal_labels, 2, 0)
        left_grid.addWidget(self.btn_show_track_labels, 2, 1)
        left_grid.addWidget(self.btn_show_switch_labels, 3, 0)
        left_grid.addWidget(self.btn_show_route_highlight, 3, 1)
        left_grid.addWidget(self.btn_clear_log, 4, 0, 1, 2)

        self.btn_cancel.clicked.connect(self.handle_cancel)
        self.btn_human_release.clicked.connect(self.handle_human_release)
        self.btn_guide.clicked.connect(self.handle_guide)
        self.btn_guide_lock.clicked.connect(self.handle_guide_lock_toggle)
        self.btn_show_signal_labels.toggled.connect(lambda v: self.station_view.set_view_options(show_signal_labels=v))
        self.btn_show_track_labels.toggled.connect(lambda v: self.station_view.set_view_options(show_track_labels=v))
        self.btn_show_switch_labels.toggled.connect(lambda v: self.station_view.set_view_options(show_switch_labels=v))
        self.btn_show_route_highlight.toggled.connect(lambda v: self.station_view.set_view_options(show_route_highlight=v))
        self.btn_clear_log.clicked.connect(self._clear_log)
        
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
            
            # 优化排布：定反位上下分布，1-5号从左到右
            col = i - 1
            right_grid.addWidget(btn_dn, 0, col)  # 第一行：定
            right_grid.addWidget(btn_rev, 1, col) # 第二行：反

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

    def _clear_log(self):
        if hasattr(self, "log_view"):
            self.log_view.clear()

    def handle_device_click(self, dtype, did):
        if dtype == "SIGNAL":
            self.sound_manager.play_ding()
            if not self.route_start:
                self.route_start = did
                route_type = "SHUNTING" if did.startswith("D") else "TRAIN"
                routes = self.state_manager.list_routes_from_start(did, route_type=route_type)
                ends = sorted({r.end_signal for r in routes})
                if ends:
                    self.update_hint(f"已选择始端: {did}，可选终端: {' / '.join(ends)}")
                else:
                    self.update_hint(f"已选择始端: {did}，请选择终端信号机")
            else:
                start = self.route_start
                end = did
                if start == end:
                    self.route_start = None
                    self.update_hint("已取消选路")
                    return

                self.update_hint(f"正在办理进路: {start} -> {end}")
                ok = self.engine.try_set_route(start, end)
                if ok:
                    self.route_start = None
                else:
                    self.update_hint("办理失败，请按日志提示重新选择终端信号机")
        elif dtype == "BUTTON":
            self.sound_manager.play_ding()
            if did == "PZA":
                self.state_manager.log("[INFO] PZA按钮：人工操作触发")
                self.update_hint("PZA按钮已触发")

    def handle_cancel(self):
        self.sound_manager.play_ding()
        self.route_start = None
        self.update_hint("执行总取消")
        self.engine.cancel_route()

    def handle_human_release(self):
        self.sound_manager.play_ding()
        self.update_hint("执行总人解")
        self.engine.manual_unlock()

    def handle_guide(self):
        self.sound_manager.play_ding()
        if not self.route_start:
            self.update_hint("请先选择需要开放引导的信号机")
            return
        start = self.route_start
        self.route_start = None
        self.update_hint(f"开放引导: {start}")
        self.engine.guide_control(start)

    def handle_guide_lock_toggle(self):
        self.sound_manager.play_ding()
        self._guide_lock_enabled = not self._guide_lock_enabled
        self.engine.set_guide_lock(self._guide_lock_enabled)
        text = "引导总锁(开)" if self._guide_lock_enabled else "引导总锁"
        self.btn_guide_lock.setText(text)

    def toggle_occupancy(self, tid):
        self.sound_manager.play_ding()
        is_occ = self.state_manager.tracks[tid].is_occupied
        self.engine.simulate_track_occupancy(tid, not is_occ)
        if not is_occ:
            self.sound_manager.play_alert()

    def add_log(self, level, message):
        now_ms = QDateTime.currentMSecsSinceEpoch()

        def play_throttled(key: str, play_fn):
            last = self._last_sound_ms.get(key, 0)
            if now_ms - last < 800:
                return
            self._last_sound_ms[key] = now_ms
            play_fn()

        color = "#00FF00" if level == "SUCCESS" else "white"
        if level == "ERROR": color = "red"
        self.log_view.append(f"<span style='color:{color}'>[{level}] {message}</span>")

        if "总人解：启动倒计时 180" in message:
            play_throttled("manual_unlock_3min", self.sound_manager.play_manual_unlock_3min)
            return

        if message.startswith("进路征用："):
            try:
                after = message.split("：", 1)[1].strip()
                parts = after.split()
                if len(parts) >= 2 and parts[1] in ("X", "S"):
                    play_throttled("prepare_receive", self.sound_manager.play_prepare_receive)
                    return
            except Exception:
                pass

        if "断丝" in message:
            play_throttled("filament_fault", self.sound_manager.play_filament_fault)
            return

        if level == "ERROR":
            if "未定义进路" in message or "进路选不出" in message:
                play_throttled("route_not_found", self.sound_manager.play_route_not_found)
            else:
                play_throttled("op_invalid", self.sound_manager.play_op_invalid)

    def update_hint(self, text):
        self.lbl_hint.setText(f"提示: {text}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.showNormal()  # 按 Esc 退出全屏
