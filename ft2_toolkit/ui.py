from __future__ import annotations

import queue
import tkinter as tk
import winsound

from . import win32
from .features import Feature, create_all
from .features.tractor_speed import TractorSpeed
from .game import GameProcess
from .hotkey import HotkeyListener
from .settings import Settings

APP_NAME = "FT2 Toolkit"
POLL_MS = 1000
HOTKEY_TOGGLE_TRACTOR = 1


class Theme:
    BACKGROUND = "#1E1F22"
    CARD = "#2B2D31"
    TEXT = "#F2F3F5"
    MUTED = "#A0A4AB"
    ACCENT = "#3BA55D"
    ACCENT_HOVER = "#4CC274"
    WARNING = "#F0B232"
    ERROR = "#ED4245"
    TRACK = "#4E5058"

    BODY = ("Segoe UI", 10)
    SMALL = ("Segoe UI", 9)
    CARD_TITLE = ("Segoe UI Semibold", 11)
    APP_TITLE = ("Segoe UI Semibold", 14)
    VALUE_FONT = ("Segoe UI Semibold", 11)

    scale = 1.0

    @classmethod
    def px(cls, value: float) -> int:
        return int(round(value * cls.scale))


class ToggleSwitch(tk.Canvas):
    def __init__(self, parent, command):
        self._width, self._height = Theme.px(46), Theme.px(24)
        super().__init__(parent, width=self._width, height=self._height, bg=Theme.CARD,
                         highlightthickness=0, bd=0, cursor="hand2", takefocus=True)
        self._command = command
        self._value = False
        self.bind("<Button-1>", lambda e: self._command(not self._value))
        self.bind("<space>", lambda e: self._command(not self._value))
        self._draw()

    def set(self, value: bool) -> None:
        if value != self._value:
            self._value = value
            self._draw()

    def _draw(self) -> None:
        self.delete("all")
        w, h = self._width, self._height
        color = Theme.ACCENT if self._value else Theme.TRACK
        self.create_oval(0, 0, h, h, fill=color, outline=color)
        self.create_oval(w - h - 1, 0, w - 1, h, fill=color, outline=color)
        self.create_rectangle(h / 2, 0, w - h / 2 - 1, h, fill=color, outline=color)
        pad = Theme.px(3)
        d = h - 2 * pad
        x = w - d - pad - 1 if self._value else pad
        self.create_oval(x, pad, x + d, pad + d, fill="white", outline="white")


class FeatureCard(tk.Frame):
    def __init__(self, parent, feature: Feature, width: int):
        super().__init__(parent, bg=Theme.CARD, padx=Theme.px(14), pady=Theme.px(12))
        self.feature = feature
        self.columnconfigure(0, weight=1)
        text_width = width - Theme.px(28 + 60)

        tk.Label(self, text=feature.title, font=Theme.CARD_TITLE, fg=Theme.TEXT, bg=Theme.CARD,
                 anchor="w").grid(row=0, column=0, sticky="w")
        tk.Label(self, text=feature.description, font=Theme.BODY, fg=Theme.MUTED, bg=Theme.CARD,
                 wraplength=text_width, justify="left", anchor="w").grid(row=1, column=0, sticky="w",
                                                                         pady=(Theme.px(4), 0))
        self.toggle = ToggleSwitch(self, feature.set_enabled)
        self.toggle.grid(row=0, column=1, rowspan=2, sticky="ne", padx=(Theme.px(8), 0))

        row = 2
        options = feature.build_options(self, Theme)
        if options is not None:
            options.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(Theme.px(8), 0))
            row += 1

        self.state = tk.Label(self, font=Theme.SMALL, bg=Theme.CARD, anchor="w", justify="left",
                              wraplength=width - Theme.px(28))
        self.state.grid(row=row, column=0, columnspan=2, sticky="w", pady=(Theme.px(8), 0))
        row += 1

        if feature.hotkey_hint:
            tk.Label(self, text=feature.hotkey_hint, font=Theme.SMALL, fg=Theme.MUTED, bg=Theme.CARD,
                     anchor="w").grid(row=row, column=0, columnspan=2, sticky="w", pady=(Theme.px(2), 0))

        feature.subscribe(self.sync)
        self.sync()

    def sync(self) -> None:
        f = self.feature
        self.toggle.set(f.enabled)
        if f.error:
            text, color = "⚠ " + f.error, Theme.ERROR
        elif not f.is_attached:
            text, color = ("On · applies when the game starts", Theme.WARNING) if f.enabled else ("Off", Theme.MUTED)
        elif f.enabled:
            text, color = "On · applied to the game", Theme.ACCENT
        else:
            text, color = "Off · game unchanged", Theme.MUTED
        self.state.config(text=text, fg=color)


