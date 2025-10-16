# components/silo.py
import math
from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QPolygonF, QPainterPath, QColor,
    QLinearGradient, QRadialGradient
)
from PySide6.QtWidgets import QGraphicsObject, QGraphicsItem, QGraphicsSimpleTextItem
from theme import BODY_BLUE, BODY_BLUE_DK, STEEL_LT, STEEL_DK, STEEL_EDGE, TXT

# Capsule gauge palette
GLASS_BG    = QColor(255, 255, 255, 28)
GLASS_EDGE  = QColor(200, 210, 220, 170)
FILL_TOP    = QColor(120, 245, 140, 240)
FILL_BOT    = QColor(60, 180, 95, 235)
TICK_MAJOR  = QColor(230, 238, 245, 210)
TICK_MINOR  = QColor(230, 238, 245, 120)
LABEL_COL   = QColor(225, 235, 245, 235)
PCT_COL     = QColor(245, 250, 255, 245)

GAUGE_WIDTH_SCALE = 0.50   # ← 50% width (narrower capsule)

class Silo(QGraphicsObject):
    """
    Cement silo with straight body + cone and an external capsule gauge.
    PUBLIC API: start/stop/is_running, set_percent/get_percent, pipe_origin_scene().
    """
    def __init__(self, body_w=260, body_h=460, draggable=True, parent=None):
        super().__init__(parent)
        self._pct = 0.0
        self._running = False
        self.body_w = float(body_w); self.body_h = float(body_h)
        self.top_ellipse_h = self.body_h * 0.16
        self.cone_h  = self.body_h * 0.28
        self.legs_h  = self.body_h * 0.22
        self.total_h = self.top_ellipse_h + self.body_h + self.cone_h + self.legs_h
        self.total_w = self.body_w * 1.15

        if draggable:
            self.setFlag(QGraphicsItem.ItemIsMovable, True)
            self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)

        self.percent_item = QGraphicsSimpleTextItem("0%", self)
        self.percent_item.setBrush(TXT)

    # ---------- geometry ----------
    def boundingRect(self) -> QRectF:
        # extra room on the right for the external capsule gauge
        m_right = 140
        m = 60
        return QRectF(-self.total_w/2 - m, -self.total_h - m,
                      self.total_w + m + m_right, self.total_h + 2*m)

    def _body_rect(self) -> QRectF:
        y_legs_top = -self.legs_h
        y_cone_top = y_legs_top - self.cone_h
        y_body_top = y_cone_top - self.body_h
        return QRectF(-self.body_w/2, y_body_top, self.body_w, self.body_h)

    def _top_ellipse_rect(self) -> QRectF:
        b = self._body_rect()
        return QRectF(b.left(), b.top() - self.top_ellipse_h, b.width(), self.top_ellipse_h)

    def _cone_poly(self):
        b = self._body_rect()
        y_cone_top = b.bottom()
        y_cone_bot = y_cone_top + self.cone_h
        top_w = self.body_w * 0.70
        bot_w = self.body_w * 0.30
        cx = 0.0
        return [
            QPointF(cx - top_w/2, y_cone_top),
            QPointF(cx + top_w/2, y_cone_top),
            QPointF(cx + bot_w/2, y_cone_bot),
            QPointF(cx - bot_w/2, y_cone_bot),
        ]

    def _legs(self):
        b = self._body_rect()
        y_top  = b.bottom() + self.cone_h
        y_foot = 0.0
        span   = self.body_w * 0.58
        left_x_attach  = -span/2
        right_x_attach =  span/2
        splay  = self.body_w * 0.18
        leg_w  = self.body_w * 0.07

        def leg(xa, xf):
            dx, dy = xf - xa, y_foot - y_top
            L = math.hypot(dx, dy) or 1.0
            px, py = -dy/L, dx/L
            hw = leg_w/2
            t = QPointF(xa, y_top)
            btm = QPointF(xf, y_foot)
            return QPolygonF([
                QPointF(t.x()+px*hw, t.y()+py*hw),
                QPointF(t.x()-px*hw, t.y()-py*hw),
                QPointF(btm.x()-px*hw, btm.y()-py*hw),
                QPointF(btm.x()+px*hw, btm.y()+py*hw),
            ])

        left = leg(left_x_attach,  left_x_attach - splay)
        right= leg(right_x_attach, right_x_attach + splay)
        pw   = self.body_w * 0.18
        pads = [QRectF(left_x_attach - splay - pw/2, 0, pw, 8),
                QRectF(right_x_attach + splay - pw/2, 0, pw, 8)]
        return (left, right), pads

    # ---------- paint ----------
    def paint(self, p: QPainter, option, widget=None):
        del option, widget
        p.setRenderHint(QPainter.Antialiasing, True)

        body = self._body_rect()
        topE = self._top_ellipse_rect()
        cone = self._cone_poly()
        (legL, legR), pads = self._legs()

        p.setBrush(QBrush(BODY_BLUE)); p.setPen(QPen(BODY_BLUE_DK, 2.0))
        p.drawRect(body); p.drawEllipse(topE)

        p.setBrush(QBrush(STEEL_LT)); p.setPen(QPen(STEEL_EDGE, 2.0))
        p.drawPolygon(QPolygonF(cone))

        self._paint_fill(p, body, cone)

        p.setBrush(QBrush(STEEL_LT)); p.setPen(QPen(STEEL_EDGE, 1.6))
        p.drawPolygon(legL); p.drawPolygon(legR)
        p.setBrush(QBrush(STEEL_DK))
        for r in pads: p.drawRoundedRect(r, 2, 2)

        # small % label inside body
        self.percent_item.setText(f"{int(round(self._pct))}%")
        br = self.percent_item.boundingRect()
        self.percent_item.setPos(-br.width()/2, body.center().y() - br.height()/2)

        # external capsule gauge (50% width)
        self._paint_side_capsule_gauge(p, body)

    def _paint_fill(self, p: QPainter, body_rect: QRectF, cone_pts):
        cone_h = self.cone_h; total = cone_h + self.body_h
        level = max(0.0, min(100.0, self._pct)) / 100.0
        h_all = total * level

        p.save()
        try:
            cone_poly = QPolygonF(cone_pts)
            path = QPainterPath(); path.addPolygon(cone_poly)
            p.setClipPath(path)
            if h_all > 0:
                cone_top_y = cone_pts[0].y(); cone_bot_y = cone_pts[2].y()
                h = min(h_all, cone_h); y_fill = cone_bot_y - h
                top_w = self.body_w * 0.70; bot_w = self.body_w * 0.30
                t = (y_fill - cone_top_y)/(cone_bot_y - cone_top_y) if cone_bot_y != cone_top_y else 1.0
                curr_w = bot_w + (top_w - bot_w)*(1.0 - t)
                rect = QRectF(-curr_w/2, y_fill, curr_w, h+2)
                c = BODY_BLUE.lighter(160); c.setAlpha(160)
                p.fillRect(rect, c)
        finally:
            p.restore()

        rem = h_all - cone_h
        if rem > 0:
            p.save()
            try:
                clip = body_rect.adjusted(1,1,-1,-1)
                p.setClipRect(clip)
                y_fill = body_rect.bottom() - rem
                rect2 = QRectF(clip.left(), y_fill, clip.width(), rem+2)
                c2 = BODY_BLUE.lighter(160); c2.setAlpha(150)
                p.fillRect(rect2, c2)
            finally:
                p.restore()

    # ----- modern capsule gauge (50% width) -----
    def _paint_side_capsule_gauge(self, p: QPainter, body: QRectF):
        gx = body.right() + 30
        gy = body.top() + 4
        gw = self.body_w * 0.28 * GAUGE_WIDTH_SCALE   # ← narrower
        gh = body.height() - 8
        r = QRectF(gx, gy, gw, gh)
        radius = r.width()/2

        # casing
        p.setBrush(QBrush(GLASS_BG)); p.setPen(QPen(GLASS_EDGE, 2))
        p.drawRoundedRect(r, radius, radius)

        # minor ticks
        p.setPen(QPen(TICK_MINOR, 1))
        for i in range(1, 20):
            if i % 2 == 0:  # major tick
                continue
            y = r.top() + r.height() * (1 - i/20)
            p.drawLine(QPointF(r.left()+7, y), QPointF(r.right()-7, y))

        # major ticks
        p.setPen(QPen(TICK_MAJOR, 1))
        for i in range(0, 11):
            y = r.top() + r.height() * (1 - i/10)
            p.drawLine(QPointF(r.left()+6, y), QPointF(r.right()-6, y))

        # labels
        p.setPen(QPen(LABEL_COL))
        f = p.font(); f.setBold(True); f.setPointSize(8); p.setFont(f)
        p.drawText(QPointF(r.right()+8, r.top()+10), "FULL")
        p.drawText(QPointF(r.right()+8, r.bottom()-2), "EMPTY")

        # fill
        frac = max(0.0, min(1.0, self._pct/100.0))
        fill_h = (r.height() - 8) * frac
        if fill_h > 1:
            fill_rect = QRectF(r.left()+4, r.bottom()-4 - fill_h, r.width()-8, fill_h)
            g = QLinearGradient(fill_rect.center().x(), fill_rect.top(),
                                fill_rect.center().x(), fill_rect.bottom())
            g.setColorAt(0.0, FILL_TOP); g.setColorAt(1.0, FILL_BOT)
            p.setBrush(QBrush(g)); p.setPen(Qt.NoPen)
            p.drawRoundedRect(fill_rect, (r.width()-8)/2, (r.width()-8)/2)

            # soft meniscus glow
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

    # ---------- PUBLIC API ----------
    def start(self) -> None: self._running = True
    def stop(self) -> None:  self._running = False
    def is_running(self) -> bool: return self._running
    def set_percent(self, value: float) -> None:
        self._pct = max(0.0, min(100.0, float(value))); self.update()
    def get_percent(self) -> float: return self._pct
    def pipe_origin_scene(self):
        cone = self._cone_poly()
        y = cone[2].y()
        local = QPointF(self.body_w * 0.16, y)
        return self.mapToScene(local)
