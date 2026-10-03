from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Callable

from .game import GameProcess
from .patching import PatchSet, byte_site

HERB_ANY_SEASON = PatchSet([byte_site(0x6BB327, "0F84910E0000", "909090909090")])

FARM_DATA_TYPEINFO = 0x22BB340
CROP_TYPEINFO = 0x22BB298
HERB_TYPEINFO = 0x22BBA78
FLOWER_TYPEINFO = 0x22BB9D0
TREE_TYPEINFO = 0x22BCB88


def _u8(game: GameProcess, address: int) -> int:
    return game.read_abs(address, 1)[0]


def _u32(game: GameProcess, address: int) -> int:
    return struct.unpack("<I", game.read_abs(address, 4))[0]


def _u64(game: GameProcess, address: int) -> int:
    return struct.unpack("<Q", game.read_abs(address, 8))[0]


def _put8(game: GameProcess, address: int, value: int) -> None:
    game.write_abs(address, bytes([value]))


def _put32(game: GameProcess, address: int, value: int) -> None:
    game.write_abs(address, struct.pack("<I", value))


def _pointers(game: GameProcess, address: int, count: int) -> list[int]:
    if count <= 0:
        return []
    return [p for p in struct.unpack(f"<{count}Q", game.read_abs(address, 8 * count)) if p]


def _list(game: GameProcess, lst: int) -> list[int]:
    if not lst:
        return []
    items = _u64(game, lst + 0x10)
    size = struct.unpack("<i", game.read_abs(lst + 0x18, 4))[0]
    return _pointers(game, items + 0x20, size) if items else []


def _array(game: GameProcess, arr: int) -> list[int]:
    return _pointers(game, arr + 0x20, _u64(game, arr + 0x18)) if arr else []


def _farm(game: GameProcess) -> int:
    klass = game.read_pointer(game.base + FARM_DATA_TYPEINFO)
    statics = game.read_pointer(klass + 0xB8)
    return game.read_pointer(statics)


def _contents(game: GameProcess, farm: int, typeinfo: int) -> list[int]:
    klass = game.read_pointer(game.base + typeinfo)
    found: dict[int, None] = {}
    for chunk in _array(game, _u64(game, farm + 0x178)):
        for lst in (_u64(game, chunk + 0x28), _u64(game, chunk + 0x30)):
            for obj in _list(game, lst):
                if _u64(game, obj) == klass:
                    found[obj] = None
    return list(found)


def _definition(game: GameProcess, obj: int) -> int:
    return _u64(game, obj + 0x10)


def grow_crops(game: GameProcess, farm: int) -> int:
    count = 0
    for crop in _contents(game, farm, CROP_TYPEINFO):
        if _u8(game, crop + 0x20) == 0:
            _put32(game, crop + 0x30, _u32(game, _definition(game, crop) + 0xD4))
            count += 1
    return count


def grow_herbs(game: GameProcess, farm: int) -> int:
    count = 0
    for herb in _contents(game, farm, HERB_TYPEINFO):
        if _u8(game, herb + 0x20) in (0, 1):
            _put32(game, herb + 0x30, _u32(game, _definition(game, herb) + 0xD4))
            _put8(game, herb + 0x20, 2)
        count += 1
    return count


def grow_flowers(game: GameProcess, farm: int) -> int:
    count = 0
    for flower in _contents(game, farm, FLOWER_TYPEINFO):
        if _u32(game, flower + 0x20) == 0:
            _put32(game, flower + 0x30, _u32(game, _definition(game, flower) + 0xD0))
            count += 1
    return count


def ripen_trees(game: GameProcess, farm: int) -> int:
    count = 0
    for tree in _contents(game, farm, TREE_TYPEINFO):
        if _u32(game, tree + 0x28) == 1:
            _put32(game, tree + 0x28, 0)
            count += 1
    return count


def ready_animals(game: GameProcess, farm: int) -> int:
    count = 0
    for field in _list(game, _u64(game, farm + 0x10)):
        for group in _list(game, _u64(game, field + 0x10)):
            waiting = 0
            for animal in _list(game, _u64(game, group + 0x18)):
                if _u32(game, animal + 0x28) != 0:
                    continue
                needed = _u32(game, _definition(game, animal) + 0xD0)
                if needed == 0:
                    continue
                if _u32(game, animal + 0x2C) < needed - 1:
                    _put32(game, animal + 0x2C, needed - 1)
                waiting += 1
            if waiting and _u32(game, group + 0x20) < waiting:
                _put32(game, group + 0x20, waiting)
            count += waiting
    return count


def ready_fish(game: GameProcess, farm: int) -> int:
    count = 0
    for pond in _list(game, _u64(game, farm + 0x2C8)):
        if _u32(game, pond + 0x10) != 0:
            continue
        for tile in _list(game, _u64(game, pond + 0x18)):
            _put32(game, tile + 0x30, _u32(game, _definition(game, tile) + 0xD0))
            _put32(game, tile + 0x34, 1)
        _put32(game, pond + 0x10, 1)
        count += 1
    return count


@dataclass(frozen=True)
class InstantAction:
    label: str
    noun: str
    run: Callable[[GameProcess, int], int]
    patch: PatchSet | None = None

    def release(self, game: GameProcess) -> None:
        if self.patch is not None:
            self.patch.revert(game)

    def __call__(self, game: GameProcess) -> str:
        if self.patch is not None:
            self.patch.verify(game)
            self.patch.apply(game)
        with game.frozen():
            count = self.run(game, _farm(game))
        if count == 0:
            return f"No {self.noun} needed it."
        return f"Done: {count} {self.noun}."


ACTIONS = (
    InstantAction("Grow crops", "crops", grow_crops),
    InstantAction("Grow flowers", "flowers", grow_flowers),
    InstantAction("Grow herbs", "herbs", grow_herbs, HERB_ANY_SEASON),
    InstantAction("Ripen trees", "trees", ripen_trees),
    InstantAction("Animals ready", "animals", ready_animals),
    InstantAction("Fish ready", "ponds", ready_fish),
)
