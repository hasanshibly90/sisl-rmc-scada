from __future__ import annotations
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QPen, QBrush, QColor
from PySide6.QtWidgets import QGraphicsObject, QGraphicsItem

class BeltConveyor(QGraphicsObject):
    def __init__(self, length_px: float = 600, belt_h: float = 28, draggable: bool = True, parent=None):
        super().__init__(parent)
        self.w = float(max(40, length_px)); self.h = float(max(8, belt_h))
        self._running=False; self._phase=0.0; self._speed=3.0; self._dir=1
        if draggable:
            self.setFlag(QGraphicsItem.ItemIsMovable, True)
            self.setFlag(QGraphicsItem.ItemIsSelectable, True)
            self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self._belt_color = QColor("#2F3742"); self._edge_color = QColor("#9AA4AF"); self._roller_color = QColor("#BDC6CF")
    def set_speed(self,v:float): self._speed=float(max(0.0,v))
    def set_direction(self,d:str): self._dir=-1 if str(d).lower()=="left" else 1
    def set_length(self,L:float): self.w=float(max(40,L)); self.prepareGeometryChange(); self.update()
    def start(self): self._running=True
    def stop(self):  self._running=False
    def advance_phase(self,amt:float):
        if self._running and self._speed>0: self._phase=(self._phase+self._dir*self._speed*amt)%1000.0; self.update()
    def boundingRect(self)->QRectF: pad=6; return QRectF(-pad,-pad,self.w+2*pad,self.h+2*pad)
    def paint(self,p:QPainter,opt,widget=None):
        p.setRenderHint(QPainter.Antialiasing,True)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(self._roller_color)); r=self.h*0.9
        p.drawEllipse(0-r/2,(self.h-r)/2,r,r); p.drawEllipse(self.w-r/2,(self.h-r)/2,r,r)
        p.setPen(QPen(self._edge_color,2)); p.setBrush(QBrush(self._belt_color)); p.drawRoundedRect(0,0,self.w,self.h,6,6)
        pen=QPen(QColor("#D7DDE3")); pen.setWidth(2); p.setPen(pen); step=max(20,self.h*1.6)
        offset=self._phase%step; y=self.h/2; x=-step+offset
        while x<=self.w+step:
            if self._dir>0: p.drawLine(x-6,y-6,x+6,y); p.drawLine(x-6,y+6,x+6,y)
            else:           p.drawLine(x+6,y-6,x-6,y); p.drawLine(x+6,y+6,x-6,y)
            x+=step
