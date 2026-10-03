from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..game import GameProcess, NotReady
from ..patching import PatchSet


@dataclass
class Slider:
    key: str
    steps: tuple[float, ...]
    value: float
    label: str | None = None
    fmt: str = "{:g}x"

    def snap(self, value: float) -> float:
        return min(self.steps, key=lambda step: abs(step - float(value)))


class Feature:
    key = ""
    title = ""
    description = ""
    hotkey_hint: str | None = None

    def __init__(self):
        self.enabled = False
        self.error: str | None = None
        self.waiting = False
        self.sliders: list[Slider] = []
        self._game: GameProcess | None = None
        self._listeners: list[Callable[[], None]] = []

    @property
    def is_attached(self) -> bool:
        return self._game is not None

    def subscribe(self, listener: Callable[[], None]) -> None:
        self._listeners.append(listener)

    def _changed(self) -> None:
        for listener in list(self._listeners):
            listener()

    def _run(self, action: Callable[[], None]) -> None:
        try:
            action()
        except Exception as e:
            self.error = str(e)

    def attach(self, game: GameProcess) -> None:
        self._game = game
        self.error = None
        self.waiting = False
        try:
            self.verify(game)
            if self.enabled:
                self.apply(game)
            else:
                self.revert(game)
        except NotReady:
            self.waiting = True
        except Exception as e:
            self.error = str(e)
        self._changed()

    def detach(self) -> None:
        self._game = None
        self._changed()

    def release(self) -> None:
        game = self._game
        if game is not None and self.error is None and not self.waiting and self.enabled:
            self._run(lambda: self.revert(game))
        self._game = None

    def suspend(self) -> None:
        self.release()
        self.waiting = False
        self._changed()

    def set_enabled(self, enabled: bool) -> None:
        if enabled == self.enabled:
            return
        self.enabled = enabled
        game = self._game
        if game is not None and self.error is None and not self.waiting:
            self._run(lambda: self.apply(game) if enabled else self.revert(game))
        self._changed()

    def update_live(self, update: Callable[[GameProcess], None]) -> None:
        game = self._game
        if game is not None and self.error is None and not self.waiting and self.enabled:
            self._run(lambda: update(game))
        self._changed()

    def slider(self, key: str) -> Slider:
        return next(s for s in self.sliders if s.key == key)

    def set_slider(self, key: str, value: float) -> None:
        s = self.slider(key)
        value = s.snap(value)
        if value == s.value:
            return
        s.value = value
        self.update_live(self.write_data)

    def write_data(self, game: GameProcess) -> None:
        pass

    def verify(self, game: GameProcess) -> None:
        raise NotImplementedError

    def apply(self, game: GameProcess) -> None:
        raise NotImplementedError

    def revert(self, game: GameProcess) -> None:
        raise NotImplementedError

    def load(self, settings: dict) -> None:
        self.enabled = bool(settings["Enabled"])
        for s in self.sliders:
            if s.key in settings["Values"]:
                s.value = s.snap(settings["Values"][s.key])

    def save(self, settings: dict) -> None:
        settings["Enabled"] = self.enabled
        for s in self.sliders:
            settings["Values"][s.key] = s.value


class PatchFeature(Feature):
    data_rva: int | None = None
    data_size = 0

    def __init__(self):
        super().__init__()
        self.patches = self.build()

    def build(self) -> PatchSet:
        raise NotImplementedError

    def verify(self, game: GameProcess) -> None:
        self.patches.verify(game)

    def apply(self, game: GameProcess) -> None:
        self.write_data(game)
        self.patches.apply(game)

    def revert(self, game: GameProcess) -> None:
        self.patches.revert(game)
        if self.data_rva is not None and any(game.read(self.data_rva, self.data_size)):
            game.write(self.data_rva, bytes(self.data_size))
