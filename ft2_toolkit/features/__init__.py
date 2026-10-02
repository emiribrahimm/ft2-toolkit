from .base import Feature
from .tractor_speed import TractorSpeed


def create_all() -> list[Feature]:
    return [TractorSpeed()]
