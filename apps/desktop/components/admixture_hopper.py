from __future__ import annotations
from components.cement_hopper import CementHopper

class AdmixtureHopper(CementHopper):
    def __init__(self, *, capacity_kg: float = 10.0, title: str = "Admixture Weigh Hopper", draggable: bool = True):
        super().__init__(capacity_kg=capacity_kg, title=title, draggable=draggable)
