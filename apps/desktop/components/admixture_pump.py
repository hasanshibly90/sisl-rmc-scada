from __future__ import annotations
from components.pump_motor import PumpMotor

class AdmixturePump(PumpMotor):
    def __init__(self, *, title: str = "ADMIX PUMP", draggable: bool = True):
        super().__init__(title=title, color="#B388FF", body_w=82, body_h=54, draggable=draggable)
