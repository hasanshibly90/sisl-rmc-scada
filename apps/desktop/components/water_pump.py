from __future__ import annotations
from components.pump_motor import PumpMotor

class WaterPump(PumpMotor):
    def __init__(self, *, title: str = "WATER PUMP", draggable: bool = True):
        super().__init__(title=title, color="#4CC3FF", body_w=86, body_h=56, draggable=draggable)
