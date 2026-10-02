from __future__ import annotations

import struct

from ..game import GameProcess
from ..patching import Asm, PatchSet, Site, call_site, jump_site
from .base import PatchFeature, Slider

SPEED_STEPS = (1, 2, 3, 5, 10, 20, 50, 100, 200, 500, 1000)
SEASON_STEPS = (1, 2, 3, 4, 6, 8)


def ticks_stub(asm: Asm, multiplier: int, stolen: str, back: int) -> None:
    asm.raw("89D0")
    asm.rip("480FAF05", multiplier)
    asm.raw("BAFFFFFFFF")
    asm.raw("4839D0")
    asm.raw("0F47C2")
    asm.raw("89C2")
    asm.raw(stolen)
    asm.jmp(back)


def call_returns_true(rva: int, target: int) -> Site:
    return Site(rva, call_site(rva, target, target).original, bytes.fromhex("B001909090"))


class TickMultiplier(PatchFeature):
    hooks: tuple[tuple[int, str], ...] = ()
    default = 10

    def __init__(self):
        super().__init__()
        self.sliders = [Slider("multiplier", SPEED_STEPS, self.default)]

    def build(self) -> PatchSet:
        asm = Asm(self.code_rva)
        sites = []
        for rva, stolen in self.hooks:
            stub = asm.here
            ticks_stub(asm, self.data_rva, stolen, rva + len(bytes.fromhex(stolen)))
            sites.append(jump_site(rva, stolen, stub))
        return PatchSet(sites, {self.code_rva: asm.build()})

    def write_data(self, game: GameProcess) -> None:
        game.write(self.data_rva, struct.pack("<Q", int(self.slider("multiplier").value)))


class SeasonMultiplier(PatchFeature):
    default = 2

    def __init__(self):
        super().__init__()
        self.sliders = [Slider("multiplier", SEASON_STEPS, self.default)]

    def write_data(self, game: GameProcess) -> None:
        game.write(self.data_rva, struct.pack("<I", int(self.slider("multiplier").value)))

    def add_edi_stub(self, asm: Asm, rva: int) -> Site:
        stub = asm.here
        asm.raw("8B80E4010000")
        asm.rip("0FAF05", self.data_rva)
        asm.raw("01C7")
        asm.jmp(rva + 6)
        return jump_site(rva, "03B8E4010000", stub)
