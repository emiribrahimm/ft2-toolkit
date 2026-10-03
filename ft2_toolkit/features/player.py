from __future__ import annotations

import struct

from ..game import GameError, GameProcess
from ..patching import DATA_SIZE, Asm, PatchSet, byte_site, cave_block, jump_site, rip_site
from .base import Feature, PatchFeature, Slider

MOVE_STEPS = (1, 1.25, 1.5, 1.75, 2, 2.5, 3)
SPEED_CLAMP = 0x1C02DBC

GAME_TYPEINFO = 0x22CCDF8
STATIC_FIELDS = 0xB8
DEFAULT_AREA = 3
AREA_STEPS = (5, 7, 9)


class MovementSpeed(PatchFeature):
    key = "walkSpeed"
    title = "Movement speed"
    description = "Faster walking, running and driving when you steer a vehicle yourself."
    data_rva, code_rva = cave_block(7)
    data_size = DATA_SIZE

    def __init__(self):
        super().__init__()
        self.sliders = [Slider("multiplier", MOVE_STEPS, 1.5)]

    def build(self) -> PatchSet:
        speed, clamp = self.data_rva, self.data_rva + 4
        asm = Asm(self.code_rva)
        walk = asm.here
        asm.raw("F3440F106B30")
        asm.rip("F3440F592D", speed)
        asm.jmp(0x3431EC)
        sprint = asm.here
        asm.raw("F30F107014")
        asm.rip("F30F5935", speed)
        asm.jmp(0x343528)
        return PatchSet([
            jump_site(0x3431E6, "F3440F106B30", walk),
            jump_site(0x343523, "F30F107014", sprint),
            rip_site(0x3434A9, "F30F100D", SPEED_CLAMP, clamp),
        ], {self.code_rva: asm.build()})

    def write_data(self, game: GameProcess) -> None:
        game.write(self.data_rva, struct.pack("<2f", self.slider("multiplier").value, 1000.0))


class CameraDistance(PatchFeature):
    key = "cameraDistance"
    title = "Camera distance"
    description = "Lets the camera sit further away from your character at every zoom level."
    data_rva, code_rva = cave_block(0)
    data_size = DATA_SIZE

    def __init__(self):
        super().__init__()
        self.sliders = [Slider("multiplier", MOVE_STEPS, 1.5)]

    def build(self) -> PatchSet:
        asm = Asm(self.code_rva)
        stub = asm.here
        asm.raw("F3440F10BFEC000000")
        asm.rip("F3440F593D", self.data_rva)
        asm.jmp(0x3443CD)
        return PatchSet([jump_site(0x3443C4, "F3440F10BFEC000000", stub)], {self.code_rva: asm.build()})

    def write_data(self, game: GameProcess) -> None:
        game.write(self.data_rva, struct.pack("<f", self.slider("multiplier").value))


class FastTransitions(PatchFeature):
    key = "fastTransitions"
    title = "Fast transitions"
    description = "Entering the house or town, teleporting and getting on vehicles take a fraction of the time."
    data_rva, _ = cave_block(1)
    data_size = DATA_SIZE
    sites = ((0x7C67B4, 0x1C02BFC, 0), (0x7C6803, 0x1C02BFC, 0), (0x7C6AE9, 0x1C02BFC, 0), (0x7C6B47, 0x1C02C00, 4))

    def build(self) -> PatchSet:
        return PatchSet([rip_site(rva, "0F2F0D", target, self.data_rva + slot) for rva, target, slot in self.sites])

    def write_data(self, game: GameProcess) -> None:
        game.write(self.data_rva, struct.pack("<2f", 0.5 / 5, 0.7 / 5))


class VehicleArea(Feature):
    key = "vehicleArea"
    title = "Bigger tractor area"
    description = "Vehicles work a bigger square of tiles at once instead of 3×3."

    def __init__(self):
        super().__init__()
        self.sliders = [Slider("size", AREA_STEPS, 5, fmt="{0:g}×{0:g}")]

    def _address(self, game: GameProcess) -> int:
        klass = game.read_pointer(game.base + GAME_TYPEINFO)
        return game.read_pointer(klass + STATIC_FIELDS)

    def _write(self, game: GameProcess, size: int) -> None:
        game.write_abs(self._address(game), struct.pack("<2i", size, size))

    def verify(self, game: GameProcess) -> None:
        x, y = struct.unpack("<2i", game.read_abs(self._address(game), 8))
        if x != y or x not in (DEFAULT_AREA,) + AREA_STEPS:
            raise GameError(f"Unsupported game version (unexpected tractor area {x}×{y}).")

    def apply(self, game: GameProcess) -> None:
        self._write(game, int(self.slider("size").value))

    def revert(self, game: GameProcess) -> None:
        self._write(game, DEFAULT_AREA)

    def write_data(self, game: GameProcess) -> None:
        self.apply(game)


class InfiniteFuel(PatchFeature):
    key = "infiniteFuel"
    title = "Infinite fuel"
    description = "Working with vehicles no longer uses fuel."

    def build(self) -> PatchSet:
        return PatchSet([
            byte_site(0x7BF461, "730D", "EB0D"),
            byte_site(0x7BF490, "2BDE", "9090"),
        ])
