import ctypes
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)

PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_QUERY_INFORMATION = 0x0400
PAGE_EXECUTE_READWRITE = 0x40
STILL_ACTIVE = 259

TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPTHREAD = 0x00000004
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

THREAD_SUSPEND_RESUME = 0x0002
THREAD_GET_CONTEXT = 0x0008
CONTEXT_CONTROL = 0x00100001
CONTEXT_SIZE = 0x4D0
CONTEXT_FLAGS_OFFSET = 0x30
CONTEXT_RIP_OFFSET = 0xF8

ERROR_ALREADY_EXISTS = 183

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_NOREPEAT = 0x4000
VK_F6 = 0x75


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD),
        ("modBaseAddr", ctypes.c_void_p),
        ("modBaseSize", wintypes.DWORD),
        ("hModule", wintypes.HMODULE),
        ("szModule", wintypes.WCHAR * 256),
        ("szExePath", wintypes.WCHAR * 260),
    ]


class THREADENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ThreadID", wintypes.DWORD),
        ("th32OwnerProcessID", wintypes.DWORD),
        ("tpBasePri", wintypes.LONG),
        ("tpDeltaPri", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
    ]


def _fn(dll, name, restype, *argtypes):
    f = getattr(dll, name)
    f.restype = restype
    f.argtypes = argtypes
    return f


SIZE_T_P = ctypes.POINTER(ctypes.c_size_t)

OpenProcess = _fn(kernel32, "OpenProcess", wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
CloseHandle = _fn(kernel32, "CloseHandle", wintypes.BOOL, wintypes.HANDLE)
GetExitCodeProcess = _fn(kernel32, "GetExitCodeProcess", wintypes.BOOL, wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
ReadProcessMemory = _fn(kernel32, "ReadProcessMemory", wintypes.BOOL,
                        wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID, ctypes.c_size_t, SIZE_T_P)
WriteProcessMemory = _fn(kernel32, "WriteProcessMemory", wintypes.BOOL,
                         wintypes.HANDLE, wintypes.LPVOID, wintypes.LPCVOID, ctypes.c_size_t, SIZE_T_P)
VirtualProtectEx = _fn(kernel32, "VirtualProtectEx", wintypes.BOOL,
                       wintypes.HANDLE, wintypes.LPVOID, ctypes.c_size_t, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD))
FlushInstructionCache = _fn(kernel32, "FlushInstructionCache", wintypes.BOOL,
                            wintypes.HANDLE, wintypes.LPCVOID, ctypes.c_size_t)

CreateToolhelp32Snapshot = _fn(kernel32, "CreateToolhelp32Snapshot", wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD)
Process32FirstW = _fn(kernel32, "Process32FirstW", wintypes.BOOL, wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W))
Process32NextW = _fn(kernel32, "Process32NextW", wintypes.BOOL, wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W))
Module32FirstW = _fn(kernel32, "Module32FirstW", wintypes.BOOL, wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W))
Module32NextW = _fn(kernel32, "Module32NextW", wintypes.BOOL, wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W))

Thread32First = _fn(kernel32, "Thread32First", wintypes.BOOL, wintypes.HANDLE, ctypes.POINTER(THREADENTRY32))
Thread32Next = _fn(kernel32, "Thread32Next", wintypes.BOOL, wintypes.HANDLE, ctypes.POINTER(THREADENTRY32))
OpenThread = _fn(kernel32, "OpenThread", wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
SuspendThread = _fn(kernel32, "SuspendThread", wintypes.DWORD, wintypes.HANDLE)
ResumeThread = _fn(kernel32, "ResumeThread", wintypes.DWORD, wintypes.HANDLE)
GetThreadContext = _fn(kernel32, "GetThreadContext", wintypes.BOOL, wintypes.HANDLE, ctypes.c_void_p)

CreateMutexW = _fn(kernel32, "CreateMutexW", wintypes.HANDLE, wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
GetCurrentThreadId = _fn(kernel32, "GetCurrentThreadId", wintypes.DWORD)

RegisterHotKey = _fn(user32, "RegisterHotKey", wintypes.BOOL, wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT)
UnregisterHotKey = _fn(user32, "UnregisterHotKey", wintypes.BOOL, wintypes.HWND, ctypes.c_int)
GetMessageW = _fn(user32, "GetMessageW", ctypes.c_int, ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT)
PostThreadMessageW = _fn(user32, "PostThreadMessageW", wintypes.BOOL,
                         wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
