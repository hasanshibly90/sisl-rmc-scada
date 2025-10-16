from __future__ import annotations
from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import QPainter, QPixmap, QTransform
from PySide6.QtWidgets import QGraphicsObject, QGraphicsItem

class PixmapItem(QGraphicsObject):
    def __init__(self, img_path: str, *, scale: float = 1.0, draggable: bool = True, parent=None):
        super().__init__(parent)
        self.pix = QPixmap(img_path)
        self.scale = float(scale)
        if draggable:
            self.setFlag(QGraphicsItem.ItemIsMovable, True)
            self.setFlag(QGraphicsItem.ItemIsSelectable, True)
            self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self._w = self.pix.width() * self.scale
        self._h = self.pix.height() * self.scale

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._w, self._h)

    def paint(self, p: QPainter, opt, widget=None):
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        if self.scale != 1.0:
            t = QTransform(); t.scale(self.scale, self.scale)
            p.setWorldTransform(p.worldTransform() * t)
        p.drawPixmap(0, 0, self.pix)

    def anchor_point(self, where: str) -> QPointF:
        m = {
            "center": QPointF(self._w/2, self._h/2),
            "top":    QPointF(self._w/2, 0),
            "bottom": QPointF(self._w/2, self._h),
            "left":   QPointF(0, self._h/2),
            "right":  QPointF(self._w, self._h/2),
        }
        return self.mapToScene(m.get(where, m["center"]))

class PipeStrip(PixmapItem):
    def outlet_scene(self) -> QPointF: return self.anchor_point("right")
    def inlet_scene(self)  -> QPointF: return self.anchor_point("left")

class ScrewMotor(PixmapItem):
    def __init__(self, img_path: str, accel_rps2: float = 4.0, max_rps: float = 20.0, **kw):
        super().__init__(img_path, **kw)
        self._rps = 0.0
        self._target_rps = 0.0
        self._accel = float(accel_rps2)
        self._max = float(max_rps)
        self._overload = False
        self.setToolTip("Screw Motor\nRPM: 0.0\nState: STOP")

    def start(self, rps=None): self._target_rps = float(self._max if rps is None else max(0.0, min(self._max, rps)))
    def stop(self): self._target_rps = 0.0
    def is_running(self) -> bool: return self._rps > 0.1 and not self._overload
    def rpm(self) -> float: return self._rps * 60.0
    def set_overload(self, flag: bool):
        self._overload = bool(flag)
        if flag: self._target_rps = 0.0

    def tick(self, dt: float = 0.03):
        if self._overload:
            self._rps = max(0.0, self._rps - self._accel * dt * 2)
        else:
            if self._rps < self._target_rps:
                self._rps = min(self._target_rps, self._rps + self._accel * dt)
            else:
                self._rps = max(self._target_rps, self._rps - self._accel * dt)
        state = "OVERLOAD" if self._overload else ("RUN" if self.is_running() else "STOP")
        self.setToolTip(f"Screw Motor\nRPM: {self.rpm():.1f}\nState: {state}")
