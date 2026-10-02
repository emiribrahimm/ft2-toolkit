from __future__ import annotations

from ..patching import DATA_SIZE, Asm, PatchSet, byte_site, cave_block
from .base import PatchFeature
from .common import SeasonMultiplier, TickMultiplier


class AnimalSpeed(TickMultiplier):
    key = "animalSpeed"
    title = "Animal production speed"
    description = "Animals produce faster. They also eat faster unless 'Animal food never runs out' is on."
    data_rva, code_rva = cave_block(1)
    data_size = DATA_SIZE
    hooks = ((0x6B3AE0, "4053554156"),)


class InfiniteFood(PatchFeature):
    key = "infiniteFood"
    title = "Animal food never runs out"
    description = "Animals keep eating even with empty feeders, and the food in feeders is never used up."

    def build(self) -> PatchSet:
        return PatchSet([
            byte_site(0x6B3AF0, "418BE8", "83CDFF"),
            byte_site(0x683C97, "294320", "909090"),
            byte_site(0x683CA2, "44896320", "90909090"),
            byte_site(0x683CFB, "294320", "909090"),
            byte_site(0x683D00, "44896320", "90909090"),
        ])


class PondSpeed(SeasonMultiplier):
    key = "pondSpeed"
    title = "Pond speed"
    description = "Each season change counts as several seasons for ponds, so fish are ready sooner (at best every season)."
    data_rva, code_rva = cave_block(2)
    data_size = DATA_SIZE

    def build(self) -> PatchSet:
        asm = Asm(self.code_rva)
        site = self.add_edi_stub(asm, 0x6BD422)
        return PatchSet([site], {self.code_rva: asm.build()})
