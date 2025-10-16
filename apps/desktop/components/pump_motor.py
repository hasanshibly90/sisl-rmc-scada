from __future__ import annotations
from PySide6.QtCore import QRectF, QPointF, QTimer, Qt
from PySide6.QtGui import QPainter, QPen, QBrush, QColor
from PySide6.QtWidgets import QGraphicsObject, QGraphicsItem

class PumpMotor(QGraphicsObject):
    def __init__(self, *, title: str = "PUMP", color: str = "#4CC3FF",
                 body_w: int = 80, body_h: int = 54, draggable: bool = True, parent=None):
        super().__init__(parent)
        self._title = title; self._color = QColor(color)
        self._w, self._h = float(body_w), float(body_h)
        self._rpm = 0.0; self._rpm_target = 0.0; self._accel = 240.0
        if draggable:
            self.setFlag(QGraphicsItem.ItemIsMovable, True)
            self.setFlag(QGraphicsItem.ItemIsSelectable, True)
            self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self._timer = QTimer(self); self._timer.setInterval(30); self._timer.timeout.connect(self._tick); self._timer.start()

    def start(self, rpm: float | None = None): self._rpm_target = float(900.0 if rpm is None else max(0.0, rpm))
    def stop(self): self._rpm_target = 0.0
    def is_running(self) -> bool: return self._rpm > 30.0
    def rpm(self) -> float: return self._rpm
    def outlet_scene(self) -> QPointF: return self.mapToScene(QPointF(self._w, self._h * 0.5))
    def inlet_scene(self) -> QPointF:  return self.mapToScene(QPointF(0.0, self._h * 0.5))

    def boundingRect(self) -> QRectF:
        pad = 6; return QRectF(-pad, -pad, self._w + pad*2, self._h + pad*2)

    def paint(self, p: QPainter, opt, widget=None):
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(QPen(QColor("#1e2730"), 2)); p.setBrush(QBrush(QColor("#2b3440")))
        p.drawRoundedRect(0, 0, self._w, self._h, 10, 10)
        can_r = self._h * 0.42; can_cx = self._h * 0.42; can_cy = self._h * 0.5
        p.setPen(QPen(QColor("#0f1115"), 1)); p.setBrush(QBrush(QColor("#566274")))
        p.drawEllipse(can_cx - can_r, can_cy - can_r, can_r*2, can_r*2)
        angle = (self._rpm % 360.0)
        p.save(); p.translate(can_cx, can_cy); p.rotate(angle); p.setPen(QPen(QColor("#e6edf5"), 2))
        p.drawLine(0,0,can_r*0.85,0); p.rotate(120); p.drawLine(0,0,can_r*0.7,0); p.rotate(120); p.drawLine(0,0,can_r*0.55,0); p.restore()
        stub_w = self._w * 0.18; p.setPen(QPen(QColor("#2f8fdc"), 3))
        p.drawLine(self._w - 2, self._h*0.5, self._w + stub_w, self._h*0.5)
        p.drawLine(0 - stub_w, self._h*0.5, 2, self._h*0.5)
        p.setPen(QPen(QColor("#c7d2de"))); p.drawText(0, -8, self._w, 14, Qt.AlignCenter, self._title)
        led = QColor("#0EA65E") if self.is_running() else QColor("#D14343")
        p.setBrush(QBrush(led)); p.setPen(Qt.NoPen); p.drawEllipse(self._w - 14, 4, 10, 10)

    def _tick(self):
        dt = 0.03
        self._rpm = (min(self._rpm_target, self._rpm + self._accel*dt)
                     if self._rpm < self._rpm_target else
                     max(self._rpm_target, self._rpm - self._accel*dt))
        self.update()
