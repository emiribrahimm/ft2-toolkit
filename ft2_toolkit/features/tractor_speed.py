from __future__ import annotations

import struct
import tkinter as tk
from dataclasses import dataclass

from ..game import GameError, GameProcess
from .base import Feature

CAVE_RVA = 0x1C01F00
CAVE_SLOTS = 8

MIN_MULTIPLIER = 1.0
MAX_MULTIPLIER = 4.0
STEP = 0.25

MULSS_XMM0 = bytes.fromhex("F30F5905")
MOVSS_XMM0 = bytes.fromhex("F30F1005")
MOVSS_XMM8 = bytes.fromhex("F3440F1005")


@dataclass(frozen=True)
class Site:
    name: str
    rva: int
    opcode: bytes
    target_rva: int
    slot: int
    multiply: bool

    @property
    def disp_rva(self) -> int:
        return self.rva + len(self.opcode)

    @property
    def end_rva(self) -> int:
        return self.disp_rva + 4

    @property
    def slot_rva(self) -> int:
        return CAVE_RVA + 4 * self.slot


SITES = (
    Site("TractorWorkSpeed multiplier", 0x35D1CB, MULSS_XMM0, 0x1C02DB4, 0, True),
    Site("auto-tractor speed cap #1", 0x7AE97A, MOVSS_XMM8, 0x1C03648, 1, True),
    Site("auto-tractor speed cap #2", 0x7AE999, MOVSS_XMM8, 0x1C03648, 1, True),
    Site("minimum work interval", 0x7AEDDB, MOVSS_XMM0, 0x1C03644, 2, False),
    Site("TractorWorkInterval", 0x35D015, MOVSS_XMM0, 0x1C02E5C, 3, False),
    Site("TractorWorkInterval (legacy)", 0x35D065, MOVSS_XMM0, 0x1C02D10, 4, False),
)

ORIGINAL, PATCHED = "original", "patched"


def _site_state(game: GameProcess, site: Site) -> str:
    data = game.read(site.rva, len(site.opcode) + 4)
    if data[:len(site.opcode)] != site.opcode:
        raise GameError(f"Unsupported game version ({site.name} not found at the expected location).")
    target = site.end_rva + struct.unpack_from("<i", data, len(site.opcode))[0]
    if target == site.target_rva:
        return ORIGINAL
    if target == site.slot_rva:
        return PATCHED
    raise GameError(f"Unsupported game version ({site.name} points to an unexpected address).")


def _float32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def _compute_slots(game: GameProcess, k: float) -> list[float]:
    slots = [0.0] * CAVE_SLOTS
    for site in SITES:
        original = game.read_float(site.target_rva)
        slots[site.slot] = _float32(original * k if site.multiply else original / k)
    return slots


class TractorSpeed(Feature):
    key = "tractorSpeed"
    title = "Auto-tractor speed"
    description = "Speeds up both driving and field work of the tractor in auto mode, without skipping tiles."
    hotkey_hint = "Hotkey: F6 to toggle (works in-game)"

    def __init__(self):
        super().__init__()
        self._multiplier = 3.0

    @property
    def multiplier(self) -> float:
        return self._multiplier

    @multiplier.setter
    def multiplier(self, value: float) -> None:
        value = min(max(round(float(value) / STEP) * STEP, MIN_MULTIPLIER), MAX_MULTIPLIER)
        if value == self._multiplier:
            return
        self._multiplier = value
        self.update_live(self._write_constants)

    def verify(self, game: GameProcess) -> None:
        states = [_site_state(game, site) for site in SITES]
        if PATCHED in states:
            return

        cave = game.read(CAVE_RVA, 4 * CAVE_SLOTS)
        if not any(cave):
            return
        values = struct.unpack(f"<{CAVE_SLOTS}f", cave)
        cap = SITES[1]
        k = values[cap.slot] / game.read_float(cap.target_rva)
        if k > 0 and k == k:
            expected = _compute_slots(game, k)
            if all(abs(a - e) <= 1e-4 * max(1.0, abs(e)) for a, e in zip(values, expected)):
                return
        raise GameError("Unrecognized data in the code cave; left untouched for safety.")

    def apply(self, game: GameProcess) -> None:
        self._write_constants(game)
        for site in SITES:
            if _site_state(game, site) == ORIGINAL:
                game.write_int32(site.disp_rva, site.slot_rva - site.end_rva)

    def revert(self, game: GameProcess) -> None:
        for site in SITES:
            if _site_state(game, site) == PATCHED:
                game.write_int32(site.disp_rva, site.target_rva - site.end_rva)
        if any(game.read(CAVE_RVA, 4 * CAVE_SLOTS)):
            game.write(CAVE_RVA, bytes(4 * CAVE_SLOTS))

    def _write_constants(self, game: GameProcess) -> None:
        game.write(CAVE_RVA, struct.pack(f"<{CAVE_SLOTS}f", *_compute_slots(game, self._multiplier)))

    def load(self, settings: dict) -> None:
        super().load(settings)
        if "multiplier" in settings["Values"]:
            self.multiplier = settings["Values"]["multiplier"]

    def save(self, settings: dict) -> None:
        super().save(settings)
        settings["Values"]["multiplier"] = self._multiplier

    def build_options(self, parent, theme):
        frame = tk.Frame(parent, bg=theme.CARD)
        scale = tk.Scale(
            frame, from_=MIN_MULTIPLIER, to=MAX_MULTIPLIER, resolution=STEP, orient=tk.HORIZONTAL,
            showvalue=False, bg=theme.ACCENT, troughcolor=theme.TRACK, activebackground=theme.ACCENT_HOVER,
            highlightthickness=0, bd=0, sliderrelief=tk.FLAT, sliderlength=theme.px(18), width=theme.px(12),
            tickinterval=0,
        )
        value = tk.Label(frame, font=theme.VALUE_FONT, fg=theme.TEXT, bg=theme.CARD, width=5, anchor="e")
        scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        value.pack(side=tk.RIGHT)

        def sync():
            if scale.get() != self._multiplier:
                scale.set(self._multiplier)
            value.config(text=f"{self._multiplier:g}x")

        def on_scale(raw):
            self.multiplier = float(raw)

        scale.config(command=on_scale)
        self.subscribe(sync)
        sync()
        return frame
