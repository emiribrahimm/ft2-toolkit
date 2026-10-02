from .animals import AnimalSpeed, InfiniteFood, PondSpeed
from .base import Feature, Slider
from .buildings import FarmhandEnergy, FreeWages, HarvestBuildingSpeed, ProductionSpeed
from .crops import CropGrowth, HarvestYield, NoWatering, TreesEverySeason
from .mine_house import MineRespawn, NoRecipeWait
from .player import InfiniteFuel, MovementSpeed, VehicleArea
from .tractor_speed import TractorSpeed

TABS = (
    ("Tractor & Player", (TractorSpeed, VehicleArea, MovementSpeed, InfiniteFuel)),
    ("Crops", (CropGrowth, NoWatering, TreesEverySeason, HarvestYield)),
    ("Animals", (AnimalSpeed, InfiniteFood, PondSpeed)),
    ("Buildings", (ProductionSpeed, HarvestBuildingSpeed, FarmhandEnergy, FreeWages)),
    ("Mine & House", (MineRespawn, NoRecipeWait)),
)


def create_all() -> list[tuple[str, list[Feature]]]:
    return [(name, [cls() for cls in classes]) for name, classes in TABS]
