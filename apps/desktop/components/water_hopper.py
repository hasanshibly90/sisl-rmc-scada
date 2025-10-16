from __future__ import annotations
from components.cement_hopper import CementHopper

class WaterHopper(CementHopper):
    def __init__(self, *, capacity_kg: float = 100.0, title: str = "Water Weigh Hopper", draggable: bool = True):
        super().__init__(capacity_kg=capacity_kg, title=title, draggable=draggable)
