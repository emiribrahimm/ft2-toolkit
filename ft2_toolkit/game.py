from __future__ import annotations

import ctypes
import struct
from ctypes import wintypes

from . import win32

PROCESS_NAME = "FarmTogether2.exe"
MODULE_NAME = "GameAssembly.dll"


class GameError(Exception):
    pass


def _find_pids(exe_name: str) -> list[int]:
    snapshot = win32.CreateToolhelp32Snapshot(win32.TH32CS_SNAPPROCESS, 0)
    if snapshot == win32.INVALID_HANDLE_VALUE:
        return []
    try:
        entry = win32.PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        pids = []
        ok = win32.Process32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            if entry.szExeFile.lower() == exe_name.lower():
                pids.append(entry.th32ProcessID)
            ok = win32.Process32NextW(snapshot, ctypes.byref(entry))
        return pids
    finally:
        win32.CloseHandle(snapshot)


def _module_base(pid: int, module_name: str) -> int | None:
    flags = win32.TH32CS_SNAPMODULE | win32.TH32CS_SNAPMODULE32
    snapshot = win32.CreateToolhelp32Snapshot(flags, pid)
    if snapshot == win32.INVALID_HANDLE_VALUE:
        return None
    try:
        entry = win32.MODULEENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        ok = win32.Module32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            if entry.szModule.lower() == module_name.lower():
                return entry.modBaseAddr
            ok = win32.Module32NextW(snapshot, ctypes.byref(entry))
        return None
    finally:
        win32.CloseHandle(snapshot)


class GameProcess:
    def __init__(self, pid: int, handle: int, base: int):
        self.pid = pid
        self.base = base
        self._handle = handle

    @classmethod
    def try_attach(cls) -> GameProcess | None:
        access = (win32.PROCESS_VM_READ | win32.PROCESS_VM_WRITE |
                  win32.PROCESS_VM_OPERATION | win32.PROCESS_QUERY_INFORMATION)
        for pid in _find_pids(PROCESS_NAME):
            base = _module_base(pid, MODULE_NAME)
            if base is None:
                continue
            handle = win32.OpenProcess(access, False, pid)
            if handle:
                return cls(pid, handle, base)
        return None

    @property
    def has_exited(self) -> bool:
        code = wintypes.DWORD()
        if not win32.GetExitCodeProcess(self._handle, ctypes.byref(code)):
            return True
        return code.value != win32.STILL_ACTIVE

    def read(self, rva: int, size: int) -> bytes:
        buffer = ctypes.create_string_buffer(size)
        read = ctypes.c_size_t()
        address = self.base + rva
        if not win32.ReadProcessMemory(self._handle, address, buffer, size, ctypes.byref(read)) or read.value != size:
            raise GameError(f"Failed to read memory at 0x{address:X} (error {ctypes.get_last_error()}).")
        return buffer.raw

    def read_float(self, rva: int) -> float:
        return struct.unpack("<f", self.read(rva, 4))[0]

    def read_int32(self, rva: int) -> int:
        return struct.unpack("<i", self.read(rva, 4))[0]

    def write(self, rva: int, data: bytes) -> None:
        address = self.base + rva
        old = wintypes.DWORD()
        if not win32.VirtualProtectEx(self._handle, address, len(data), win32.PAGE_EXECUTE_READWRITE, ctypes.byref(old)):
            raise GameError(f"Failed to change memory protection at 0x{address:X} (error {ctypes.get_last_error()}).")
        try:
            written = ctypes.c_size_t()
            if not win32.WriteProcessMemory(self._handle, address, data, len(data), ctypes.byref(written)) \
                    or written.value != len(data):
                raise GameError(f"Failed to write memory at 0x{address:X} (error {ctypes.get_last_error()}).")
        finally:
            win32.VirtualProtectEx(self._handle, address, len(data), old.value, ctypes.byref(wintypes.DWORD()))
        win32.FlushInstructionCache(self._handle, address, len(data))

    def write_int32(self, rva: int, value: int) -> None:
        self.write(rva, struct.pack("<i", value))

    def close(self) -> None:
        if self._handle:
            win32.CloseHandle(self._handle)
            self._handle = None
