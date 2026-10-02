from __future__ import annotations

import ctypes
import struct
import sys
import tkinter as tk
import traceback
from tkinter import messagebox

TITLE = "FT2 Toolkit"


def _message(kind, text: str) -> None:
    root = tk.Tk()
    root.withdraw()
    kind(TITLE, text)
    root.destroy()


def main() -> None:
    if sys.platform != "win32":
        print("FT2 Toolkit only runs on Windows.")
        return
    if struct.calcsize("P") != 8:
        _message(messagebox.showerror, "64-bit Python is required because the game is a 64-bit process.")
        return

    from . import win32
    from .ui import MainWindow

    mutex = win32.CreateMutexW(None, True, "Local\\FT2Toolkit")
    if ctypes.get_last_error() == win32.ERROR_ALREADY_EXISTS:
        _message(messagebox.showinfo, "FT2 Toolkit is already running.")
        return

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass

    root = tk.Tk()

    def report(exc_type, exc, tb):
        messagebox.showerror(TITLE, "Unexpected error:\n\n" + "".join(traceback.format_exception(exc_type, exc, tb)))

    root.report_callback_exception = report
    try:
        MainWindow(root)
    except Exception:
        report(*sys.exc_info())
        root.destroy()
        return
    root.mainloop()
    win32.CloseHandle(mutex)
