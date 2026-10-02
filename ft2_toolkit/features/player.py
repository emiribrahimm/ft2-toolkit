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
    key = "movementSpeed"
    title = "Movement speed"
    description = "Faster walking and running, and faster driving when you steer the tractor yourself."
    data_rva, code_rva = cave_block(7)
    data_size = DATA_SIZE

    def __init__(self):
        super().__init__()
        self.sliders = [
            Slider("onFoot", MOVE_STEPS, 1.5, "On foot"),
            Slider("driving", MOVE_STEPS, 1.5, "Driving"),
        ]

    def build(self) -> PatchSet:
        foot, vehicle, clamp = self.data_rva, self.data_rva + 4, self.data_rva + 8
        asm = Asm(self.code_rva)
        walk = asm.here
        asm.raw("F3440F106B30")
        asm.raw("4C8B9398000000")
        asm.raw("4D85D2")
        asm.short("74", "foot")
        asm.raw("41807A1A00")
        asm.short("75", "vehicle")
        asm.label("foot")
        asm.rip("F3440F592D", foot)
        asm.jmp(0x3431EC)
        asm.label("vehicle")
        asm.rip("F3440F592D", vehicle)
        asm.jmp(0x3431EC)
        sprint = asm.here
        asm.raw("F30F107014")
        asm.rip("F30F5935", foot)
        asm.jmp(0x343528)
        return PatchSet([
            jump_site(0x3431E6, "F3440F106B30", walk),
            jump_site(0x343523, "F30F107014", sprint),
            rip_site(0x3434A9, "F30F100D", SPEED_CLAMP, clamp),
        ], {self.code_rva: asm.build()})

    def write_data(self, game: GameProcess) -> None:
        values = (self.slider("onFoot").value, self.slider("driving").value, 1000.0)
        game.write(self.data_rva, struct.pack("<3f", *values))


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
