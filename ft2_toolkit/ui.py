from __future__ import annotations

import queue
import tkinter as tk
import winsound

from . import win32
from .farm import ACTIONS, InstantAction
from .features import Feature, Slider, create_all
from .features.tractor_speed import TractorSpeed
from .game import GameProcess
from .hotkey import HotkeyListener
from .session import Session, detect
from .settings import Settings

APP_NAME = "FT2 Toolkit"
POLL_MS = 500
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
    TAB_ACTIVE = "#404249"

    BODY = ("Segoe UI", 10)
    SMALL = ("Segoe UI", 9)
    TAB = ("Segoe UI Semibold", 10)
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


class StepSlider(tk.Frame):
    def __init__(self, parent, feature: Feature, slider: Slider, guard):
        super().__init__(parent, bg=Theme.CARD)
        self.feature = feature
        self.slider = slider
        self.guard = guard
        if slider.label:
            tk.Label(self, text=slider.label, font=Theme.SMALL, fg=Theme.MUTED, bg=Theme.CARD,
                     width=8, anchor="w").pack(side=tk.LEFT)
        self.scale = tk.Scale(
            self, from_=0, to=len(slider.steps) - 1, resolution=1, orient=tk.HORIZONTAL, showvalue=False,
            bg=Theme.ACCENT, troughcolor=Theme.TRACK, activebackground=Theme.ACCENT_HOVER,
            highlightthickness=0, bd=0, sliderrelief=tk.FLAT, sliderlength=Theme.px(18), width=Theme.px(12),
            command=self._on_scale,
        )
        self.value = tk.Label(self, font=Theme.VALUE_FONT, fg=Theme.TEXT, bg=Theme.CARD, width=6, anchor="e")
        self.scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.value.pack(side=tk.RIGHT)
        feature.subscribe(self.sync)
        self.sync()

    def _on_scale(self, raw) -> None:
        self.guard()
        self.feature.set_slider(self.slider.key, self.slider.steps[int(float(raw))])

    def sync(self) -> None:
        index = self.slider.steps.index(self.slider.value)
        if int(self.scale.get()) != index:
            self.scale.set(index)
        self.value.config(text=self.slider.fmt.format(self.slider.value))


class FeatureCard(tk.Frame):
    def __init__(self, parent, feature: Feature, width: int, guard):
        super().__init__(parent, bg=Theme.CARD, padx=Theme.px(14), pady=Theme.px(10))
        self.feature = feature
        self.guard = guard
        self.columnconfigure(0, weight=1)

        tk.Label(self, text=feature.title, font=Theme.CARD_TITLE, fg=Theme.TEXT, bg=Theme.CARD,
                 anchor="w").grid(row=0, column=0, sticky="w")
        tk.Label(self, text=feature.description, font=Theme.SMALL, fg=Theme.MUTED, bg=Theme.CARD,
                 wraplength=width - Theme.px(28 + 60), justify="left", anchor="w").grid(
            row=1, column=0, sticky="w", pady=(Theme.px(2), 0))
        self.toggle = ToggleSwitch(self, self._toggle)
        self.toggle.grid(row=0, column=1, rowspan=2, sticky="ne", padx=(Theme.px(8), 0))

        row = 2
        for slider in feature.sliders:
            StepSlider(self, feature, slider, guard).grid(row=row, column=0, columnspan=2, sticky="ew",
                                                          pady=(Theme.px(6), 0))
            row += 1

        self.state = tk.Label(self, font=Theme.SMALL, bg=Theme.CARD, anchor="w", justify="left",
                              wraplength=width - Theme.px(28))
        self.state.grid(row=row, column=0, columnspan=2, sticky="w", pady=(Theme.px(6), 0))
        row += 1

        if feature.hotkey_hint:
            tk.Label(self, text=feature.hotkey_hint, font=Theme.SMALL, fg=Theme.MUTED, bg=Theme.CARD,
                     anchor="w").grid(row=row, column=0, columnspan=2, sticky="w")

        feature.subscribe(self.sync)
        self.sync()

    def _toggle(self, value: bool) -> None:
        self.guard()
        self.feature.set_enabled(value)

    def sync(self) -> None:
        f = self.feature
        self.toggle.set(f.enabled)
        if f.error:
            text, color = "⚠ " + f.error, Theme.ERROR
        elif f.waiting:
            text, color = "Waiting for the game to finish loading…", Theme.WARNING
        elif not f.is_attached:
            text, color = ("On · applies on a single-player farm", Theme.WARNING) if f.enabled else ("Off", Theme.MUTED)
        elif f.enabled:
            text, color = "On · applied to the game", Theme.ACCENT
        else:
            text, color = "Off · game unchanged", Theme.MUTED
        self.state.config(text=text, fg=color)


