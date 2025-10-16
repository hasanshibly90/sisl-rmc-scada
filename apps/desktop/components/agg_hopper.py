# components/agg_hopper.py
from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPainterPath, QLinearGradient, QRadialGradient, QFont
)
from PySide6.QtWidgets import QGraphicsObject, QGraphicsItem, QGraphicsSimpleTextItem
from theme import YELLOW, STEEL_EDGE, TXT

# -------- Hopper colors --------
HOPPER_FACE   = YELLOW
HOPPER_EDGE   = QColor(42, 50, 63)
HOPPER_SHINE  = QColor(255, 255, 255, 36)

OUTLET_FACE   = QColor(212, 215, 220)
OUTLET_EDGE   = STEEL_EDGE
OUTLET_PLUG   = QColor(120, 130, 145)

BASE_FACE     = QColor(65, 72, 84)

WEIGHT_TXT    = TXT

# -------- Capsule gauge palette (matches silo/mixer) --------
GLASS_BG    = QColor(255, 255, 255, 28)
GLASS_EDGE  = QColor(200, 210, 220, 170)
FILL_TOP    = QColor(120, 245, 140, 240)
FILL_BOT    = QColor(60, 180, 95, 235)
TICK_MAJOR  = QColor(230, 238, 245, 210)
TICK_MINOR  = QColor(230, 238, 245, 120)
LABEL_COL   = QColor(225, 235, 245, 235)
PCT_COL     = QColor(245, 250, 255, 245)

# -------- Gate / flow (like mixer) --------
GATE_CLR    = QColor("#D9DEE5")
GATE_EDGE   = STEEL_EDGE
FLOW_CLR    = QColor(200, 215, 240, 220)

BAR_W       = 16
OPEN_GAP    = 42
FLOW_H      = 58

GAUGE_WIDTH_SCALE = 0.50  # 50% width (narrow capsule)

