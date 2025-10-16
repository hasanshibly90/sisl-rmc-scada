# components/plant_view.py
from PySide6.QtWidgets import QGraphicsView
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from theme import BG

class PlantView(QGraphicsView):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        self.setBackgroundBrush(BG)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.RubberBandDrag)

    def wheelEvent(self, e):  # disable zoom
        e.ignore()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.fit_to_items()

    def fit_to_items(self):
        sc = self.scene()
        if not sc: return
        rect = sc.itemsBoundingRect()
        if rect.isEmpty(): return
        self.fitInView(rect.adjusted(-40, -40, 40, 40), Qt.KeepAspectRatio)
