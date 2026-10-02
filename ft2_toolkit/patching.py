from __future__ import annotations

import struct
import time
from dataclasses import dataclass

from .game import GameError, GameProcess

ORIGINAL, PATCHED = "original", "patched"

TEXT_CAVE = 0x2B2600
TEXT_CAVE_BLOCK = 0x100
TEXT_CAVE_BLOCKS = 8
DATA_SIZE = 0x10


def cave_block(index: int) -> tuple[int, int]:
    if not 0 <= index < TEXT_CAVE_BLOCKS:
        raise ValueError(index)
    start = TEXT_CAVE + index * TEXT_CAVE_BLOCK
    return start, start + DATA_SIZE


@dataclass(frozen=True)
class Site:
    rva: int
    original: bytes
    patched: bytes

    def state(self, game: GameProcess) -> str:
        current = game.read(self.rva, len(self.original))
        if current == self.original:
            return ORIGINAL
        if current == self.patched:
            return PATCHED
        raise GameError(f"Unsupported game version (unexpected code at 0x{self.rva:X}).")


def _rel32(target: int, end: int) -> bytes:
    return struct.pack("<i", target - end)


def byte_site(rva: int, original: str, patched: str) -> Site:
    return Site(rva, bytes.fromhex(original), bytes.fromhex(patched))


def jump_site(rva: int, original: str, stub: int) -> Site:
    stolen = bytes.fromhex(original)
    return Site(rva, stolen, b"\xE9" + _rel32(stub, rva + 5) + b"\x90" * (len(stolen) - 5))


def call_site(rva: int, target: int, new_target: int) -> Site:
    return Site(rva, b"\xE8" + _rel32(target, rva + 5), b"\xE8" + _rel32(new_target, rva + 5))


def rip_site(rva: int, opcode: str, target: int, new_target: int) -> Site:
    prefix = bytes.fromhex(opcode)
    end = rva + len(prefix) + 4
    return Site(rva, prefix + _rel32(target, end), prefix + _rel32(new_target, end))


class Asm:
    def __init__(self, origin: int):
        self.origin = origin
        self.code = bytearray()
        self.labels: dict[str, int] = {}
        self.fixups: list[tuple[int, str]] = []

    @property
    def here(self) -> int:
        return self.origin + len(self.code)

    def raw(self, hex_bytes: str) -> Asm:
        self.code += bytes.fromhex(hex_bytes)
        return self

    def rip(self, prefix: str, target: int, suffix: str = "") -> Asm:
        head, tail = bytes.fromhex(prefix), bytes.fromhex(suffix)
        end = self.here + len(head) + 4 + len(tail)
        self.code += head + _rel32(target, end) + tail
        return self

    def jmp(self, target: int) -> Asm:
        return self.rip("E9", target)

    def label(self, name: str) -> Asm:
        self.labels[name] = len(self.code)
        return self

    def short(self, opcode: str, name: str) -> Asm:
        self.code += bytes.fromhex(opcode) + b"\0"
        self.fixups.append((len(self.code) - 1, name))
        return self

    def build(self) -> bytes:
        for pos, name in self.fixups:
            delta = self.labels[name] - (pos + 1)
            if not -128 <= delta <= 127:
                raise ValueError(name)
            self.code[pos] = delta & 0xFF
        return bytes(self.code)


class PatchSet:
    def __init__(self, sites: list[Site], code: dict[int, bytes] | None = None):
        self.sites = sites
        self.code = code or {}

    def is_patched(self, game: GameProcess) -> bool:
        return any(site.state(game) == PATCHED for site in self.sites)

    def verify(self, game: GameProcess) -> None:
        if self.is_patched(game):
            return
        for rva, code in self.code.items():
            current = game.read(rva, len(code))
            if any(current) and current != code:
                raise GameError("Unrecognized data in the code cave; left untouched for safety.")

    def apply(self, game: GameProcess) -> None:
        for rva, code in self.code.items():
            if game.read(rva, len(code)) != code:
                game.write(rva, code)
        pending = [site for site in self.sites if site.state(game) == ORIGINAL]
        if pending:
            busy = [(site.rva + 1, site.rva + len(site.original)) for site in pending]
            _frozen_write(game, [(site.rva, site.patched) for site in pending], busy)

    def revert(self, game: GameProcess) -> None:
        pending = [site for site in self.sites if site.state(game) == PATCHED]
        busy = [(site.rva + 1, site.rva + len(site.original)) for site in pending]
        busy += [(rva, rva + len(code)) for rva, code in self.code.items()]
        writes = [(site.rva, site.original) for site in pending]
        writes += [(rva, bytes(len(code))) for rva, code in self.code.items() if any(game.read(rva, len(code)))]
        if writes:
            _frozen_write(game, writes, busy)


def _frozen_write(game: GameProcess, writes: list[tuple[int, bytes]], busy: list[tuple[int, int]]) -> None:
    for _ in range(200):
        with game.frozen() as rips:
            if not any(start <= rip < end for rip in rips for start, end in busy):
                for rva, data in writes:
                    game.write(rva, data)
                return
        time.sleep(0.005)
    raise GameError("The game kept running the code being patched; try again.")
