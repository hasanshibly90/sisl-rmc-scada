# components/cement_hopper.py
from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont
from PySide6.QtWidgets import QGraphicsObject, QGraphicsItem, QGraphicsSimpleTextItem

EDGE        = QColor(48, 56, 66)
FACE        = QColor(220, 224, 232)
FACE_DARK   = QColor(195, 202, 212)
TXT         = QColor(235, 240, 248)
BAR_BG      = QColor(255, 255, 255, 36)
BAR_FG      = QColor(110, 235, 131, 230)

class CementHopper(QGraphicsObject):
    """
    Simple cement hopper (capacity, weight) with a slim gauge.
    Public API:
      set_title(text)
      set_capacity_kg(kg), get_capacity_kg()
      set_weight_kg(kg),   get_weight_kg()
      add_material(kg)     # increments weight, clamps to capacity
      inlet_scene()        # top-center inlet for conveyors
    """
    def __init__(self, w=280, h=220, capacity_kg=500.0, title="Cement Hopper", draggable=True, parent=None):
        super().__init__(parent)
        self.w, self.h = float(w), float(h)
        self._capacity = float(capacity_kg)
        self._weight   = 0.0
        self._title    = str(title)

        if draggable:
            self.setFlag(QGraphicsItem.ItemIsMovable, True)
            self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)

        self.title_item = QGraphicsSimpleTextItem(self._title, self)
        tf = self.title_item.font(); tf.setBold(True); tf.setPointSize(11)
        self.title_item.setFont(tf); self.title_item.setBrush(QBrush(TXT))

        self.weight_item = QGraphicsSimpleTextItem("0.00 / 0.00 kg", self)
        wf = self.weight_item.font(); wf.setPointSize(10)
        self.weight_item.setFont(wf); self.weight_item.setBrush(QBrush(TXT))

    # public API
    def set_title(self, t: str): self._title = str(t); self.update()
    def set_capacity_kg(self, kg: float): self._capacity = max(1.0, float(kg)); self.update()
    def get_capacity_kg(self) -> float: return self._capacity
    def set_weight_kg(self, kg: float): self._weight = max(0.0, min(float(kg), self._capacity)); self.update()
    def get_weight_kg(self) -> float: return self._weight
    def add_material(self, kg: float): self.set_weight_kg(self._weight + float(kg))

    # inlet position (top-center)
    def inlet_scene(self) -> QPointF:
        rect = self.mapRectToScene(self.boundingRect())
        return QPointF(rect.center().x(), rect.top())

    # qgraphics
    def boundingRect(self) -> QRectF:
        m = 40
        return QRectF(-self.w/2 - m, -self.h/2 - m, self.w + 2*m, self.h + 2*m)

    def paint(self, p: QPainter, option, widget=None):
        del option, widget
        p.setRenderHint(QPainter.Antialiasing, True)

        body = QRectF(-self.w/2, -self.h/2, self.w, self.h*0.68)
        funnel = QRectF(-self.w*0.22, body.bottom()-2, self.w*0.44, self.h*0.22)
        bar = QRectF(-self.w*0.46, funnel.bottom()+14, self.w*0.92, 10)

        # title
        self.title_item.setText(self._title)
        tbr = self.title_item.boundingRect()
        self.title_item.setPos(-tbr.width()/2, body.top()-tbr.height()-6)

        # body
        p.setPen(QPen(EDGE, 2)); p.setBrush(QBrush(FACE))
        p.drawRoundedRect(body, 10, 10)
        # funnel
        p.setBrush(QBrush(FACE_DARK))
        p.drawRoundedRect(funnel, 6, 6)

        # weight text
        self.weight_item.setText(f"{self._weight:0.2f} / {self._capacity:0.2f} kg")
        wbr = self.weight_item.boundingRect()
        self.weight_item.setPos(-wbr.width()/2, bar.top()-wbr.height()-6)

        # progress bar
        frac = 0.0 if self._capacity <= 0 else max(0.0, min(1.0, self._weight / self._capacity))
        p.setPen(QPen(EDGE, 1)); p.setBrush(QBrush(BAR_BG)); p.drawRoundedRect(bar, 5, 5)
        fill = QRectF(bar.left()+2, bar.top()+2, (bar.width()-4)*frac, bar.height()-4)
        if fill.width() > 0:
            p.setPen(Qt.NoPen); p.setBrush(QBrush(BAR_FG)); p.drawRoundedRect(fill, 4, 4)
