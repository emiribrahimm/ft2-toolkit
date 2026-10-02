from __future__ import annotations

import struct

from ..game import GameProcess
from ..patching import DATA_SIZE, Asm, PatchSet, byte_site, call_site, cave_block
from .base import PatchFeature, Slider
from .common import TickMultiplier

EARN_RESOURCE = 0x645870
EARN_RESOURCE_LIST = 0x645960


class CropGrowth(TickMultiplier):
    key = "cropGrowth"
    title = "Crop growth speed"
    description = ("Crops, herbs and flowers grow faster. "
                   "They also dry out faster unless 'No watering needed' is on.")
    data_rva, code_rva = cave_block(0)
    data_size = DATA_SIZE
    hooks = (
        (0x6B65C0, "48895C2420"),
        (0x6BAB80, "48895C2420"),
        (0x6B8CC0, "405341564883EC28"),
    )


class NoWatering(PatchFeature):
    key = "noWatering"
    title = "No watering needed"
    description = "Crops, herbs and flowers always count as watered, so flowers also reach full quality."

    def build(self) -> PatchSet:
        return PatchSet([
            byte_site(0x6B661D, "0FB67031", "40B60190"),
            byte_site(0x6BABDD, "0FB67031", "40B60190"),
            byte_site(0x6B8D42, "440FB67831", "41B7019090"),
            byte_site(0x6B8FB9, "752C", "EB2C"),
        ])


class TreesEverySeason(PatchFeature):
    key = "treesEverySeason"
    title = "Trees fruit every season"
    description = "Trees become harvestable at every season change (about every 17 minutes)."

    def build(self) -> PatchSet:
        return PatchSet([byte_site(0x6BF2BF, "7555", "EB55")])


class HarvestYield(PatchFeature):
    key = "harvestYield"
    title = "Harvest yield"
    description = ("Multiplies the produce from crops, herbs, flowers, trees, animals, ponds and the mine. "
                   "Storage limits still apply.")
    data_rva, code_rva = cave_block(6)
    data_size = DATA_SIZE
    single_sites = (0x6B782C, 0x6BBEBB, 0x6B9812, 0x6BEF4A, 0x6B52F2, 0x6A8A23, 0x6AAFA9)
    list_sites = (0x6ACC66,)

    def __init__(self):
        super().__init__()
        self.sliders = [Slider("multiplier", (1, 2, 3, 4, 5, 10), 2)]

    def build(self) -> PatchSet:
        asm = Asm(self.code_rva)
        single = asm.here
        asm.raw("488B4208")
        asm.rip("480FAF05", self.data_rva)
        asm.raw("48894208")
        asm.jmp(EARN_RESOURCE)
        many = asm.here
        asm.raw("488B4210")
        asm.raw("4885C0")
        asm.short("74", "done")
        asm.raw("448B5218")
        asm.raw("4C8D5828")
        asm.label("loop")
        asm.raw("4585D2")
        asm.short("74", "done")
        asm.raw("498B03")
        asm.rip("480FAF05", self.data_rva)
        asm.raw("498903")
        asm.raw("4983C310")
        asm.raw("41FFCA")
        asm.short("EB", "loop")
        asm.label("done")
        asm.jmp(EARN_RESOURCE_LIST)
        sites = [call_site(rva, EARN_RESOURCE, single) for rva in self.single_sites]
        sites += [call_site(rva, EARN_RESOURCE_LIST, many) for rva in self.list_sites]
        return PatchSet(sites, {self.code_rva: asm.build()})

    def write_data(self, game: GameProcess) -> None:
        game.write(self.data_rva, struct.pack("<Q", int(self.slider("multiplier").value)))
