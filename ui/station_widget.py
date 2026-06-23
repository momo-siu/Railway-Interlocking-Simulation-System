from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QFont
from utils.state_manager import StateManager
from utils.models import SignalColor, SwitchPosition

class StationWidget(QWidget):
    device_clicked = pyqtSignal(str, str)  # device_type, device_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state_manager = StateManager()
        self.state_manager.state_changed.connect(self.update_ui)
        self.setMinimumSize(1200, 600)
        
        # 存储设备点击区域
        self.click_regions = {} # id -> (rect, type)
        
        # 基础坐标定义 (重构为百分比或更合理的固定值以适应全屏)
        self.center_y = 400
        self.y_3g = self.center_y - 100
        self.y_iig = self.center_y
        self.y_1g = self.center_y + 100
        self.y_safety = self.center_y + 150
        
        self.x_start = 50
        self.x_x_signal = 150
        self.x_d1 = 220
        self.x_sw1 = 300
        
        # 斜线分岔点
        self.x_sw3_entry = 400
        self.x_sw5_entry = 400
        
        self.x_track_start = 450
        self.x_track_end = 850
        
        self.x_sw4 = 950
        self.x_sw2 = 950
        
        self.x_s_signal = 1100
        self.x_end = 1250

    def update_ui(self, device_id, state):
        self.update()

    def mousePressEvent(self, event):
        pos = event.pos()
        for sid, (rect, dtype) in self.click_regions.items():
            if rect.contains(QPointF(pos)):
                self.device_clicked.emit(dtype, sid)
                return

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0))  # 纯黑背景，符合专业UI
        
        self.draw_tracks(painter)
        self.draw_switches(painter)
        self.draw_signals(painter)
        self.draw_labels(painter)

    def draw_tracks(self, painter):
        # 颜色定义
        color_idle = QColor(0, 191, 255)  # 浅蓝色空闲
        color_occupied = Qt.red
        color_locked = Qt.white
        
        def get_pen(tid, width=3):
            tk = self.state_manager.tracks.get(tid)
            color = color_idle
            if tk:
                if tk.is_occupied: color = color_occupied
                elif tk.is_locked: color = color_locked
            return QPen(color, width)

        # 1. JXG
        painter.setPen(get_pen("JXG"))
        painter.drawLine(self.x_start, self.y_iig, self.x_x_signal, self.y_iig)
        
        # 2. IIAG
        painter.setPen(get_pen("IIAG"))
        painter.drawLine(self.x_x_signal, self.y_iig, self.x_sw1, self.y_iig)
        
        # 3. IIG (正线股道)
        painter.setPen(get_pen("IIG"))
        painter.drawLine(self.x_sw1, self.y_iig, self.x_sw4, self.y_iig)
        
        # 4. 3G (上方侧线)
        painter.setPen(get_pen("3G"))
        painter.drawLine(self.x_sw3_entry, self.y_3g, self.x_sw4, self.y_3g)
        
        # 5. 1G (下方侧线)
        painter.setPen(get_pen("1G"))
        painter.drawLine(self.x_sw5_entry, self.y_1g, self.x_sw2, self.y_1g)
        
        # 6. 安全线
        painter.setPen(get_pen("安全线"))
        painter.drawLine(self.x_sw5_entry, self.y_safety, self.x_sw5_entry - 100, self.y_safety)
        # 车挡
        painter.drawLine(self.x_sw5_entry - 100, self.y_safety - 10, self.x_sw5_entry - 100, self.y_safety + 10)
        
        # 7. IIBG
        painter.setPen(get_pen("IIBG"))
        painter.drawLine(self.x_sw4, self.y_iig, self.x_s_signal, self.y_iig)
        
        # 8. JSG
        painter.setPen(get_pen("JSG"))
        painter.drawLine(self.x_s_signal, self.y_iig, self.x_end, self.y_iig)

    def draw_switches(self, painter):
        # 斜线连接逻辑
        color_idle = QColor(0, 191, 255)
        
        def draw_diagonal_switch(swid, start_p, end_p, is_reverse_active):
            sw = self.state_manager.switches[swid]
            color = color_idle
            if sw.is_locked: color = Qt.white
            elif sw.position == SwitchPosition.MOVING: color = Qt.yellow
            
            # 基础虚线背景（表示物理存在）
            p_bg = QPen(QColor(60, 60, 60), 1, Qt.DashLine)
            painter.setPen(p_bg)
            painter.drawLine(start_p, end_p)
            
            # 实际连通线
            if is_reverse_active:
                p_active = QPen(color, 3)
                painter.setPen(p_active)
                painter.drawLine(start_p, end_p)

        # 1# 道岔区域 (IIAG末端)
        sw1 = self.state_manager.switches["1"]
        # 直向 (IIG)
        draw_diagonal_switch("1", QPointF(self.x_sw1, self.y_iig), QPointF(self.x_sw1 + 40, self.y_iig), sw1.position == SwitchPosition.NORMAL)
        # 侧向 (向上 3G)
        draw_diagonal_switch("1", QPointF(self.x_sw1, self.y_iig), QPointF(self.x_sw3_entry, self.y_3g), sw1.position == SwitchPosition.REVERSE)
        # 侧向 (向下 1G/安全线)
        # 注意：这里逻辑上 1# 可能有多个反位分支，或者 5# 在 1# 的侧线上
        painter.setPen(QPen(QColor(60, 60, 60), 1, Qt.DashLine))
        painter.drawLine(self.x_sw1, self.y_iig, self.x_sw5_entry, self.y_1g)

        # 3# 道岔 (3G入口)
        # 4# 道岔 (IIG/3G出口汇合)
        draw_diagonal_switch("4", QPointF(self.x_sw4, self.y_3g), QPointF(self.x_sw4 + 50, self.y_iig), True) # 示意连接
        
        # 2# 道岔 (1G出口汇合)
        draw_diagonal_switch("2", QPointF(self.x_sw2, self.y_1g), QPointF(self.x_sw2 + 50, self.y_iig), True)

        # 5# 道岔 (安全线/1G分岔)
        draw_diagonal_switch("5", QPointF(self.x_sw1 + 50, self.y_iig + 25), QPointF(self.x_sw5_entry, self.y_safety), True)

    def draw_signals(self, painter):
        colors = {
            SignalColor.RED: Qt.red,
            SignalColor.GREEN: QColor(0, 255, 0),
            SignalColor.YELLOW: Qt.yellow,
            SignalColor.BLUE: QColor(0, 0, 255),
            SignalColor.WHITE: Qt.white,
            SignalColor.OFF: Qt.black
        }

        def draw_sig_pro(x, y, sid, direction="right", is_d=False):
            sig = self.state_manager.signals[sid]
            radius = 8 if not is_d else 6
            
            # 绘制信号机架
            painter.setPen(QPen(Qt.white, 2))
            if direction == "right":
                painter.drawLine(x, y, x, y - 20)
                rect = QRectF(x, y - 25, radius*2, radius*2)
            else:
                painter.drawLine(x, y, x, y + 20)
                rect = QRectF(x - radius*2, y + 5, radius*2, radius*2)
            
            # 绘制灯光
            painter.setBrush(QBrush(colors.get(sig.color, Qt.black)))
            painter.drawEllipse(rect)
            
            # 点击区域
            self.click_regions[sid] = (rect, "SIGNAL")

        # 进站
        draw_sig_pro(self.x_x_signal, self.y_iig, "X", "right")
        draw_sig_pro(self.x_s_signal, self.y_iig, "S", "left")
        
        # 出站
        draw_sig_pro(self.x_track_end, self.y_3g, "X3", "right")
        draw_sig_pro(self.x_track_end, self.y_iig, "XII", "right")
        draw_sig_pro(self.x_track_end, self.y_1g, "X1", "right")
        
        draw_sig_pro(self.x_track_start + 50, self.y_3g, "S3", "left")
        draw_sig_pro(self.x_track_start + 50, self.y_iig, "SII", "left")
        draw_sig_pro(self.x_track_start + 50, self.y_1g, "S1", "left")
        
        # 调车
        draw_sig_pro(self.x_d1, self.y_iig, "D1", "right", True)
        draw_sig_pro(self.x_sw4 - 50, self.y_iig, "D2", "left", True)

    def draw_labels(self, painter):
        painter.setPen(Qt.white)
        painter.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        
        # 站名
        painter.setFont(QFont("Microsoft YaHei", 24, QFont.Bold))
        painter.setPen(QColor(0, 255, 0))
        painter.drawText(self.rect(), Qt.AlignTop | Qt.AlignHCenter, "\n标 准 站")
        
        painter.setFont(QFont("Microsoft YaHei", 10))
        painter.setPen(Qt.white)
        # 轨道名称
        painter.drawText(self.x_start + 20, self.y_iig + 25, "JXG")
        painter.drawText(self.x_track_start + 100, self.y_3g - 15, "3G")
        painter.drawText(self.x_track_start + 100, self.y_iig - 15, "IIG")
        painter.drawText(self.x_track_start + 100, self.y_1g + 25, "1G")
        
        # 方向
        painter.setPen(Qt.yellow)
        painter.drawText(self.x_start, self.y_iig - 40, "← 下行方向")
        painter.drawText(self.x_end - 100, self.y_iig + 60, "上行方向 →")

        # 版权/提示
        painter.setFont(QFont("Microsoft YaHei", 32, QFont.Bold))
        painter.setPen(QColor(0, 255, 0, 100)) # 半透明绿色
        painter.drawText(self.rect(), Qt.AlignBottom | Qt.AlignHCenter, "试用版 (非商用)\n")
