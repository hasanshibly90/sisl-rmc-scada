from __future__ import annotations
from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import QPainter, QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsObject

class MotorBadge(QGraphicsObject):
    def __init__(self, anchor_fn, radius: float = 10.0, parent=None):
        super().__init__(parent)
        self._anchor_fn = anchor_fn; self._r = float(max(6.0, radius)); self._running = False
        self.setZValue(10); self._update_position()
    def set_running(self, running: bool): 
        if self._running != bool(running): self._running = bool(running); self.update()
    def is_running(self) -> bool: return self._running
    def refresh(self): self._update_position()
    def boundingRect(self) -> QRectF: d = self._r*2; return QRectF(0, 0, d, d)
    def paint(self, p: QPainter, opt, widget=None):
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(QPen(QColor("#101418"),2)); p.setBrush(QBrush(QColor("#0EA65E" if self._running else "#D14343")))
        p.drawEllipse(0,0,self._r*2,self._r*2); p.setPen(Qt.NoPen); p.setBrush(QBrush(QColor("#EEF2F6")))
        d=self._r*0.5; p.drawEllipse(self._r-d/2,self._r-d/2,d,d)
    def _update_position(self):
        try: scene_pt: QPointF = self._anchor_fn()
        except Exception: return
        self.setPos(scene_pt - QPointF(self._r, self._r))