class InstantCard(tk.Frame):
    def __init__(self, parent, width: int, run):
        super().__init__(parent, bg=Theme.CARD, padx=Theme.px(14), pady=Theme.px(10))
        tk.Label(self, text="Instant grow", font=Theme.CARD_TITLE, fg=Theme.TEXT, bg=Theme.CARD,
                 anchor="w").pack(fill=tk.X)
        tk.Label(self, text="Makes everything of that kind on your farm ready to harvest right away.",
                 font=Theme.SMALL, fg=Theme.MUTED, bg=Theme.CARD, wraplength=width - Theme.px(28),
                 justify="left", anchor="w").pack(fill=tk.X, pady=(Theme.px(2), Theme.px(8)))
        grid = tk.Frame(self, bg=Theme.CARD)
        grid.pack(fill=tk.X)
        grid.columnconfigure((0, 1), weight=1, uniform="buttons")
        self.result = tk.Label(self, text="", font=Theme.SMALL, fg=Theme.MUTED, bg=Theme.CARD, anchor="w",
                               wraplength=width - Theme.px(28), justify="left")
        for index, action in enumerate(ACTIONS):
            button = tk.Label(grid, text=action.label, font=Theme.TAB, fg="white", bg=Theme.ACCENT,
                              pady=Theme.px(8), cursor="hand2")
            button.grid(row=index // 2, column=index % 2, sticky="ew", padx=Theme.px(3), pady=Theme.px(3))
            button.bind("<Button-1>", lambda e, a=action: self.result.config(**run(a)))
            button.bind("<Enter>", lambda e, b=button: b.config(bg=Theme.ACCENT_HOVER))
            button.bind("<Leave>", lambda e, b=button: b.config(bg=Theme.ACCENT))
        self.result.pack(fill=tk.X, pady=(Theme.px(8), 0))


class MainWindow:
    CONTENT_WIDTH = 460

    def __init__(self, root: tk.Tk):
        self.root = root
        self.settings = Settings.load()
        self.tabs = create_all()
        self.features = [f for _, features in self.tabs for f in features]
        self.tractor_speed = next(f for f in self.features if isinstance(f, TractorSpeed))
        self.game: GameProcess | None = None
        self.session = Session.NO_FARM

        for f in self.features:
            f.load(self.settings.feature(f.key))
            f.subscribe(self.save_settings)

        Theme.scale = root.winfo_fpixels("1i") / 96.0
        width = Theme.px(self.CONTENT_WIDTH)

        root.title(APP_NAME)
        root.configure(bg=Theme.BACKGROUND)
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", self.close)

        body = tk.Frame(root, bg=Theme.BACKGROUND, padx=Theme.px(16), pady=Theme.px(14))
        body.pack()

        tk.Label(body, text=APP_NAME, font=Theme.APP_TITLE, fg=Theme.TEXT,
                 bg=Theme.BACKGROUND, anchor="w").pack(fill=tk.X)
        status = tk.Frame(body, bg=Theme.BACKGROUND)
        status.pack(fill=tk.X, pady=(Theme.px(2), Theme.px(10)))
        self.status_dot = tk.Label(status, text="●", font=Theme.BODY, bg=Theme.BACKGROUND)
        self.status_dot.pack(side=tk.LEFT, padx=(0, Theme.px(4)))
        self.status_text = tk.Label(status, font=Theme.BODY, fg=Theme.MUTED, bg=Theme.BACKGROUND)
        self.status_text.pack(side=tk.LEFT)

        self.hotkey_warning = tk.Label(
            body, text="F6 is already used by another program; use the toggle in this window instead.",
            font=Theme.SMALL, fg=Theme.WARNING, bg=Theme.BACKGROUND, wraplength=width, justify="left", anchor="w")

        tab_bar = tk.Frame(body, bg=Theme.BACKGROUND)
        tab_bar.pack(fill=tk.X, pady=(0, Theme.px(8)))
        pages = tk.Frame(body, bg=Theme.BACKGROUND)
        pages.pack(fill=tk.BOTH)
        pages.columnconfigure(0, weight=1)
        pages.rowconfigure(0, weight=1)
        self.tab_buttons: list[tk.Label] = []
        self.pages: list[tk.Frame] = []
        for index, (name, features) in enumerate(self.tabs + [("Farm", None)]):
            button = tk.Label(tab_bar, text=name, font=Theme.TAB, fg=Theme.MUTED, bg=Theme.BACKGROUND,
                              padx=Theme.px(10), pady=Theme.px(5), cursor="hand2")
            button.pack(side=tk.LEFT, padx=(0, Theme.px(4)))
            button.bind("<Button-1>", lambda e, i=index: self.show_tab(i))
            self.tab_buttons.append(button)
            page = tk.Frame(pages, bg=Theme.BACKGROUND, width=width)
            page.grid(row=0, column=0, sticky="nsew")
            if features is None:
                InstantCard(page, width, self.run_action).pack(fill=tk.X, pady=(0, Theme.px(8)))
            for f in features or ():
                FeatureCard(page, f, width, self.sync_session).pack(fill=tk.X, pady=(0, Theme.px(8)))
            self.pages.append(page)

        tk.Label(body, text="Single-player only: everything pauses in online and co-op sessions. Settings are saved "
                            "automatically and the game returns to normal when this window closes.",
                 font=Theme.SMALL, fg=Theme.MUTED, bg=Theme.BACKGROUND, wraplength=width, justify="left",
                 anchor="w").pack(fill=tk.X, pady=(Theme.px(2), 0))

        self.hotkeys = HotkeyListener({HOTKEY_TOGGLE_TRACTOR: win32.VK_F6})
        self.hotkeys.start()
        if HOTKEY_TOGGLE_TRACTOR in self.hotkeys.failed:
            self.hotkey_warning.pack(fill=tk.X, after=status, pady=(0, Theme.px(8)))

        self.show_tab(0)
        self.update_status()
        self.poll()
        self.check_hotkeys()

    def run_action(self, action: InstantAction) -> dict:
        session = self.sync_session()
        if session is Session.MULTIPLAYER:
            return {"text": "Not available in online or co-op sessions.", "fg": Theme.ERROR}
        if session is not Session.SOLO:
            return {"text": "Start Farm Together 2 and load a single-player farm first.", "fg": Theme.WARNING}
        try:
            return {"text": action(self.game), "fg": Theme.ACCENT}
        except Exception as e:
            return {"text": "⚠ " + str(e), "fg": Theme.ERROR}

    def show_tab(self, index: int) -> None:
        for i, button in enumerate(self.tab_buttons):
            active = i == index
            button.config(bg=Theme.TAB_ACTIVE if active else Theme.BACKGROUND,
                          fg=Theme.TEXT if active else Theme.MUTED)
        self.pages[index].tkraise()

    def sync_session(self) -> Session:
        if self.game is not None and self.game.has_exited:
            self.drop_game()
        session = detect(self.game) if self.game is not None else Session.NO_FARM
        if session is not self.session:
            previous, self.session = self.session, session
            if session is Session.SOLO:
                for f in self.features:
                    f.attach(self.game)
            elif previous is Session.SOLO:
                self.pause()
            self.update_status()
        return session

    def pause(self) -> None:
        for action in ACTIONS:
            try:
                action.release(self.game)
            except Exception:
                pass
        for f in self.features:
            f.suspend()

    def drop_game(self) -> None:
        for f in self.features:
            f.detach()
        self.game.close()
        self.game = None
        self.session = Session.NO_FARM

    def poll(self) -> None:
        if self.game is None:
            self.game = GameProcess.try_attach()
        if self.sync_session() is Session.SOLO:
            for f in self.features:
                if f.waiting:
                    f.attach(self.game)

        self.update_status()
        self.root.after(POLL_MS, self.poll)

    def check_hotkeys(self) -> None:
        try:
            while True:
                if self.hotkeys.pressed.get_nowait() == HOTKEY_TOGGLE_TRACTOR:
                    self.sync_session()
                    self.tractor_speed.set_enabled(not self.tractor_speed.enabled)
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except queue.Empty:
            pass
        self.root.after(100, self.check_hotkeys)

    def update_status(self) -> None:
        if self.game is None:
            color, text = Theme.WARNING, "Waiting for Farm Together 2… it will connect automatically."
        elif self.session is Session.SOLO:
            color, text = Theme.ACCENT, f"Connected to a single-player farm (PID {self.game.pid})"
        elif self.session is Session.MULTIPLAYER:
            color, text = Theme.ERROR, "Online or co-op session detected · everything is paused"
        else:
            color, text = Theme.WARNING, "Connected · waiting for a single-player farm"
        self.status_dot.config(fg=color)
        self.status_text.config(text=text)

    def save_settings(self) -> None:
        for f in self.features:
            f.save(self.settings.feature(f.key))
        self.settings.save()

    def close(self) -> None:
        self.hotkeys.stop()
        self.save_settings()
        if self.game is not None:
            for action in ACTIONS:
                try:
                    action.release(self.game)
                except Exception:
                    pass
        for f in self.features:
            f.release()
        if self.game is not None:
            self.game.close()
            self.game = None
        self.root.destroy()