class AggHopper(QGraphicsObject):
    """
    Aggregate hopper (single HOPPER capsule gauge, weight readout, optional discharge gate).
    New (optional): set_dosing(True/False) => brief glow pulse on the hopper body.
    """
    def __init__(self, w=380, h=400, draggable=True, parent=None):
        super().__init__(parent)
        self.w = float(w)
        self.h = float(h)
        self._title = "Agg"
        self._weight_kg = 0.0
        self._capacity_kg = 1500.0
        self._level_override_pct = None
        self._gate_open = False
        self._flow_phase = 0.0

        # transient dosing pulse (frames) – when >0, we draw a glow
        self._dosing_pulse = 0

        # compatibility inputs (not rendered in single-capsule mode, but harmless if called)
        self._cement_pct = 0.0
        self._mixer_pct  = 0.0

        if draggable:
            self.setFlag(QGraphicsItem.ItemIsMovable, True)
            self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)

        self.title_item  = QGraphicsSimpleTextItem(self._title, self)
        self.weight_item = QGraphicsSimpleTextItem("WEIGHT: 0.00 kg", self)
        self.title_item.setBrush(QBrush(WEIGHT_TXT))
        self.weight_item.setBrush(QBrush(WEIGHT_TXT))

    # ---------- geometry ----------
    def boundingRect(self) -> QRectF:
        m_left, m_right = 40, 160
        m_y = 60
        return QRectF(-self.w/2 - m_left, -self.h/2 - m_y, self.w + m_left + m_right, self.h + 2*m_y)

    def _layout(self):
        top_lip_h   = self.h * 0.095
        body_top_y  = -self.h * 0.32
        body_bot_y  =  self.h * 0.12
        outlet_h    = self.h * 0.20
        outlet_w    = self.w * 0.34

        body_top_l = QPointF(-self.w * 0.48, body_top_y)
        body_top_r = QPointF( self.w * 0.48, body_top_y)
        body_bot_l = QPointF(-self.w * 0.34, body_bot_y)
        body_bot_r = QPointF( self.w * 0.34, body_bot_y)

        lip_rect    = QRectF(-self.w * 0.54, body_top_y - top_lip_h, self.w * 1.08, top_lip_h)
        outlet_rect = QRectF(-outlet_w/2, body_bot_y + 8, outlet_w, outlet_h)
        base_rect   = QRectF(-self.w * 0.46, outlet_rect.bottom() + 14, self.w * 0.92, 7)

        gx   = self.w * 0.58
        gw   = self.w * 0.28 * GAUGE_WIDTH_SCALE
        gh   = (body_top_y * -1 + body_bot_y) + self.h * 0.28
        gr   = QRectF(gx, body_top_y - self.h * 0.02, gw, gh)

        return body_top_l, body_top_r, body_bot_l, body_bot_r, lip_rect, outlet_rect, base_rect, gr

    # ---------- percent ----------
    def _hopper_frac(self) -> float:
        if self._level_override_pct is not None:
            return max(0.0, min(1.0, self._level_override_pct / 100.0))
        if self._capacity_kg <= 0:
            return 0.0
        return max(0.0, min(1.0, self._weight_kg / self._capacity_kg))

    # ---------- paint ----------
    def paint(self, p: QPainter, option, widget=None):
        del option, widget
        p.setRenderHint(QPainter.Antialiasing, True)
        tl, tr, bl, br, lip_rect, outlet_rect, base_rect, gr = self._layout()

        # title
        self.title_item.setText(self._title)
        tbr = self.title_item.boundingRect()
        self.title_item.setPos((tl.x()+tr.x())/2 - tbr.width()/2, lip_rect.top() - tbr.height() - 10)

        # body
        p.setPen(QPen(HOPPER_EDGE, 3))
        body = QPainterPath(tl); body.lineTo(tr); body.lineTo(br); body.lineTo(bl); body.closeSubpath()
        p.setBrush(QBrush(HOPPER_FACE)); p.drawPath(body)

        # dosing glow (if pulsing)
        if self._dosing_pulse > 0:
            a = max(0, min(180, self._dosing_pulse))  # alpha
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, a//2))
            p.drawPath(body)
            self._dosing_pulse -= 6  # decay

        # lip + shine
        p.setPen(QPen(HOPPER_EDGE, 3)); p.setBrush(QBrush(HOPPER_FACE))
        p.drawRoundedRect(lip_rect, 8, 8)
        p.setBrush(QBrush(HOPPER_SHINE)); p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(lip_rect.left()+10, lip_rect.top()+4, lip_rect.width()-20, lip_rect.height()*0.45), 6, 6)

        # outlet box + plug
        p.setPen(QPen(OUTLET_EDGE, 3)); p.setBrush(QBrush(OUTLET_FACE)); p.drawRoundedRect(outlet_rect, 6, 6)
        plug_r = 7
        p.setBrush(QBrush(OUTLET_PLUG)); p.setPen(QPen(OUTLET_PLUG, 1))
        p.drawEllipse(QPointF(outlet_rect.center().x(), outlet_rect.center().y()), plug_r, plug_r)

        # base tray
        p.setPen(Qt.NoPen); p.setBrush(QBrush(BASE_FACE)); p.drawRoundedRect(base_rect, 3, 3)

        # capsule gauge (HOPPER)
        self._paint_capsule(p, gr, self._hopper_frac(), title="HOPPER")

        # gate (CLOSED plate only—kept simple here)
        if False:
            pass  # (If you need the open stream on agg bins too, we can enable like the mixer)

        # weight readout
        self.weight_item.setText(f"WEIGHT: {self._weight_kg:0.2f} kg")
        wbr = self.weight_item.boundingRect()
        mid_x = (tl.x()+tr.x())/2
        self.weight_item.setPos(mid_x - wbr.width()/2, base_rect.bottom()+10)

    def _paint_capsule(self, p: QPainter, r: QRectF, frac: float, *, title: str):
        radius = r.width()/2
        # case
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

        # labels + title
        p.setPen(QPen(LABEL_COL))
        f = QFont(p.font()); f.setBold(True); f.setPointSize(8); p.setFont(f)
        p.drawText(QPointF(r.right()+6, r.top()+10), "FULL")
        p.drawText(QPointF(r.right()+6, r.bottom()-2), "EMPTY")
        if title:
            p.drawText(QPointF(r.left(), r.top()-6), title)

        # fill
        frac = max(0.0, min(1.0, frac))
        fill_h = (r.height() - 8) * frac
        if fill_h > 1:
            fill_rect = QRectF(r.left()+4, r.bottom()-4 - fill_h, r.width()-8, fill_h)
            g = QLinearGradient(fill_rect.center().x(), fill_rect.top(), fill_rect.center().x(), fill_rect.bottom())
            g.setColorAt(0.0, FILL_TOP); g.setColorAt(1.0, FILL_BOT)
            p.setBrush(QBrush(g)); p.setPen(Qt.NoPen)
            p.drawRoundedRect(fill_rect, (r.width()-8)/2, (r.width()-8)/2)

        # % text
        pct_text = f"{int(round(frac*100))}%"
        p.setPen(QPen(PCT_COL))
        f2 = QFont(p.font()); f2.setBold(True); f2.setPointSize(16); p.setFont(f2)
        brw = p.fontMetrics().horizontalAdvance(pct_text)
        brh = p.fontMetrics().ascent()
        p.drawText(QPointF(r.center().x() - brw/2, r.center().y() + brh/2), pct_text)

    # ---------- public API ----------
    def set_title(self, text: str): self._title = str(text); self.update()
    def set_weight_kg(self, kg: float): self._weight_kg = max(0.0, float(kg)); self.update()
    def get_weight_kg(self) -> float:   return self._weight_kg
    def set_capacity_kg(self, kg: float): self._capacity_kg = max(1.0, float(kg)); self.update()
    def get_capacity_kg(self) -> float:   return self._capacity_kg
    def set_level_pct(self, pct: float): self._level_override_pct = max(0.0, min(100.0, float(pct))); self.update()
    def clear_level_pct_override(self): self._level_override_pct = None; self.update()
    # Compatibility no-ops for now (kept to avoid breaking calls)
    def set_cement_pct(self, pct: float): self._cement_pct = max(0.0, min(100.0, float(pct))); self.update()
    def set_mixer_pct(self,  pct: float): self._mixer_pct  = max(0.0, min(100.0, float(pct))); self.update()

    def set_dosing(self, on: bool = True, intensity: int = 180):
        """Call briefly while a gate is dosing; draws a fading glow over ~1s."""
        self._dosing_pulse = max(self._dosing_pulse, intensity)
        self.update()

    def open_gate(self):  pass
    def close_gate(self): pass
    def is_gate_open(self) -> bool: return False

    def advance_phase(self, d: float = 2.0):
        # decay the dosing pulse if active
        if self._dosing_pulse > 0:
            self._dosing_pulse = max(0, self._dosing_pulse - 6)
            self.update()