class MainWindow:
    CONTENT_WIDTH = 440

    def __init__(self, root: tk.Tk):
        self.root = root
        self.settings = Settings.load()
        self.features = create_all()
        self.tractor_speed = next(f for f in self.features if isinstance(f, TractorSpeed))
        self.game: GameProcess | None = None

        for f in self.features:
            f.load(self.settings.feature(f.key))
            f.subscribe(self.save_settings)

        Theme.scale = root.winfo_fpixels("1i") / 96.0
        width = Theme.px(self.CONTENT_WIDTH)

        root.title(APP_NAME)
        root.configure(bg=Theme.BACKGROUND)
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", self.close)

        body = tk.Frame(root, bg=Theme.BACKGROUND, padx=Theme.px(16), pady=Theme.px(16))
        body.pack()

        tk.Label(body, text=APP_NAME, font=Theme.APP_TITLE, fg=Theme.TEXT,
                 bg=Theme.BACKGROUND, anchor="w").pack(fill=tk.X)
        status = tk.Frame(body, bg=Theme.BACKGROUND)
        status.pack(fill=tk.X, pady=(Theme.px(4), Theme.px(14)))
        self.status_dot = tk.Label(status, text="●", font=Theme.BODY, bg=Theme.BACKGROUND)
        self.status_dot.pack(side=tk.LEFT, padx=(0, Theme.px(4)))
        self.status_text = tk.Label(status, font=Theme.BODY, fg=Theme.MUTED, bg=Theme.BACKGROUND)
        self.status_text.pack(side=tk.LEFT)

        self.hotkey_warning = tk.Label(
            body, text="F6 is already used by another program; use the toggle in this window instead.",
            font=Theme.SMALL, fg=Theme.WARNING, bg=Theme.BACKGROUND, wraplength=width, justify="left", anchor="w")

        for f in self.features:
            FeatureCard(body, f, width).pack(fill=tk.X, pady=(0, Theme.px(10)))

        tk.Label(body, text="Settings are saved automatically. The game returns to normal when this window closes.",
                 font=Theme.SMALL, fg=Theme.MUTED, bg=Theme.BACKGROUND, wraplength=width, justify="left",
                 anchor="w").pack(fill=tk.X, pady=(Theme.px(4), 0))

        self.hotkeys = HotkeyListener({HOTKEY_TOGGLE_TRACTOR: win32.VK_F6})
        self.hotkeys.start()
        if HOTKEY_TOGGLE_TRACTOR in self.hotkeys.failed:
            self.hotkey_warning.pack(fill=tk.X, after=status, pady=(0, Theme.px(10)))

        self.update_status()
        self.poll()
        self.check_hotkeys()

    def poll(self) -> None:
        if self.game is not None and self.game.has_exited:
            for f in self.features:
                f.detach()
            self.game.close()
            self.game = None

        if self.game is None:
            self.game = GameProcess.try_attach()
            if self.game is not None:
                for f in self.features:
                    f.attach(self.game)

        self.update_status()
        self.root.after(POLL_MS, self.poll)

    def check_hotkeys(self) -> None:
        try:
            while True:
                if self.hotkeys.pressed.get_nowait() == HOTKEY_TOGGLE_TRACTOR:
                    self.tractor_speed.set_enabled(not self.tractor_speed.enabled)
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except queue.Empty:
            pass
        self.root.after(100, self.check_hotkeys)

    def update_status(self) -> None:
        if self.game is not None:
            self.status_dot.config(fg=Theme.ACCENT)
            self.status_text.config(text=f"Connected to Farm Together 2 (PID {self.game.pid})")
        else:
            self.status_dot.config(fg=Theme.WARNING)
            self.status_text.config(text="Waiting for Farm Together 2… it will connect automatically.")

    def save_settings(self) -> None:
        for f in self.features:
            f.save(self.settings.feature(f.key))
        self.settings.save()

    def close(self) -> None:
        self.hotkeys.stop()
        self.save_settings()
        for f in self.features:
            f.release()
        if self.game is not None:
            self.game.close()
            self.game = None
        self.root.destroy()
