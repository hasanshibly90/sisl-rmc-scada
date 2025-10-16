# components/mixer.py
import math
from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QPolygonF, QColor, QPainterPath,
    QLinearGradient, QRadialGradient
)
from PySide6.QtWidgets import QGraphicsObject, QGraphicsItem, QGraphicsSimpleTextItem
from theme import (
    YELLOW, YELLOW_DK, OK_GREEN,
    BLUE_MOTOR, BLUE_MOTOR_DK,
    STEEL_LT, STEEL_DK, STEEL_EDGE, TXT
)

# Capsule gauge palette (shared with silo/hopper)
GLASS_BG    = QColor(255, 255, 255, 28)
GLASS_EDGE  = QColor(200, 210, 220, 170)
FILL_TOP    = QColor(120, 245, 140, 240)
FILL_BOT    = QColor(60, 180, 95, 235)
TICK_MAJOR  = QColor(230, 238, 245, 210)
TICK_MINOR  = QColor(230, 238, 245, 120)
LABEL_COL   = QColor(225, 235, 245, 235)
PCT_COL     = QColor(245, 250, 255, 245)

# Discharge visuals
BAR_CLR     = QColor("#D9DEE5")
BAR_EDGE    = STEEL_EDGE
FLOW_CLR    = QColor(200, 215, 240, 220)

BAR_W       = 18
OPEN_GAP    = 46
FLOW_H      = 64

# Side capsule width scaling (50% narrower, per your request)
GAUGE_WIDTH_SCALE = 0.50

