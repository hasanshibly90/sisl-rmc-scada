# components/collector_hopper.py
from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QLinearGradient
)
from PySide6.QtWidgets import QGraphicsObject, QGraphicsItem, QGraphicsSimpleTextItem
from theme import YELLOW, STEEL_EDGE, TXT
import math

# ===== Palette (calm & readable) ===============================================
EDGE           = QColor(48, 56, 66)
FRAME          = QColor(235, 185, 45)     # clean ochre (derived from YELLOW)
FRAME_EDGE     = EDGE
POST           = QColor(145, 154, 168)    # steel posts
PAN_FACE       = YELLOW
PAN_EDGE       = EDGE
SHADOW         = QColor(0, 0, 0, 22)
GLASS          = QColor(255, 255, 255, 26)

TAG_FACE       = QColor(40, 45, 52)
TAG_TEXT       = QColor(230, 235, 245)

STREAM         = QColor(200, 215, 240, 220)  # center stream
BAR_BG         = QColor(255, 255, 255, 36)
BAR_GRAD_TOP   = QColor(110, 235, 131, 230)
BAR_GRAD_BOT   = QColor(70, 190, 100, 230)

GATE_EDGE      = STEEL_EDGE
GATE_FILL      = QColor("#D9DEE5")

# ===== Component ================================================================
class CollectingHopper(QGraphicsObject):
    """
    Minimal, clean collecting hopper with:
      - 4 per-segment amounts (Agg 1..4)
      - active aggregate name + kg in center bezel
      - Total weight + slim progress bar
      - Gate open/close with animated stream
    PUBLIC API:
      set_title(text)
      set_segment_amounts([a1..a4])  -> auto total
      set_active_segment(idx or None)
      set_active_and_amount(idx, kg)
      set_segment_labels([lbl1..lbl4])
      set_weight_kg(kg)/get_weight_kg()     # manual total override
      set_capacity_kg(kg)/get_capacity_kg()
      open_gate()/close_gate()/is_gate_open()
      advance_phase(d)
    """
    def __init__(self, w=1500, h=260, draggable=True, parent=None):
        super().__init__(parent)
        self.w, self.h = float(w), float(h)

        # model
        self._title = "COLLECTING HOPPER"
        self._seg_amounts = [0.0, 0.0, 0.0, 0.0]
        self._seg_labels  = ["Agg 1", "Agg 2", "Agg 3", "Agg 4"]
        self._active_idx  = None

        self._capacity_kg = 6000.0
        self._weight_kg   = 0.0      # total (auto-sum unless overridden)
        self._auto_total  = True
        self._pct_override = None

        self._gate_open = False
        self._phase     = 0.0

        if draggable:
            self.setFlag(QGraphicsItem.ItemIsMovable, True)
            self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)

        # header + total labels
        self.title_item = QGraphicsSimpleTextItem(self._title, self)
        tf = self.title_item.font(); tf.setBold(True); tf.setPointSize(12)
        self.title_item.setFont(tf); self.title_item.setBrush(QBrush(TXT))

        self.total_item = QGraphicsSimpleTextItem("WEIGHT: 0.00 kg", self)
        tlf = self.total_item.font(); tlf.setPointSize(11)
        self.total_item.setFont(tlf); self.total_item.setBrush(QBrush(TXT))

        self.pct_item = QGraphicsSimpleTextItem("0%", self)
        pf = self.pct_item.font(); pf.setBold(True); pf.setPointSize(13)
        self.pct_item.setFont(pf); self.pct_item.setBrush(QBrush(TXT))

    # ---------- geometry ----------
    def boundingRect(self) -> QRectF:
        m = 70
        return QRectF(-self.w/2 - m, -self.h/2 - m, self.w + 2*m, self.h + 2*m)

    def _geom(self):
        top_y  = -self.h*0.38
        pan_y  = -self.h*0.12
        pan_h  =  self.h*0.40

        top_beam = QRectF(-self.w/2, top_y, self.w, 26)
        left_post  = QRectF(top_beam.left(),  top_y+10, 20, self.h*0.65)
        right_post = QRectF(top_beam.right()-20, top_y+10, 20, self.h*0.65)

        pan = QRectF(-self.w*0.48, pan_y, self.w*0.96, pan_h)
        gate = QRectF(-120, pan_y + pan_h - 8, 240, 18)

        return top_beam, left_post, right_post, pan, gate

    def _segments(self, pan: QRectF):
        seg_w = pan.width()/4.0
        segs, tags = [], []
        for i in range(4):
            left = pan.left() + seg_w*i
            rect = QRectF(left, pan.top(), seg_w, pan.height())
            segs.append(rect)
            # small tag above mid-height of pan
            tag = QRectF(rect.center().x()-56, pan.top() + pan.height()*0.18 - 14, 112, 28)
            tags.append(tag)
        return segs, tags

    # ---------- helpers ----------
    def _total_frac(self):
        if self._pct_override is not None:
            return max(0.0, min(1.0, self._pct_override/100.0))
        cap = max(1.0, self._capacity_kg)
        return max(0.0, min(1.0, self._weight_kg / cap))

    # ---------- painting ----------
    def paint(self, p: QPainter, option, widget=None):
        del option, widget
        p.setRenderHint(QPainter.Antialiasing, True)

        top_beam, lpost, rpost, pan, gate = self._geom()

        # title
        self.title_item.setText(self._title)
        tbr = self.title_item.boundingRect()
        self.title_item.setPos(-tbr.width()/2, top_beam.top()-tbr.height()-8)

        # top beam + posts
        p.setPen(QPen(FRAME_EDGE, 3)); p.setBrush(QBrush(FRAME))
        p.drawRoundedRect(top_beam, 6, 6)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(SHADOW))
        p.drawRoundedRect(top_beam.adjusted(4,4,-4,-4), 6, 6)

        p.setPen(QPen(EDGE, 2)); p.setBrush(QBrush(POST))
        p.drawRoundedRect(lpost, 4, 4); p.drawRoundedRect(rpost, 4, 4)

        # pan
        p.setPen(QPen(PAN_EDGE, 3)); p.setBrush(QBrush(PAN_FACE))
        p.drawRoundedRect(pan, 8, 8)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(SHADOW))
        p.drawRoundedRect(pan.adjusted(6,6,-6,-6), 8, 8)

        # segments & tags
        segs, tags = self._segments(pan)
        for i, tag in enumerate(tags):
            p.setBrush(QBrush(TAG_FACE)); p.setPen(QPen(EDGE, 2))
            p.drawRoundedRect(tag, 8, 8)
            lbl = self._seg_labels[i] if i < len(self._seg_labels) else f"Agg {i+1}"
            val = self._seg_amounts[i] if i < len(self._seg_amounts) else 0.0
            text = f"{lbl}: {val:,.0f} kg"
            p.setPen(QPen(TAG_TEXT))
            f = QFont(); f.setPointSize(9); f.setBold(True); p.setFont(f)
            tw = p.fontMetrics().horizontalAdvance(text)
            p.drawText(QPointF(tag.center().x()-tw/2, tag.center().y()+3), text)

        # center bezel: show active aggregate
        bezel = QRectF(-240/2, -70/2, 240, 70)
        p.setPen(QPen(EDGE, 3)); p.setBrush(QBrush(TAG_FACE))
        p.drawRoundedRect(bezel, 10, 10)
        p.setPen(QPen(QColor(230,235,245), 2)); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(bezel.adjusted(8,8,-8,-8), 8, 8)

        p.setPen(QPen(TAG_TEXT))
        f = QFont(); f.setBold(True); f.setPointSize(11); p.setFont(f)
        if self._active_idx is not None and 0 <= self._active_idx < 4:
            lbl = self._seg_labels[self._active_idx]
            val = self._seg_amounts[self._active_idx]
            line1 = f"{lbl} DISCHARGING"
            line2 = f"{val:,.0f} kg"
        else:
            line1, line2 = "COLLECTING HOPPER", ""
        tw1 = p.fontMetrics().horizontalAdvance(line1)
        p.drawText(QPointF(-tw1/2, bezel.center().y()-6), line1)
        if line2:
            f2 = QFont(f); f2.setPointSize(14); f2.setBold(True); p.setFont(f2)
            tw2 = p.fontMetrics().horizontalAdvance(line2)
            p.drawText(QPointF(-tw2/2, bezel.center().y()+18), line2)

        # total (auto from segs if auto mode)
        if self._auto_total:
            self._weight_kg = sum(self._seg_amounts)
        frac = self._total_frac()

        self.total_item.setText(f"WEIGHT: {self._weight_kg:0.2f} kg")
        tbr = self.total_item.boundingRect()
        self.total_item.setPos(-tbr.width()/2, rpost.bottom()+6)

        # slim progress bar
        bar = QRectF(-self.w*0.40, rpost.bottom()+26, self.w*0.80, 10)
        p.setPen(QPen(EDGE, 1)); p.setBrush(QBrush(BAR_BG))
        p.drawRoundedRect(bar, 5, 5)
        fill = QRectF(bar.left()+2, bar.top()+2, (bar.width()-4)*frac, bar.height()-4)
        if fill.width() > 0:
            g = QLinearGradient(fill.left(), fill.top(), fill.left(), fill.bottom())
            g.setColorAt(0.0, BAR_GRAD_TOP); g.setColorAt(1.0, BAR_GRAD_BOT)
            p.setPen(Qt.NoPen); p.setBrush(QBrush(g)); p.drawRoundedRect(fill, 4, 4)

        self.pct_item.setText(f"{int(round(frac*100))}%")
        pbr = self.pct_item.boundingRect()
        self.pct_item.setPos(bar.center().x()-pbr.width()/2, bar.top() - pbr.height() - 4)

        # gate
        p.setPen(QPen(GATE_EDGE, 2))
        if not self._gate_open:
            p.setBrush(QBrush(GATE_FILL)); p.drawRoundedRect(gate, 4, 4)
        else:
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(gate.left(), gate.top()-6, gate.width(), gate.height()), 4, 4)
            self._paint_stream(p, QPointF(0, gate.center().y()))

    def _paint_stream(self, p: QPainter, start: QPointF):
        p.setPen(Qt.NoPen); p.setBrush(QBrush(STREAM))
        h = 86
        wobble = 6.5
        xoff = math.sin(self._phase) * wobble
        p.drawRoundedRect(QRectF(start.x()-12 + xoff*0.12, start.y()+6, 24, h), 8, 8)
        for i in range(3):
            t = (self._phase*0.65 + i*0.85) % 1.0
            dy = t * h
            dx = xoff * (0.25 + 0.25*t)
            r = 4 + 2*math.sin(self._phase + i)
            p.drawEllipse(QPointF(start.x()+dx, start.y()+12+dy), r, r)

    # ---------- API ----------
    def set_title(self, text: str):
        self._title = str(text); self.update()

    def set_segment_amounts(self, amounts):
        if not amounts: return
        a = [float(x) for x in amounts[:4]]
        while len(a) < 4: a.append(0.0)
        self._seg_amounts = a
        self._auto_total = True
        self.update()

    def set_segment_labels(self, labels):
        if not labels: return
        lst = [str(x) for x in labels[:4]]
        while len(lst) < 4: lst.append(f"Agg {len(lst)+1}")
        self._seg_labels = lst; self.update()

    def set_active_segment(self, idx):
        if idx is None:
            self._active_idx = None
        else:
            i = int(idx)
            self._active_idx = i if 0 <= i < 4 else None
        self.update()

    def set_active_and_amount(self, idx, kg):
        i = int(idx)
        if 0 <= i < 4:
            if i >= len(self._seg_amounts):
                self._seg_amounts += [0.0]*(i-len(self._seg_amounts)+1)
            self._seg_amounts[i] = max(0.0, float(kg))
            self._active_idx = i
            self._auto_total = True
            self.update()

    def set_weight_kg(self, kg: float):
        """Manual total override (disables auto-sum until next set_segment_amounts)."""
        self._weight_kg = max(0.0, float(kg))
        self._auto_total = False
        self.update()

    def get_weight_kg(self) -> float:
        return self._weight_kg

    def set_capacity_kg(self, kg: float):
        self._capacity_kg = max(1.0, float(kg)); self.update()

    def get_capacity_kg(self) -> float:
        return self._capacity_kg

    def set_level_pct(self, pct: float):
        self._pct_override = max(0.0, min(100.0, float(pct))); self.update()

    def clear_level_pct_override(self):
        self._pct_override = None; self.update()

    def open_gate(self):  self._gate_open = True;  self.update()
    def close_gate(self): self._gate_open = False; self.update()
    def is_gate_open(self) -> bool: return self._gate_open

    def advance_phase(self, d: float = 2.0):
        if self._gate_open:
            self._phase = (self._phase + d/60.0) % (2*math.pi)
            self.update()
