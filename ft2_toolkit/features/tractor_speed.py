from __future__ import annotations

import struct

from ..game import GameProcess
from ..patching import PatchSet, rip_site
from .base import PatchFeature, Slider

CAVE_RVA = 0x1C01F00
CAVE_SLOTS = 8

MULSS_XMM0 = "F30F5905"
MOVSS_XMM0 = "F30F1005"
MOVSS_XMM8 = "F3440F1005"

SITES = (
    (0x35D1CB, MULSS_XMM0, 0x1C02DB4, 0, True),
    (0x7AE97A, MOVSS_XMM8, 0x1C03648, 1, True),
    (0x7AE999, MOVSS_XMM8, 0x1C03648, 1, True),
    (0x7AEDDB, MOVSS_XMM0, 0x1C03644, 2, False),
    (0x35D015, MOVSS_XMM0, 0x1C02E5C, 3, False),
    (0x35D065, MOVSS_XMM0, 0x1C02D10, 4, False),
)


class TractorSpeed(PatchFeature):
    key = "tractorSpeed"
    title = "Auto-tractor speed"
    description = "Speeds up both driving and field work of the tractor in auto mode, without skipping tiles."
    hotkey_hint = "Hotkey: F6 to toggle (works in-game)"
    data_rva = CAVE_RVA
    data_size = 4 * CAVE_SLOTS

    def __init__(self):
        super().__init__()
        steps = tuple(1 + 0.25 * i for i in range(13))
        self.sliders = [Slider("multiplier", steps, 3.0)]

    def build(self) -> PatchSet:
        return PatchSet([
            rip_site(rva, opcode, target, CAVE_RVA + 4 * slot)
            for rva, opcode, target, slot, _ in SITES
        ])

    def write_data(self, game: GameProcess) -> None:
        k = self.slider("multiplier").value
        slots = [0.0] * CAVE_SLOTS
        for _, _, target, slot, multiply in SITES:
            original = game.read_float(target)
            slots[slot] = original * k if multiply else original / k
        game.write(CAVE_RVA, struct.pack(f"<{CAVE_SLOTS}f", *slots))
