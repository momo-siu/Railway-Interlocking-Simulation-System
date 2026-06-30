from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QFont
from utils.state_manager import StateManager
from utils.models import SignalColor, SwitchPosition, RouteStage, SignalAspect

class StationWidget(QWidget):
    device_clicked = pyqtSignal(str, str)  # device_type, device_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state_manager = StateManager()
        self.state_manager.state_changed.connect(self.update_ui)
        self.setMinimumSize(1200, 600)
        
        # 存储设备点击区域
        self.click_regions = {} # id -> (rect, type)

        self.show_signal_labels = True
        self.show_track_labels = True
        self.show_switch_labels = True
        self.show_route_highlight = True
        
        # 基础坐标定义 - 调大并准备居中
        self.base_x_offset = 100
        self.center_y = 450 # 稍微下移，为顶部按钮留出更多空间
        self.y_3g = self.center_y - 120
        self.y_iig = self.center_y
        self.y_1g = self.center_y + 120
        self.y_safety = self.y_1g
        
        self.x_start = self.base_x_offset
        self.x_x_signal = self.base_x_offset + 150
        self.x_d1 = self.base_x_offset + 250
        self.x_sw1 = self.base_x_offset + 350
        
        # 斜线分岔点 - 间距加大
        self.x_sw3_entry = self.base_x_offset + 500
        self.x_sw5_entry = self.base_x_offset + 500
        
        self.x_track_start = self.base_x_offset + 550
        self.x_track_end = self.base_x_offset + 1050
        
        self.x_sw4 = self.base_x_offset + 1150
        self.x_sw2 = self.base_x_offset + 1200
        
        self.x_s_signal = self.base_x_offset + 1350
        self.x_end = self.base_x_offset + 1550

    def set_view_options(
        self,
        show_signal_labels=None,
        show_track_labels=None,
        show_switch_labels=None,
        show_route_highlight=None,
    ):
        if show_signal_labels is not None:
            self.show_signal_labels = bool(show_signal_labels)
        if show_track_labels is not None:
            self.show_track_labels = bool(show_track_labels)
        if show_switch_labels is not None:
            self.show_switch_labels = bool(show_switch_labels)
        if show_route_highlight is not None:
            self.show_route_highlight = bool(show_route_highlight)
        self.update()

    def update_ui(self, device_id, state):
        self.update()

    def mousePressEvent(self, event):
        pos = event.pos()
        for sid, (rect, dtype) in self.click_regions.items():
            if rect.contains(QPointF(pos)):
                self.device_clicked.emit(dtype, sid)
                return

    def paintEvent(self, event):
        # 动态计算居中偏移量
        total_station_width = 1550 # 根据 x_end 的大致范围
        self.base_x_offset = max(50, (self.width() - total_station_width) // 2)
        
        # 站场图下移至屏幕垂直正中心 (考虑顶部工具栏高度后)
        self.center_y = self.height() // 2 + 50 # 50 是为了平衡视觉重心
        self.y_3g = self.center_y - 120
        self.y_iig = self.center_y
        self.y_1g = self.center_y + 120
        self.y_safety = self.y_1g
        
        # 更新所有依赖 base_x_offset 的坐标 (确保为整数)
        self.x_start = int(self.base_x_offset)
        self.x_x_signal = self.x_start + 150
        self.x_d1 = self.x_start + 250
        self.x_sw1 = self.x_start + 350
        self.x_sw3_entry = self.x_start + 500
        self.x_sw5_entry = self.x_start + 500
        self.x_track_start = self.x_start + 550
        self.x_track_end = self.x_start + 1050
        self.x_sw4 = self.x_start + 1150
        self.x_sw2 = self.x_start + 1200
        self.x_s_signal = self.x_start + 1350
        self.x_end = self.x_start + 1550
        self.x_3g_left = self.x_sw3_entry + 80
        self.x_3g_right = self.x_sw4 - 80
        self.x_1g_left = self.x_sw1 + 260
        self.x_1g_right = self.x_sw2 - 80
        self.x_safety_left = self.x_1g_left
        self.x_safety_bumper = self.x_safety_left - 120

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0))  # 纯黑背景，符合专业UI
        
        self.click_regions = {}
        self.draw_tracks(painter)
        self.draw_insulated_joints(painter)
        self.draw_switches(painter)
        self.draw_route_highlight(painter)
        self.draw_signals(painter)
        self.draw_labels(painter)
        self.draw_pza_button(painter)

    def draw_insulated_joints(self, painter):
        painter.setPen(QPen(QColor(200, 200, 200), 2))

        def draw_joint(x: int, y: int):
            painter.drawLine(int(x), int(y) - 8, int(x), int(y) + 8)

        joints = [
            (self.x_x_signal, self.y_iig),
            (self.x_sw1, self.y_iig),
            (self.x_sw3_entry, self.y_iig),
            (self.x_3g_left, self.y_3g),
            (self.x_3g_right, self.y_3g),
            (self.x_1g_left, self.y_1g),
            (self.x_1g_right, self.y_1g),
            (self.x_safety_left, self.y_safety),
            (self.x_sw4, self.y_iig),
            (self.x_sw2, self.y_iig),
            (self.x_s_signal, self.y_iig),
        ]
        for x, y in joints:
            draw_joint(x, y)

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
        painter.drawLine(self.x_3g_left, self.y_3g, self.x_3g_right, self.y_3g)
        
        # 5. 1G (下方侧线)
        painter.setPen(get_pen("1G"))
        painter.drawLine(self.x_1g_left, self.y_1g, self.x_1g_right, self.y_1g)
        
        # 6. 安全线
        painter.setPen(get_pen("安全线"))
        painter.drawLine(self.x_safety_left, self.y_safety, self.x_safety_bumper, self.y_safety)
        # 车挡
        painter.drawLine(self.x_safety_bumper, self.y_safety - 10, self.x_safety_bumper, self.y_safety + 10)
        
        # 7. IIBG
        painter.setPen(get_pen("IIBG"))
        painter.drawLine(self.x_sw4, self.y_iig, self.x_s_signal, self.y_iig)
        
        # 8. JSG
        painter.setPen(get_pen("JSG"))
        painter.drawLine(self.x_s_signal, self.y_iig, self.x_end, self.y_iig)

    def draw_route_highlight(self, painter):
        if not self.show_route_highlight:
            return

        active = [
            r for r in self.state_manager.routes.values()
            if r.is_active and r.stage in (RouteStage.PRELOCKED, RouteStage.OPENED, RouteStage.APPROACH_LOCKED, RouteStage.RELEASING)
        ]
        if not active:
            return

        base_track_segments = {
            "JXG": [(self.x_start, self.y_iig, self.x_x_signal, self.y_iig)],
            "IIAG": [(self.x_x_signal, self.y_iig, self.x_sw1, self.y_iig)],
            "IIG": [(self.x_sw1, self.y_iig, self.x_sw4, self.y_iig)],
            "3G": [(self.x_3g_left, self.y_3g, self.x_3g_right, self.y_3g)],
            "1G": [(self.x_1g_left, self.y_1g, self.x_1g_right, self.y_1g)],
            "安全线": [(self.x_safety_left, self.y_safety, self.x_safety_bumper, self.y_safety)],
            "JSG": [(self.x_s_signal, self.y_iig, self.x_end, self.y_iig)],
        }

        switch_segments = {
            "1": {
                SwitchPosition.NORMAL: [(self.x_sw1, self.y_iig, self.x_sw1 + 70, self.y_iig)],
                SwitchPosition.REVERSE: [(self.x_sw1, self.y_iig, self.x_3g_left, self.y_3g)],
            },
            "3": {
                SwitchPosition.NORMAL: [(self.x_sw3_entry, self.y_iig, self.x_sw3_entry + 60, self.y_iig)],
                SwitchPosition.REVERSE: [(self.x_sw3_entry, self.y_iig, self.x_1g_left, self.y_1g)],
            },
            "5": {
                SwitchPosition.NORMAL: [(self.x_1g_left, self.y_1g, self.x_1g_left + 60, self.y_1g)],
                SwitchPosition.REVERSE: [(self.x_1g_left, self.y_1g, self.x_sw3_entry, self.y_iig)],
            },
            "4": {
                SwitchPosition.NORMAL: [(self.x_sw4, self.y_iig, self.x_sw4 + 60, self.y_iig)],
                SwitchPosition.REVERSE: [(self.x_sw4, self.y_iig, self.x_3g_right, self.y_3g)],
            },
            "2": {
                SwitchPosition.NORMAL: [(self.x_sw2, self.y_iig, self.x_sw2 + 60, self.y_iig)],
                SwitchPosition.REVERSE: [(self.x_sw2, self.y_iig, self.x_1g_right, self.y_1g)],
            },
        }

        painter.setPen(QPen(QColor(255, 0, 0), 4))
        for r in active:
            for tid in r.path_tracks:
                if tid == "IIBG":
                    iibh_start_x = self.x_sw4
                    if "2" in r.path_switches:
                        iibh_start_x = self.x_sw2
                    for x1, y1, x2, y2 in [(iibh_start_x, self.y_iig, self.x_s_signal, self.y_iig)]:
                        painter.drawLine(x1, y1, x2, y2)
                else:
                    for x1, y1, x2, y2 in base_track_segments.get(tid, []):
                        painter.drawLine(x1, y1, x2, y2)

            for sid, required_pos in r.path_switches.items():
                for x1, y1, x2, y2 in switch_segments.get(str(sid), {}).get(required_pos, []):
                    painter.drawLine(x1, y1, x2, y2)
            for sid, required_pos in r.flank_switches.items():
                for x1, y1, x2, y2 in switch_segments.get(str(sid), {}).get(required_pos, []):
                    painter.drawLine(x1, y1, x2, y2)

    def draw_switches(self, painter):
        # 斜线连接逻辑
        color_idle = QColor(0, 191, 255)
        
        def get_active_pen(swid):
            sw = self.state_manager.switches[swid]
            color = color_idle
            if sw.is_locked:
                color = Qt.white
            elif sw.position == SwitchPosition.MOVING:
                color = Qt.yellow
            return QPen(color, 3)

        def draw_bg_line(start_p, end_p):
            painter.setPen(QPen(QColor(60, 60, 60), 1, Qt.DashLine))
            painter.drawLine(start_p, end_p)

        def draw_active_line(swid, start_p, end_p):
            painter.setPen(get_active_pen(swid))
            painter.drawLine(start_p, end_p)

        active_routes = [
            r for r in self.state_manager.routes.values()
            if r.is_active and r.stage in (RouteStage.PRELOCKED, RouteStage.OPENED, RouteStage.APPROACH_LOCKED, RouteStage.RELEASING)
        ]
        active_track_ids = set()
        for r in active_routes:
            for tid in r.path_tracks:
                active_track_ids.add(tid)

        sw1 = self.state_manager.switches["1"]
        sw3 = self.state_manager.switches["3"]
        sw5 = self.state_manager.switches["5"]
        sw4 = self.state_manager.switches["4"]
        sw2 = self.state_manager.switches["2"]

        p1_base = QPointF(self.x_sw1, self.y_iig)
        p1_straight = QPointF(self.x_sw1 + 70, self.y_iig)
        p1_div = QPointF(self.x_3g_left, self.y_3g)

        draw_bg_line(p1_base, p1_straight)
        draw_bg_line(p1_base, p1_div)

        if sw1.position == SwitchPosition.REVERSE:
            draw_active_line("1", p1_base, p1_div)
        else:
            draw_active_line("1", p1_base, p1_straight)

        p3_base = QPointF(self.x_sw3_entry, self.y_iig)
        p3_straight = QPointF(self.x_sw3_entry + 60, self.y_iig)
        p3_div = QPointF(self.x_1g_left, self.y_1g)
        draw_bg_line(p3_base, p3_straight)
        draw_bg_line(p3_base, p3_div)
        if sw3.position == SwitchPosition.REVERSE:
            draw_active_line("3", p3_base, p3_div)
        else:
            draw_active_line("3", p3_base, p3_straight)

        p5_base = QPointF(self.x_1g_left, self.y_1g)
        p5_to_1g = QPointF(p5_base.x() + 60, self.y_1g)
        p5_to_iig = p3_base
        draw_bg_line(p5_base, p5_to_1g)
        draw_bg_line(p5_base, p5_to_iig)
        if sw5.position == SwitchPosition.REVERSE:
            draw_active_line("5", p5_base, p5_to_iig)
        else:
            draw_active_line("5", p5_base, p5_to_1g)

        p4_base = QPointF(self.x_sw4, self.y_iig)
        p4_straight = QPointF(self.x_sw4 + 60, self.y_iig)
        p4_div = QPointF(self.x_3g_right, self.y_3g)
        draw_bg_line(p4_base, p4_straight)
        draw_bg_line(p4_base, p4_div)
        if sw4.position == SwitchPosition.REVERSE:
            draw_active_line("4", p4_base, p4_div)
        else:
            draw_active_line("4", p4_base, p4_straight)

        p2_base = QPointF(self.x_sw2, self.y_iig)
        p2_straight = QPointF(self.x_sw2 + 60, self.y_iig)
        p2_div = QPointF(self.x_1g_right, self.y_1g)
        draw_bg_line(p2_base, p2_straight)
        draw_bg_line(p2_base, p2_div)
        if sw2.position == SwitchPosition.REVERSE:
            draw_active_line("2", p2_base, p2_div)
        else:
            draw_active_line("2", p2_base, p2_straight)

        # 5# 道岔 (安全线/1G分岔)
        # 已由 5# 在咽喉区统一绘制

        if self.show_switch_labels:
            painter.setPen(QColor(0, 255, 0))
            painter.setFont(QFont("Consolas", 10, QFont.Bold))
            painter.drawText(QPointF(self.x_sw1 - 25, self.y_iig - 15), "1#")
            painter.drawText(QPointF(self.x_sw3_entry + 10, self.y_iig - 15), "3#")
            painter.drawText(QPointF(self.x_1g_left + 10, self.y_1g - 15), "5#")
            painter.drawText(QPointF(self.x_sw4 - 25, self.y_iig - 15), "4#")
            painter.drawText(QPointF(self.x_sw2 - 25, self.y_iig - 15), "2#")

    def draw_signals(self, painter):
        colors = {
            SignalColor.RED: Qt.red,
            SignalColor.GREEN: QColor(0, 255, 0),
            SignalColor.YELLOW: Qt.yellow,
            SignalColor.BLUE: QColor(0, 0, 255),
            SignalColor.WHITE: Qt.white,
            SignalColor.MOON_WHITE: QColor(200, 200, 255),
            SignalColor.OFF: Qt.black
        }

        def get_lamp_colors(sig):
            off = QColor(20, 20, 20)
            red = Qt.red
            green = QColor(0, 255, 0)
            yellow = Qt.yellow
            blue = QColor(0, 0, 255)
            white = Qt.white
            moon = QColor(200, 200, 255)

            if sig.id.startswith("D"):
                if sig.aspect == SignalAspect.STOP:
                    return blue, off
                if sig.aspect == SignalAspect.SHUNT_PROCEED:
                    return white, off
                return blue, off

            if sig.aspect == SignalAspect.STOP:
                return red, off
            if sig.aspect == SignalAspect.PROCEED:
                return green, off
            if sig.aspect == SignalAspect.CAUTION:
                return yellow, off
            if sig.aspect == SignalAspect.DOUBLE_CAUTION:
                return yellow, yellow
            if sig.aspect == SignalAspect.GUIDE:
                return red, moon
            return off, off

        def draw_sig_pro(x, y, sid, direction="right", is_d=False):
            sig = self.state_manager.signals[sid]
            radius = 8 if not is_d else 7
            
            # 绘制信号机架
            painter.setPen(QPen(Qt.white, 2))
            if direction == "right":
                painter.drawLine(x, y, x, y - 20)
                # 改为横向并列排列
                rect1 = QRectF(x, y - 25, radius*2, radius*2)
                rect2 = QRectF(x + radius*2 + 2, y - 25, radius*2, radius*2)
            else:
                painter.drawLine(x, y, x, y + 20)
                # 改为横向并列排列
                rect1 = QRectF(x - radius*2, y + 5, radius*2, radius*2)
                rect2 = QRectF(x - radius*4 - 2, y + 5, radius*2, radius*2)
            
            c1, c2 = get_lamp_colors(sig)
            painter.setBrush(QBrush(c1))
            painter.drawEllipse(rect1)
            painter.setBrush(QBrush(c2))
            painter.drawEllipse(rect2)

            if self.show_signal_labels:
                painter.setPen(QColor(220, 220, 220))
                painter.setFont(QFont("Consolas", 10, QFont.Bold))
                if direction == "right":
                    # 标签位置微调，避免重叠
                    label_pos = QPointF(rect2.right() + 8, rect1.center().y() + 4)
                else:
                    if sid == "D2":
                        # 特殊调整 D2：向下移动 25 (从-10到+15)，向左移动 10 (边距从-8到-18)
                        label_pos = QPointF(rect2.left() - 18 - len(sid) * 8, rect1.center().y() + 15)
                    else:
                        # 标签位置微调：对于左向信号机（S3, SII, S1等），将标签垂直向上移动，避免与灯位重叠
                        label_pos = QPointF(rect2.left() - 8 - len(sid) * 8, rect1.center().y() - 27)
                painter.drawText(label_pos, sid)
            
            # 点击区域涵盖两个灯位
            hit = rect1.united(rect2).adjusted(-6, -6, 6, 6)
            self.click_regions[sid] = (hit, "SIGNAL")

        # 进站
        draw_sig_pro(self.x_x_signal, self.y_iig, "X", "right")
        draw_sig_pro(self.x_s_signal, self.y_iig, "S", "left")
        
        # 出站（下行→右端）
        draw_sig_pro(self.x_3g_right - 20, self.y_3g, "X3", "right")
        draw_sig_pro(self.x_sw4 - 120, self.y_iig, "XII", "right")
        draw_sig_pro(self.x_1g_right - 20, self.y_1g, "X1", "right")
        
        # 出站（上行→左端）
        left_dep_x_3g = self.x_3g_left + 30
        left_dep_x_iig = self.x_sw3_entry + 30
        left_dep_x_1g = self.x_1g_left + 30
        draw_sig_pro(left_dep_x_3g, self.y_3g, "S3", "left")
        draw_sig_pro(left_dep_x_iig, self.y_iig, "SII", "left")
        draw_sig_pro(left_dep_x_1g, self.y_1g, "S1", "left")
        
        # 调车
        draw_sig_pro(self.x_d1, self.y_iig, "D1", "right", True)
        d2_x = self.x_s_signal - 110
        draw_sig_pro(d2_x, self.y_iig, "D2", "left", True)

    def draw_labels(self, painter):
        painter.setPen(Qt.white)
        painter.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        
        # 站名 - 适当下移
        painter.setFont(QFont("Microsoft YaHei", 32, QFont.Bold))
        painter.setPen(QColor(0, 255, 0))
        painter.drawText(self.rect(), Qt.AlignTop | Qt.AlignHCenter, "\n\n标 准 站")
        
        if self.show_track_labels:
            painter.setFont(QFont("Microsoft YaHei", 10))
            painter.setPen(Qt.white)
            # 调整标注位置，避免与线路重叠
            painter.drawText(self.x_start + 20, self.y_iig + 35, "JXG")
            painter.drawText(self.x_x_signal + 40, self.y_iig + 35, "IIAG")
            painter.drawText(self.x_3g_left + 80, self.y_3g - 25, "3G")
            painter.drawText(self.x_track_start + 100, self.y_iig - 25, "IIG")
            painter.drawText(self.x_1g_left + 120, self.y_1g + 35, "1G")
            painter.drawText(self.x_safety_left - 80, self.y_safety + 35, "安全线")
            painter.drawText((self.x_sw4 + self.x_s_signal) // 2 - 20, self.y_iig - 35, "IIBG")
            painter.drawText(self.x_s_signal + 30, self.y_iig + 35, "JSG")
        
        # 方向 - 微调避免重叠
        painter.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        painter.setPen(Qt.yellow)
        painter.drawText(self.x_start, self.y_iig - 60, "← 下行方向")
        painter.drawText(self.x_end - 120, self.y_iig + 60, "上行方向 →")

        # 坡度标注
        painter.setPen(QPen(QColor(180, 180, 180), 2))
        painter.setFont(QFont("Consolas", 12, QFont.Bold))
        slope_x = self.x_end - 180
        slope_y = self.y_3g - 40
        # 绘制坡度符号 (水平线 + 左侧下斜尾巴)
        painter.drawLine(int(slope_x), int(slope_y), int(slope_x + 60), int(slope_y))
        painter.drawLine(int(slope_x), int(slope_y), int(slope_x - 15), int(slope_y + 15))
        # 绘制 6‰ 文字
        painter.drawText(QRectF(slope_x, slope_y - 25, 60, 20), Qt.AlignCenter, "6‰")

    def draw_pza_button(self, painter):
        # 调整 PZA 按钮位置，避免与安全线标签重叠
        rect = QRectF(self.x_safety_left - 120, self.y_safety + 60, 60, 28)
        painter.setPen(QPen(QColor(120, 120, 120), 1))
        painter.setBrush(QBrush(QColor(30, 30, 30)))
        painter.drawRoundedRect(rect, 4, 4)
        painter.setPen(QColor(220, 220, 220))
        painter.setFont(QFont("Consolas", 11, QFont.Bold))
        painter.drawText(rect, Qt.AlignCenter, "PZA")
        self.click_regions["PZA"] = (rect.adjusted(-6, -6, 6, 6), "BUTTON")
