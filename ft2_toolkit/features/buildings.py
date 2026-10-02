from __future__ import annotations

from ..patching import DATA_SIZE, PatchSet, byte_site, cave_block
from .base import PatchFeature
from .common import TickMultiplier, call_returns_true

CAN_PAY = 0x63A1C0
TRY_BUY = 0x667580


class ProductionSpeed(TickMultiplier):
    key = "productionSpeed"
    title = "Production building speed"
    description = "Production buildings turn their input into goods faster."
    data_rva, code_rva = cave_block(3)
    data_size = DATA_SIZE
    hooks = ((0x6DF130, "48895C2420"),)


class HarvestBuildingSpeed(TickMultiplier):
    key = "harvestBuildingSpeed"
    title = "Harvest building speed"
    description = "Buildings that you harvest on a timer become ready faster."
    data_rva, code_rva = cave_block(4)
    data_size = DATA_SIZE
    hooks = ((0x6D6EF0, "40534883EC20"),)


class FarmhandEnergy(PatchFeature):
    key = "farmhandEnergy"
    title = "Farmhands never get tired"
    description = "Farmhand energy no longer goes down while they work."

    def build(self) -> PatchSet:
        return PatchSet([byte_site(0x6D2F8D, "760E297B60", "9090909090")])


class FreeWages(PatchFeature):
    key = "freeWages"
    title = "Free farmhand wages"
    description = "Paying farmhands (including from the town) costs no money."

    def build(self) -> PatchSet:
        return PatchSet([
            call_returns_true(0x6D1F4D, CAN_PAY),
            call_returns_true(0x6D331F, TRY_BUY),
            call_returns_true(0x6D2B00, CAN_PAY),
            call_returns_true(0x6D2BBE, TRY_BUY),
        ])
