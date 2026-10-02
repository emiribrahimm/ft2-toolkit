from __future__ import annotations

import ctypes
import queue
import threading
from ctypes import wintypes

from . import win32


class HotkeyListener:
    def __init__(self, hotkeys: dict[int, int]):
        self._hotkeys = hotkeys
        self.pressed: queue.Queue[int] = queue.Queue()
        self.failed: list[int] = []
        self._thread_id = 0
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, name="hotkeys", daemon=True)

    def start(self) -> None:
        self._thread.start()
        self._ready.wait(timeout=2)

    def stop(self) -> None:
        if self._thread_id:
            win32.PostThreadMessageW(self._thread_id, win32.WM_QUIT, 0, 0)
            self._thread.join(timeout=2)

    def _run(self) -> None:
        self._thread_id = win32.GetCurrentThreadId()
        registered = []
        for hotkey_id, vk in self._hotkeys.items():
            if win32.RegisterHotKey(None, hotkey_id, win32.MOD_NOREPEAT, vk):
                registered.append(hotkey_id)
            else:
                self.failed.append(hotkey_id)
        self._ready.set()

        msg = wintypes.MSG()
        try:
            while win32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == win32.WM_HOTKEY:
                    self.pressed.put(msg.wParam)
        finally:
            for hotkey_id in registered:
                win32.UnregisterHotKey(None, hotkey_id)
