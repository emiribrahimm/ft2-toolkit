from __future__ import annotations

from typing import Callable

from ..game import GameProcess


class Feature:
    key = ""
    title = ""
    description = ""
    hotkey_hint: str | None = None

    def __init__(self):
        self.enabled = False
        self.error: str | None = None
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

        def sync():
            self.verify(game)
            if self.enabled:
                self.apply(game)
            else:
                self.revert(game)

        self._run(sync)
        self._changed()

    def detach(self) -> None:
        self._game = None
        self._changed()

    def release(self) -> None:
        game = self._game
        if game is not None and self.error is None and self.enabled:
            self._run(lambda: self.revert(game))
        self._game = None

    def set_enabled(self, enabled: bool) -> None:
        if enabled == self.enabled:
            return
        self.enabled = enabled
        game = self._game
        if game is not None and self.error is None:
            self._run(lambda: self.apply(game) if enabled else self.revert(game))
        self._changed()

    def update_live(self, update: Callable[[GameProcess], None]) -> None:
        game = self._game
        if game is not None and self.error is None and self.enabled:
            self._run(lambda: update(game))
        self._changed()

    def verify(self, game: GameProcess) -> None:
        raise NotImplementedError

    def apply(self, game: GameProcess) -> None:
        raise NotImplementedError

    def revert(self, game: GameProcess) -> None:
        raise NotImplementedError

    def build_options(self, parent, theme):
        return None

    def load(self, settings: dict) -> None:
        self.enabled = bool(settings["Enabled"])

    def save(self, settings: dict) -> None:
        settings["Enabled"] = self.enabled
