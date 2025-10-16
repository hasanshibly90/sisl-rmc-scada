# components/flow_connector.py — Realistic steel pipe + dynamic flow (FINAL)
from __future__ import annotations
from typing import Callable, Literal, Optional

from PySide6.QtCore import QObject, QPointF, QRectF, QTimer, QElapsedTimer, QEvent, Qt
from PySide6.QtGui import QPainterPath, QPen, QPainter, QColor, QLinearGradient
from PySide6.QtWidgets import QGraphicsObject, QGraphicsItem, QGraphicsDropShadowEffect

Shape = Literal["L", "U", "auto"]

class FlowConnectorItem(QGraphicsObject):
    def __init__(
        self,
        a_item: QGraphicsItem, a_anchor_fn: Callable[[], QPointF],
        b_item: QGraphicsItem, b_anchor_fn: Callable[[], QPointF],
        get_src: Callable[[], float], set_src: Callable[[float], None],
        get_dst: Callable[[], float], set_dst: Callable[[float], None],
        *, enabled_fn: Callable[[], bool],
        rate_kgps: float = 20.0,
        src_capacity_kg: Optional[float] = None,
        dst_capacity_kg: Optional[float] = None,
        shape: Shape = "auto",
        z: float = -1.0,
        diameter_px: int = 18,
        wall_px: int = 2,
        color_outer: QColor | str = "#8E9AA6",
        color_inner: QColor | str = "#D9DEE3",
        color_flow:  QColor | str = "#BFC6CC",
        flow_dash: list[float] | None = None,
        flow_speed: float = 1.8,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._a_item = a_item; self._b_item = b_item
        self._a_anchor = a_anchor_fn; self._b_anchor = b_anchor_fn
        self._get_src = get_src; self._set_src = set_src
        self._get_dst = get_dst; self._set_dst = set_dst
        self._enabled_fn = enabled_fn
        self._rate = float(rate_kgps)
        self._src_cap = src_capacity_kg; self._dst_cap = dst_capacity_kg
        self._shape: Shape = shape
        self._path = QPainterPath()
        self._dash_phase = 0.0
        self._pulse = 0.0
        self._enabled_blend = 0.0
        self._outer_w = max(4, int(diameter_px))
        self._wall_px = max(1, int(wall_px))
        self._inner_w = max(2, self._outer_w - 2*self._wall_px)
        self._min_inner_w = max(2, self._inner_w - 3)
        self._max_inner_w = self._inner_w
        self._flanges: list[QPointF] = []
        self._pen_outer = QPen(QColor(color_outer)); self._pen_outer.setWidth(self._outer_w)
        self._pen_outer.setJoinStyle(Qt.RoundJoin);   self._pen_outer.setCapStyle(Qt.RoundCap)
        self._pen_inner = QPen(QColor(color_inner)); self._pen_inner.setWidth(self._inner_w)
        self._pen_inner.setJoinStyle(Qt.RoundJoin);   self._pen_inner.setCapStyle(Qt.RoundCap)
        self._base_flow  = QColor(color_flow)
        self._flow_speed_base = float(flow_speed)
        self._flow_dash  = flow_dash or [16, 12]
        self.setZValue(z)
        self.setAcceptedMouseButtons(Qt.NoButton)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(16); shadow.setOffset(4, 4); shadow.setColor(QColor(0, 0, 0, 130))
        self.setGraphicsEffect(shadow)
        self._filters_installed = False
        self._anim = QTimer(self); self._anim.setInterval(40)
        self._anim.timeout.connect(self._on_anim); self._anim.start()
        self._elapsed = QElapsedTimer(); self._elapsed.start()
        self.rebuild()

    def _bore_width(self) -> int:
        lo, hi = 10.0, 80.0
        r = max(lo, min(hi, self._rate)); t = (r - lo) / (hi - lo)
        import math
        w = int(self._min_inner_w + t * (self._max_inner_w - self._min_inner_w))
        if self._enabled_fn(): w += int(1.2 * (0.5 + 0.5 * math.sin(self._pulse)))
        return max(self._min_inner_w, w)

    def _flow_color(self) -> QColor:
        lo, hi = 10.0, 80.0
        r = max(lo, min(hi, self._rate)); t = (r - lo) / (hi - lo)
        def lerp(a,b,t): return int(a + (b - a) * t)
        return QColor( lerp(154,226,t), lerp(163,230,t), lerp(169,232,t) )

    def _flow_speed(self) -> float:
        lo, hi = 10.0, 80.0
        r = max(lo, min(hi, self._rate)); t = (r - lo) / (hi - lo)
        return self._flow_speed_base * (0.4 + 0.6 * t)

    def boundingRect(self) -> QRectF:
        pad = self._outer_w * 0.75
        return self._path.boundingRect().adjusted(-pad, -pad, pad, pad)

    def paint(self, p: QPainter, opt, widget=None):
        p.setRenderHint(QPainter.Antialiasing, True)
        br = self._path.boundingRect()
        p.save()
        cs_pen = QPen(QColor(0, 0, 0, 70), self._outer_w + 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(cs_pen); p.translate(1.2, 1.6); p.drawPath(self._path)
        p.restore()
        g_outer = QLinearGradient(br.topLeft(), br.bottomRight())
        g_outer.setColorAt(0.00, QColor("#7f8a93"))
        g_outer.setColorAt(0.35, QColor("#b7c1c8"))
        g_outer.setColorAt(0.50, QColor("#e7edf2"))
        g_outer.setColorAt(0.70, QColor("#aab4bc"))
        g_outer.setColorAt(1.00, QColor("#6e7780"))
        p.setPen(QPen(g_outer, self._outer_w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)); p.drawPath(self._path)
        g_inner = QLinearGradient(br.bottomLeft(), br.topRight())
        g_inner.setColorAt(0.00, QColor("#cdd5db")); g_inner.setColorAt(1.00, QColor("#aeb7bf"))
        p.setPen(QPen(g_inner, self._inner_w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)); p.drawPath(self._path)
        flow_pen = QPen(self._flow_color(), self._bore_width(), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        flow_pen.setDashPattern(self._flow_dash)
        c = flow_pen.color(); c.setAlpha(int(80 + 175 * self._enabled_blend)); flow_pen.setColor(c)
        flow_pen.setDashOffset(self._dash_phase)
        p.setPen(flow_pen); p.drawPath(self._path)
        rings = QPen(QColor(0, 0, 0, 42), max(2, int(self._outer_w * 0.12)), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        rings.setDashPattern([1, max(120, int(self._outer_w * 7.2))]); p.setPen(rings); p.drawPath(self._path)
        cap_pen = QPen(QColor(60, 65, 72, 180), 1)
        p.setPen(cap_pen); p.setBrush(QColor("#c5ccd2")); r_cap = self._outer_w * 0.52
        try:
            p1 = self._a_anchor(); p2 = self._b_anchor(); p.drawEllipse(p1, r_cap, r_cap); p.drawEllipse(p2, r_cap, r_cap)
        except Exception:
            pass
        if self._flanges:
            for cpt in self._flanges:
                self._draw_flange(p, cpt, self._outer_w * 0.8)

    def _draw_flange(self, p: QPainter, center: QPointF, ro: float, bolts: int = 6):
        ri = ro * 0.58; p.save()
        p.setPen(QPen(QColor("#5e6871"), 1)); p.setBrush(QColor("#c5ccd2")); p.drawEllipse(center, ro, ro)
        p.setBrush(QColor("#a8b1b9")); p.drawEllipse(center, ri, ri)
        from math import cos, sin, tau
        rb = ro * 0.14; rad = (ro + ri) * 0.5
        bolt_pen = QPen(QColor("#3a3f45"), 1); p.setPen(bolt_pen); p.setBrush(QColor("#dfe4e7"))
        for i in range(bolts):
            ang = (tau / bolts) * i
            cx = center.x() + rad * cos(ang); cy = center.y() + rad * sin(ang)
            p.drawEllipse(QPointF(cx, cy), rb, rb)
        p.restore()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSceneHasChanged:
            self._try_install_filters()
        return super().itemChange(change, value)

    def sceneEventFilter(self, watched, event):
        names = (
            "GraphicsSceneMove","GraphicsSceneMousePress","GraphicsSceneMouseRelease",
            "GraphicsSceneMouseDoubleClick","GraphicsSceneHoverMove","GraphicsSceneDragMove",
            "GraphicsSceneWheel","GraphicsSceneContextMenu","GraphicsSceneHelp",
        )
        interesting = [int(getattr(QEvent,n)) for n in names if getattr(QEvent,n,None) is not None]
        if int(event.type()) in interesting: self.rebuild()
        return False

    def set_shape(self, shape: Shape):
        self._shape = shape; self.rebuild()

    def set_rate(self, kgps: float):
        self._rate = max(0.0, float(kgps))

    def _try_install_filters(self):
        if self._filters_installed: return
        sc = self.scene()
        if not sc: return
        if self._a_item.scene() is sc and self._b_item.scene() is sc:
            sc.changed.connect(self.rebuild)
            self._a_item.installSceneEventFilter(self)
            self._b_item.installSceneEventFilter(self)
            self._filters_installed = True

    def _on_anim(self):
        self._dash_phase = (self._dash_phase + self._flow_speed()) % 1000.0
        self._pulse = (self._pulse + 0.25) % 6.28318
        target = 1.0 if self._enabled_fn() else 0.0
        self._enabled_blend += (target - self._enabled_blend) * 0.15
        dt = max(0.0, self._elapsed.restart() / 1000.0)
        if self._enabled_fn():
            src = float(self._get_src()); dst = float(self._get_dst())
            move = min(self._rate * dt, max(0.0, src))
            if self._dst_cap is not None:
                free = max(0.0, self._dst_cap - dst); move = min(move, free)
            if move > 0.0: self._set_src(src - move); self._set_dst(dst + move)
        self.update()

    def rebuild(self):
        self._try_install_filters()
        try:
            p1 = self._a_anchor(); p2 = self._b_anchor()
        except Exception:
            return
        self.prepareGeometryChange()
        r = max(14.0, self._outer_w * 1.0)
        path = QPainterPath(p1)
        flanges: list[QPointF] = [p1]
        if self._shape == "U":
            drop = max(60.0, abs(p2.y() - p1.y()) * 0.5)
            c1 = QPointF(p1.x(), p1.y() + drop); c2 = QPointF(p2.x(), p1.y() + drop)
            path.lineTo(QPointF(p1.x(), p1.y() + drop - r))
            path.quadTo(QPointF(p1.x(), p1.y() + drop), QPointF(p1.x() + r, p1.y() + drop))
            path.lineTo(QPointF(p2.x() - r, p1.y() + drop))
            path.quadTo(QPointF(p2.x(), p1.y() + drop), QPointF(p2.x(), p1.y() + drop - r))
            path.lineTo(QPointOf(p2.x(), p2.y()))
            flanges += [c1, c2]
        else:
            mid_x = (p1.x() + p2.x()) / 2.0
            c1 = QPointF(mid_x, p1.y()); c2 = QPointF(mid_x, p2.y())
            path.lineTo(QPointF(mid_x - r, p1.y()))
            path.quadTo(QPointF(mid_x, p1.y()), QPointF(mid_x, p1.y() + (r if p2.y() >= p1.y() else -r)))
            path.lineTo(QPointF(mid_x, p2.y() - (r if p2.y() >= p1.y() else -r)))
            path.quadTo(QPointF(mid_x, p2.y()), QPointF(mid_x + (r if p2.x() >= mid_x else -r), p2.y()))
            path.lineTo(p2)
            flanges += [c1, c2]
        flanges.append(p2)
        self._flanges = flanges
        self._path = path
        self.update()
