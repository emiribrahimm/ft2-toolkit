from __future__ import annotations

import struct
from enum import Enum

from .game import GameError, GameProcess

NETWORK_MANAGER_TYPEINFO = 0x22E95D0
STAGE_PARAMETERS_TYPEINFO = 0x2308B60
STAGE_SCRIPT_TYPEINFO = 0x2308C08
STATIC_FIELDS = 0xB8


class Session(Enum):
    NO_FARM = "no farm"
    SOLO = "single-player"
    MULTIPLAYER = "multiplayer"


def _u64(game: GameProcess, address: int) -> int:
    return struct.unpack("<Q", game.read_abs(address, 8))[0]


def _count(game: GameProcess, lst: int) -> int:
    return struct.unpack("<i", game.read_abs(lst + 0x18, 4))[0] if lst else 0


def _statics(game: GameProcess, typeinfo: int) -> int:
    klass = _u64(game, game.base + typeinfo)
    return _u64(game, klass + STATIC_FIELDS) if klass else 0


def detect(game: GameProcess) -> Session:
    try:
        parameters = _statics(game, STAGE_PARAMETERS_TYPEINFO)
        network = _statics(game, NETWORK_MANAGER_TYPEINFO)
        stages = _statics(game, STAGE_SCRIPT_TYPEINFO)
        if parameters and (game.read_abs(parameters + 0xC, 1)[0] or _u64(game, parameters + 0x18)):
            return Session.MULTIPLAYER
        if network and _u64(game, network):
            return Session.MULTIPLAYER
        stage = _u64(game, stages) if stages else 0
        if not parameters or not stage:
            return Session.NO_FARM
        players = _count(game, _u64(game, stage + 0xA8))
        local_players = _count(game, _u64(game, stage + 0xB0))
        if players > 1 or local_players > 1:
            return Session.MULTIPLAYER
        return Session.SOLO if players == 1 else Session.NO_FARM
    except GameError:
        return Session.NO_FARM
