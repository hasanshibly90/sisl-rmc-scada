from __future__ import annotations
from typing import List
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPixmap, QTransform
from PySide6.QtWidgets import QGraphicsObject, QGraphicsPixmapItem

class SpritePipe(QGraphicsObject):
    def __init__(self, straight: str, elbow: str, flange: str | None = None, scale: float = 1.0, parent=None):
        super().__init__(parent)
        self._straight = QPixmap(straight)
        self._elbow    = QPixmap(elbow)
        self._flange   = QPixmap(flange) if flange else None
        self._scale    = float(scale)
        self._points: List[QPointF] = []
        self._children: List[QGraphicsPixmapItem] = []
        self._wet = 0.0
        self.setZValue(-0.5)

    def set_wetness(self, k: float):
        self._wet = max(0.0, min(1.0, float(k)))
        for c in self._children:
            c.setOpacity(0.9 + 0.1 * self._wet)

    def boundingRect(self) -> QRectF:
        if not self._points: return QRectF(0, 0, 1, 1)
        xs = [p.x() for p in self._points]; ys = [p.y() for p in self._points]
        return QRectF(min(xs)-100, min(ys)-100, (max(xs)-min(xs))+200, (max(ys)-min(ys))+200)

    def paint(self, p, opt, widget=None): pass

    def _clear(self):
        for c in self._children:
            if c.scene(): c.scene().removeItem(c)
        self._children.clear()

    def set_path_points(self, pts: List[QPointF]):
        self._points = pts[:] if pts else []
        self._rebuild()

    def _rebuild(self):
        self._clear()
        if len(self._points) < 2: return

        for i in range(len(self._points)-1):
            a = self._points[i]; b = self._points[i+1]
            horiz = abs(a.y()-b.y()) < 0.5; vert = abs(a.x()-b.x()) < 0.5
            if not (horiz or vert): continue
            if horiz:
                x1,x2 = sorted([a.x(),b.x()]); y=a.y()
                step = max(1.0, self._straight.width()*self._scale); x=x1
                while x < x2:
                    tile=QGraphicsPixmapItem(self._straight, self)
                    tile.setScale(self._scale)
                    tile.setPos(x, y - (self._straight.height()*self._scale)/2.0)
                    self._children.append(tile); x += step
            else:
                y1,y2 = sorted([a.y(),b.y()]); x=a.x()
                step = max(1.0, self._straight.height()*self._scale); y=y1
                while y < y2:
                    tile=QGraphicsPixmapItem(self._straight, self)
                    tile.setScale(self._scale)
                    tile.setTransform(QTransform().rotate(90), True)
                    tile.setPos(x - (self._straight.height()*self._scale)/2.0, y)
                    self._children.append(tile); y += step

        for i in range(1, len(self._points)-1):
            prev=self._points[i-1]; cur=self._points[i]; nxt=self._points[i+1]
            dx1,dy1=cur.x()-prev.x(),cur.y()-prev.y(); dx2,dy2=nxt.x()-cur.x(),nxt.y()-cur.y()
            angle=0
            if   (dx1>0 and dy2>0) or (dy1>0 and dx2<0): angle=0
            elif (dy1>0 and dx2>0) or (dx1>0 and dy2<0): angle=90
            elif (dx1<0 and dy2<0) or (dy1<0 and dx2>0): angle=180
            elif (dy1<0 and dx2<0) or (dx1<0 and dy2>0): angle=270
            elbow=QGraphicsPixmapItem(self._elbow, self)
            elbow.setScale(self._scale); elbow.setTransform(QTransform().rotate(angle), True)
            elbow.setPos(cur.x()-(self._elbow.width()*self._scale)/2.0, cur.y()-(self._elbow.height()*self._scale)/2.0)
            self._children.append(elbow)
            if self._flange:
                fl=QGraphicsPixmapItem(self._flange, self); fl.setScale(self._scale)
                fl.setPos(cur.x()-(self._flange.width()*self._scale)/2.0, cur.y()-(self._flange.height()*self._scale)/2.0)
                self._children.append(fl)
