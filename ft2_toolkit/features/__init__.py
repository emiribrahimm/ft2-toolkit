from .base import Feature, Slider
from .player import CameraDistance, FastTransitions, InfiniteFuel, MovementSpeed, VehicleArea
from .tractor_speed import TractorSpeed

TABS = (
    ("Tractor", (TractorSpeed, VehicleArea, InfiniteFuel)),
    ("Player", (MovementSpeed, CameraDistance, FastTransitions)),
)


def create_all() -> list[tuple[str, list[Feature]]]:
    return [(name, [cls() for cls in classes]) for name, classes in TABS]