class Mixer(QGraphicsObject):
    """
    Mixer with:
      - twin paddles (viewport)
      - side capsule gauge (only one gauge shown; center ring removed)
      - discharge gate: CLOSED plate, OPEN “||” with falling stream
    API (unchanged):
      start/stop/is_running, advance_phase(d),
      set_charge_progress(pct), get_charge_progress(),
      open_gate/close_gate/is_gate_open
    """
    def __init__(self, w=560, h=340, draggable=True, parent=None):
        super().__init__(parent)
        self.w = float(w); self.h = float(h)
        self._running = False
        self._phase = 0.0
        self._flow_phase = 0.0
        self._charge_progress = 0.0
        self._gate_open = False

        if draggable:
            self.setFlag(QGraphicsItem.ItemIsMovable, True)
            self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)

        # badge; (we no longer draw center % text)
        self.badge = QGraphicsSimpleTextItem("JS2000", self)
        self.badge.setBrush(QBrush(TXT))

    # ---------- geometry ----------
    def boundingRect(self) -> QRectF:
        m = 140
        return QRectF(-self.w/2 - m, -self.h/2 - m, self.w + 2*m, self.h + 2*m)

    def _body_rect(self) -> QRectF:
        # main mixer housing rect (used for viewport and side gauge position)
        return QRectF(-230, -92, 460, 184)

    def inlet_scene(self) -> QPointF:
        r = self._body_rect()
        return self.mapToScene(QPointF(r.left() - 22, 0))

    # ---------- paint ----------
    def paint(self, p: QPainter, option, widget=None):
        del option, widget
        p.setRenderHint(QPainter.Antialiasing, True)

        self._paint_frame(p)
        self._paint_body(p)
        self._paint_inlet(p)
        self._paint_motor_train(p)

        # paddles viewport (arrows spin when running)
        self._paint_viewport(p)

        # discharge zone
        self._paint_discharge_zone(p)

        # SIDE CAPSULE GAUGE (only one gauge now; center ring removed)
        self._paint_side_gauge(p)

        # top details & badge
        self._paint_top_details(p)
        self._paint_lid_arrows(p)
        self._paint_badge(p)

    # ---------- frame/body/inlet/motor ----------
    def _paint_frame(self, p: QPainter):
        base_h = 18; leg_w = 18
        base_left  = QRectF(-230,  94, 150, base_h)
        base_right = QRectF(  80,  94, 150, base_h)
        leg_left   = QRectF(-175, -20, leg_w, 120)
        leg_right  = QRectF( 157, -20, leg_w, 120)
        cross      = QRectF(-150, 42, 300, 12)
        p.setBrush(QBrush(STEEL_LT)); p.setPen(QPen(STEEL_EDGE, 2))
        for r in (base_left, base_right, leg_left, leg_right, cross):
            p.drawRoundedRect(r, 6, 6)
        p.setBrush(QBrush(STEEL_DK)); p.setPen(QPen(STEEL_EDGE, 1.5))
        for cx in (base_left.center().x(), base_right.center().x()):
            p.drawRoundedRect(QRectF(cx-23, 112, 46, 8), 2, 2)

    def _paint_body(self, p: QPainter):
        body = self._body_rect(); bevel = 42
        # soft background shadow
        sh = QPainterPath(); sh.addRoundedRect(body.adjusted(5,5,5,5), 12, 12)
        p.fillPath(sh, QColor(0,0,0,20))
        # beveled housing polygon
        poly = [
            QPointF(body.left()+bevel, body.top()),
            QPointF(body.right()-bevel, body.top()),
            QPointF(body.right(), body.top()+bevel),
            QPointF(body.right(), body.bottom()-bevel),
            QPointF(body.right()-bevel, body.bottom()),
            QPointF(body.left()+bevel, body.bottom()),
            QPointF(body.left(), body.bottom()-bevel),
            QPointF(body.left(), body.top()+bevel),
        ]
        p.setBrush(QBrush(YELLOW)); p.setPen(QPen(YELLOW_DK, 2.6))
        p.drawPolygon(QPolygonF(poly))
        # seams
        p.setPen(QPen(QColor(0,0,0,40), 1))
        p.drawLine(QPointF(body.center().x(), body.top()+6), QPointF(body.center().x(), body.bottom()-6))
        p.drawLine(QPointF(body.left()+body.width()*0.33, body.top()+8), QPointF(body.left()+body.width()*0.33, body.bottom()-8))
        p.drawLine(QPointF(body.left()+body.width()*0.66, body.top()+8), QPointF(body.left()+body.width()*0.66, body.bottom()-8))

    def _paint_inlet(self, p: QPainter):
        b = self._body_rect()
        inlet = QRectF(b.left() - 22, -12, 22, 24)
        p.setBrush(QBrush(STEEL_DK)); p.setPen(QPen(STEEL_EDGE, 2)); p.drawRect(inlet)

    def _paint_motor_train(self, p: QPainter):
        motor = QRectF(212, -44, 116, 88)
        p.setBrush(QBrush(BLUE_MOTOR)); p.setPen(QPen(BLUE_MOTOR_DK, 2))
        p.drawRoundedRect(motor, 12, 12)
        p.setPen(QPen(BLUE_MOTOR_DK, 3))
        for i in range(7):
            x = motor.left() + 18 + i*14
            p.drawLine(QPointF(x, motor.top()+10), QPointF(x, motor.bottom()-10))
        reducer = QRectF(168, -34, 48, 68)
        p.setBrush(QBrush(STEEL_LT)); p.setPen(QPen(STEEL_EDGE, 2)); p.drawRoundedRect(reducer, 8, 8)
        p.setBrush(QBrush(STEEL_DK)); p.setPen(QPen(STEEL_EDGE, 2)); p.drawEllipse(QPointF(160, 0), 10, 10)

    # ---------- discharge ----------
    def _discharge_geometry(self):
        b = self._body_rect()
        top_l  = QPointF(b.left()+48,  b.bottom()-4)
        top_r  = QPointF(b.right()-48, b.bottom()-4)
        bot_r  = QPointF(b.right()-66, b.bottom()+34)
        bot_l  = QPointF(b.left()+66,  b.bottom()+34)
        hopper = QPainterPath(top_l); hopper.lineTo(top_r); hopper.lineTo(bot_r); hopper.lineTo(bot_l); hopper.closeSubpath()
        outlet = QRectF((bot_l.x()+bot_r.x())/2 - 42, bot_l.y()+8, 84, 24)
        return hopper, outlet

    def _paint_discharge_zone(self, p: QPainter):
        hopper, outlet = self._discharge_geometry()
        p.setPen(QPen(YELLOW_DK, 2))
        p.setBrush(QBrush(QColor(220,220,220,140))); p.drawPath(hopper)
        p.setBrush(QBrush(QColor(210,210,210,150))); p.drawRoundedRect(outlet, 4, 4)

        # gate
        p.setBrush(QBrush(BAR_CLR)); p.setPen(QPen(BAR_EDGE, 2.2))
        if not self._gate_open:
            plate_h = BAR_W + 4
            plate_w = outlet.width() + 32
            plate_y = outlet.bottom() + 2
            plate_x = outlet.center().x() - plate_w/2
            p.drawRoundedRect(QRectF(plate_x, plate_y, plate_w, plate_h), 5, 5)
            # small hinge dots
            cap_r = 4.5
            p.setBrush(QBrush(QColor(90,100,115))); p.setPen(QPen(BAR_EDGE, 1.2))
            p.drawEllipse(QPointF(plate_x + 6,  plate_y + plate_h/2), cap_r, cap_r)
            p.drawEllipse(QPointF(plate_x + plate_w - 6, plate_y + plate_h/2), cap_r, cap_r)
        else:
            left_x  = outlet.center().x() - OPEN_GAP/2
            right_x = outlet.center().x() + OPEN_GAP/2
            top_y   = outlet.top() - 2
            bar_h   = 56
            p.drawRoundedRect(QRectF(left_x - BAR_W/2,  top_y, BAR_W, bar_h), 5, 5)
            p.drawRoundedRect(QRectF(right_x - BAR_W/2, top_y, BAR_W, bar_h), 5, 5)
            self._paint_flow(p, outlet)

    def _paint_flow(self, p: QPainter, outlet: QRectF):
        cx = outlet.center().x()
        top_y = outlet.bottom()
        h = FLOW_H
        wobble = math.sin(self._flow_phase) * 6.5
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(FLOW_CLR))
        p.drawRoundedRect(QRectF(cx - 14 + wobble*0.12, top_y + 2, 28, h), 8, 8)
        for i in range(3):
            t = (self._flow_phase*0.7 + i*0.85) % 1.0
            dy = t * h
            dx = wobble * (0.25 + 0.25*t)
            r = 5 + 3*math.sin(self._flow_phase + i)
            p.drawEllipse(QPointF(cx + dx, top_y + dy + 10), r, r)

    # ---------- paddles viewport ----------
    def _paint_viewport(self, p: QPainter) -> QRectF:
        b = self._body_rect()
        vp = QRectF(b.left()+28, b.top()+b.height()*0.28, b.width()-56, b.height()*0.46)
        p.setBrush(QBrush(GLASS_BG)); p.setPen(QPen(GLASS_EDGE, 2.2)); p.drawRoundedRect(vp, 10, 10)
        p.fillRect(QRectF(vp.left()+8, vp.top()+6, vp.width()-16, vp.height()*0.22), QColor(255,255,255,70))
        p.save(); p.setClipRect(vp.adjusted(3,3,-3,-3))
        cy = vp.center().y()
        left_cx  = vp.left() + vp.width()*0.33
        right_cx = vp.left() + vp.width()*0.67
        self._draw_shaft(p, QPointF(left_cx,  cy), vp.height()*0.40,  self._phase, QColor(60,70,85))
        self._draw_shaft(p, QPointF(right_cx, cy), vp.height()*0.40, -self._phase, QColor(60,70,85))
        p.restore()
        p.setPen(QPen(QColor(255,255,255,120), 1)); p.drawRoundedRect(vp.adjusted(2.5,2.5,-2.5,-2.5), 9, 9)
        return vp

    def _draw_shaft(self, p: QPainter, center: QPointF, span: float, phase_deg: float, metal: QColor):
        p.setBrush(QBrush(metal)); p.setPen(QPen(QColor(40,45,55), 1.6)); p.drawEllipse(center, 8, 8)
        blade_w = 10; blade_L = span * 0.42
        for k in range(4):
            ang = phase_deg + k*90.0; rad = math.radians(ang)
            dx = math.sin(rad) * (blade_w/2); dy = math.cos(rad) * (blade_w/2)
            tipx = center.x() + math.cos(rad) * (-blade_L); tipy = center.y() + math.sin(rad) * (-blade_L)
            base1 = QPointF(center.x()+dx, center.y()-dy); base2 = QPointF(center.x()-dx, center.y()+dy)
            tip1  = QPointF(tipx+dx, tipy-dy); tip2  = QPointF(tipx-dx, tipy+dy)
            p.setBrush(QBrush(metal)); p.setPen(QPen(QColor(30,32,38), 1.2))
            p.drawPolygon(QPolygonF([base1, base2, tip2, tip1]))

    # ---------- side capsule gauge (ONLY gauge shown) ----------
    def _paint_side_gauge(self, p: QPainter):
        body = self._body_rect()
        gx = body.right() + 30
        gy = body.top() + 4
        gw = body.width() * 0.28 * GAUGE_WIDTH_SCALE
        gh = body.height() - 8
        r = QRectF(gx, gy, gw, gh)
        radius = r.width()/2

        # casing
        p.setBrush(QBrush(GLASS_BG)); p.setPen(QPen(GLASS_EDGE, 2))
        p.drawRoundedRect(r, radius, radius)

        # ticks
        p.setPen(QPen(TICK_MINOR, 1))
        for i in range(1, 20):
            if i % 2 == 0: continue
            y = r.top() + r.height() * (1 - i/20)
            p.drawLine(QPointF(r.left()+7, y), QPointF(r.right()-7, y))
        p.setPen(QPen(TICK_MAJOR, 1))
        for i in range(0, 11):
            y = r.top() + r.height() * (1 - i/10)
            p.drawLine(QPointF(r.left()+6, y), QPointF(r.right()-6, y))

        # labels
        p.setPen(QPen(LABEL_COL))
        f = p.font(); f.setBold(True); f.setPointSize(8); p.setFont(f)
        p.drawText(QPointF(r.right()+8, r.top()+10), "FULL")
        p.drawText(QPointF(r.right()+8, r.bottom()-2), "EMPTY")

        # fill from charge progress
        frac = max(0.0, min(1.0, self._charge_progress/100.0))
        fill_h = (r.height() - 8) * frac
        if fill_h > 1:
            fill_rect = QRectF(r.left()+4, r.bottom()-4 - fill_h, r.width()-8, fill_h)
            g = QLinearGradient(fill_rect.center().x(), fill_rect.top(),
                                fill_rect.center().x(), fill_rect.bottom())
            g.setColorAt(0.0, FILL_TOP); g.setColorAt(1.0, FILL_BOT)
            p.setBrush(QBrush(g)); p.setPen(Qt.NoPen)
            p.drawRoundedRect(fill_rect, (r.width()-8)/2, (r.width()-8)/2)

            # meniscus glow
            glow = QRadialGradient(fill_rect.center().x(), fill_rect.top()+10, r.width())
            glow.setColorAt(0.0, QColor(255,255,255,90))
            glow.setColorAt(1.0, QColor(255,255,255,0))
            p.setBrush(QBrush(glow))
            p.drawEllipse(QPointF(fill_rect.center().x(), fill_rect.top()+10), r.width()*0.45, r.width()*0.18)

        # big % inside capsule
        pct_text = f"{int(round(frac*100))}%"
        p.setPen(QPen(PCT_COL))
        ff = p.font(); ff.setBold(True); ff.setPointSize(16); p.setFont(ff)
        brw = p.fontMetrics().horizontalAdvance(pct_text)
        brh = p.fontMetrics().ascent()
        p.drawText(QPointF(r.center().x() - brw/2, r.center().y() + brh/2), pct_text)

    # ---------- top details & badge ----------
    def _paint_top_details(self, p: QPainter):
        hatch = QRectF(-52, -128, 104, 36)
        p.setBrush(QBrush(STEEL_LT)); p.setPen(QPen(STEEL_EDGE, 2)); p.drawRoundedRect(hatch, 8, 8)
        p.setPen(QPen(STEEL_EDGE, 2)); p.drawLine(QPointF(hatch.left()+10, hatch.top()+10), QPointF(hatch.left()+30, hatch.top()+10))
        p.setBrush(QBrush(STEEL_DK)); p.setPen(QPen(STEEL_EDGE, 1))
        for dx in (16,32,64,80): p.drawEllipse(QPointF(hatch.left()+dx, hatch.bottom()-8), 2.5, 2.5)

    def _paint_lid_arrows(self, p: QPainter):
        if not self._running: return
        center = QPointF(0, -92); radius = 78
        p.save(); p.translate(center); p.rotate(self._phase)
        p.setPen(QPen(OK_GREEN, 6)); p.setBrush(QBrush(OK_GREEN))
        for i in range(3):
            p.save(); p.rotate(i*120)
            rect = QRectF(-radius, -radius, 2*radius, 2*radius)
            p.setBrush(Qt.NoBrush); p.drawArc(rect, 50*16, 210*16)
            p.restore()
        p.restore()

    def _paint_badge(self, p: QPainter):
        b = self._body_rect()
        badge_r = QRectF(-70, -32, 140, 64)
        p.setBrush(QBrush(QColor(30,30,30,190))); p.setPen(Qt.NoPen)
        p.drawRoundedRect(badge_r, 12, 12)
        self.badge.setPos(badge_r.left()+20, badge_r.top()+12)

    # ---------- API ----------
    def start(self) -> None: self._running = True; self.update()
    def stop(self) -> None:  self._running = False; self.update()
    def is_running(self) -> bool: return self._running
    def advance_phase(self, d: float = 3.0) -> None:
        if self._running or self._gate_open:
            self._phase = (self._phase + d) % 360.0
            self._flow_phase = (self._flow_phase + d/60.0) % (2*math.pi)
            self.update()
    def set_charge_progress(self, pct: float) -> None:
        self._charge_progress = max(0.0, min(100.0, float(pct))); self.update()
    def get_charge_progress(self) -> float:
        return self._charge_progress
    def open_gate(self) -> None:
        if not self._gate_open:
            self._gate_open = True; self.update()
    def close_gate(self) -> None:
        if self._gate_open:
            self._gate_open = False; self.update()
    def is_gate_open(self) -> bool:
        return self._gate_open
