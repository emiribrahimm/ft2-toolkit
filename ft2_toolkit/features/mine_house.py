from __future__ import annotations

from ..patching import DATA_SIZE, Asm, PatchSet, byte_site, cave_block, jump_site
from .base import PatchFeature
from .common import SeasonMultiplier


class MineRespawn(SeasonMultiplier):
    key = "mineRespawn"
    title = "Mine respawn speed"
    description = "Minerals and mushrooms in the mine come back after fewer season changes (at best every season)."
    data_rva, code_rva = cave_block(5)
    data_size = DATA_SIZE

    def build(self) -> PatchSet:
        asm = Asm(self.code_rva)
        spot = asm.here
        asm.raw("8B88E4010000")
        asm.rip("0FAF0D", self.data_rva)
        asm.jmp(0x6AA97F)
        shroom = self.add_edi_stub(asm, 0x6A8515)
        return PatchSet([jump_site(0x6AA979, "8B88E4010000", spot), shroom], {self.code_rva: asm.build()})


class NoRecipeWait(PatchFeature):
    key = "noRecipeWait"
    title = "No waiting between recipe steps"
    description = "Cooking, painting, carving and song steps are ready again right away."

    def build(self) -> PatchSet:
        return PatchSet([byte_site(0x6C7816, "7259", "9090")])
