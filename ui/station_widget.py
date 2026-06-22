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
        self.setMinimumSize(1000, 500)
        
        # 存储设备点击区域
        self.click_regions = {} # id -> (rect, type)
        self.y_3g = 150
        self.y_iig = 250
        self.y_1g = 350
        self.y_safety = 400
        
        self.x_start = 50
        self.x_x_signal = 150
        self.x_sw1 = 250
        self.x_sw3 = 350
        self.x_sw5 = 350
        self.x_track_start = 400
        self.x_track_end = 700
        self.x_sw4 = 750
        self.x_sw2 = 800
        self.x_s_signal = 850
        self.x_end = 950

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
        painter.fillRect(self.rect(), QColor(30, 30, 30))  # 背景深灰色
        
        self.draw_tracks(painter)
        self.draw_switches(painter)
        self.draw_signals(painter)
        self.draw_labels(painter)

    def draw_tracks(self, painter):
        # 轨道颜色定义
        color_idle = Qt.gray
        color_occupied = Qt.red
        color_locked = Qt.white
        
        def get_color(tid):
            tk = self.state_manager.tracks.get(tid)
            if not tk: return color_idle
            if tk.is_occupied: return color_occupied
            if tk.is_locked: return color_locked
            return color_idle

        pen = QPen(Qt.gray, 3)
        
        # JXG
        pen.setColor(get_color("JXG"))
        painter.setPen(pen)
        painter.drawLine(self.x_start, self.y_iig, self.x_x_signal, self.y_iig)
        
        # IIAG
        pen.setColor(get_color("IIAG"))
        painter.setPen(pen)
        painter.drawLine(self.x_x_signal, self.y_iig, self.x_sw1, self.y_iig)
        
        # IIG
        pen.setColor(get_color("IIG"))
        painter.setPen(pen)
        painter.drawLine(self.x_sw1, self.y_iig, self.x_sw4, self.y_iig)
        
        # 3G
        pen.setColor(get_color("3G"))
        painter.setPen(pen)
        painter.drawLine(self.x_sw3, self.y_3g, self.x_sw4, self.y_3g)
        
        # 1G
        pen.setColor(get_color("1G"))
        painter.setPen(pen)
        painter.drawLine(self.x_sw5, self.y_1g, self.x_sw2, self.y_1g)
        
        # 安全线
        pen.setColor(get_color("安全线"))
        painter.setPen(pen)
        painter.drawLine(self.x_sw5, self.y_safety, 200, self.y_safety)
        # 车挡
        painter.drawLine(200, self.y_safety - 10, 200, self.y_safety + 10)
        
        # IIBG
        pen.setColor(get_color("IIBG"))
        painter.setPen(pen)
        painter.drawLine(self.x_sw2, self.y_iig, self.x_s_signal, self.y_iig)
        
        # JSG
        pen.setColor(get_color("JSG"))
        painter.setPen(pen)
        painter.drawLine(self.x_s_signal, self.y_iig, self.x_end, self.y_iig)

    def draw_switches(self, painter):
        pen = QPen(Qt.gray, 3)
        
        def draw_sw_state(swid, x, y, is_vertical=False):
            sw = self.state_manager.switches[swid]
            if sw.is_locked:
                pen.setColor(Qt.white)
            elif sw.position == SwitchPosition.MOVING:
                pen.setColor(Qt.yellow)
            else:
                pen.setColor(Qt.gray)
            painter.setPen(pen)
            
            # 绘制道岔尖轨示意
            if sw.position == SwitchPosition.NORMAL:
                painter.drawLine(x, y, x + 30, y)
            elif sw.position == SwitchPosition.REVERSE:
                painter.drawLine(x, y, x + 20, y - 20 if not is_vertical else y + 20)
            else: # MOVING
                painter.drawLine(x, y, x + 25, y - 10)

        draw_sw_state("1", self.x_sw1, self.y_iig)
        draw_sw_state("3", self.x_sw3, self.y_3g)
        draw_sw_state("5", self.x_sw5, self.y_1g)
        draw_sw_state("4", self.x_sw4, self.y_iig)
        draw_sw_state("2", self.x_sw2, self.y_iig)

        # 绘制固定连接线 (浅色虚线或细线)
        pen_link = QPen(QColor(100, 100, 100), 1, Qt.DashLine)
        painter.setPen(pen_link)
        painter.drawLine(self.x_sw1, self.y_iig, self.x_sw3, self.y_3g)
        painter.drawLine(self.x_sw1, self.y_iig, self.x_sw5, self.y_1g)
        painter.drawLine(self.x_sw4, self.y_3g, self.x_sw4, self.y_iig)
        painter.drawLine(self.x_sw2, self.y_1g, self.x_sw2, self.y_iig)

    def draw_signals(self, painter):
        colors = {
            SignalColor.RED: Qt.red,
            SignalColor.GREEN: Qt.green,
            SignalColor.YELLOW: Qt.yellow,
            SignalColor.BLUE: Qt.blue,
            SignalColor.WHITE: Qt.white,
            SignalColor.OFF: Qt.black
        }

        def draw_sig(x, y, sid, direction="right"):
            sig = self.state_manager.signals[sid]
            painter.setBrush(QBrush(colors.get(sig.color, Qt.black)))
            painter.setPen(QPen(Qt.white, 1))
            
            # 信号机圆圈
            radius = 8
            rect = QRectF(x - radius, y - 15 - radius if direction=="right" else y + 15 - radius, radius*2, radius*2)
            painter.drawEllipse(rect)
            
            if direction == "right":
                painter.drawLine(x, y, x, y - 15) # 信号机柱
            else:
                painter.drawLine(x, y, x, y + 15)
            
            # 记录点击区域
            self.click_regions[sid] = (rect, "SIGNAL")

        # 进站信号
        draw_sig(self.x_x_signal, self.y_iig, "X", "right")
        draw_sig(self.x_s_signal, self.y_iig, "S", "left")
        
        # 出站信号
        draw_sig(self.x_track_end, self.y_3g, "X3", "right")
        draw_sig(self.x_track_end, self.y_iig, "XII", "right")
        draw_sig(self.x_track_end, self.y_1g, "X1", "right")
        
        draw_sig(self.x_track_start, self.y_3g, "S3", "left")
        draw_sig(self.x_track_start, self.y_iig, "SII", "left")
        draw_sig(self.x_track_start, self.y_1g, "S1", "left")
        
        # 调车信号
        draw_sig(200, self.y_iig, "D1", "right")
        draw_sig(750, self.y_iig, "D2", "left")

    def draw_labels(self, painter):
        painter.setPen(Qt.white)
        painter.setFont(QFont("Arial", 10))
        
        # 轨道区段名称
        painter.drawText(100, self.y_iig + 20, "JXG")
        painter.drawText(200, self.y_iig + 20, "IIAG")
        painter.drawText(500, self.y_3g - 10, "3G")
        painter.drawText(500, self.y_iig - 10, "IIG")
        painter.drawText(500, self.y_1g + 20, "1G")
        painter.drawText(220, self.y_safety + 20, "安全线")
        painter.drawText(750, self.y_iig + 20, "IIBG")
        painter.drawText(900, self.y_iig + 20, "JSG")
        
        # 信号机名称
        painter.drawText(self.x_x_signal - 10, self.y_iig - 25, "X")
        painter.drawText(self.x_s_signal - 10, self.y_iig + 35, "S")
        
        # 道岔名称
        painter.drawText(self.x_sw1 - 10, self.y_iig - 10, "1")
        painter.drawText(self.x_sw3 - 10, self.y_3g - 10, "3")
        painter.drawText(self.x_sw5 - 10, self.y_1g + 20, "5")
        painter.drawText(self.x_sw4 + 10, self.y_iig - 10, "4")
        painter.drawText(self.x_sw2 + 10, self.y_iig + 20, "2")
