#!/usr/bin/env python3
"""Writes down every console window that appears, and who owns it.

Windows will not tell a normal user which process started: the Security log
needs an administrator and auditing switched on. A window is visible without
any of that. Polling the desktop costs no process at all, which matters when
the thing under investigation is process count."""
import ctypes
import ctypes.wintypes as w
import os
import sys
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi

PROC = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
QUERY = 0x1000
CONSOLES = ("ConsoleWindowClass", "CASCADIA_HOSTING_WINDOW_CLASS",
            "PseudoConsoleWindow", "Windows.UI.Core.CoreWindow")


def name_of(pid):
    handle = kernel32.OpenProcess(QUERY, False, pid)
    if not handle:
        return "?"
    buf = ctypes.create_unicode_buffer(1024)
    size = w.DWORD(1024)
    ok = kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size))
    kernel32.CloseHandle(handle)
    return os.path.basename(buf.value) if ok else "?"


class ENTRY(ctypes.Structure):
    _fields_ = [("dwSize", w.DWORD), ("cntUsage", w.DWORD),
                ("th32ProcessID", w.DWORD), ("th32DefaultHeapID", ctypes.POINTER(w.ULONG)),
                ("th32ModuleID", w.DWORD), ("cntThreads", w.DWORD),
                ("th32ParentProcessID", w.DWORD), ("pcPriClassBase", w.LONG),
                ("dwFlags", w.DWORD), ("szExeFile", ctypes.c_char * 260)]


def parents():
    """Who started whom, from the process table itself.

    A snapshot carries the parent id, and reading it costs no process. Asking
    PowerShell the same question would add one to the count under test."""
    snap = kernel32.CreateToolhelp32Snapshot(2, 0)
    tree = {}
    entry = ENTRY()
    entry.dwSize = ctypes.sizeof(ENTRY)
    if kernel32.Process32First(snap, ctypes.byref(entry)):
        while True:
            tree[entry.th32ProcessID] = (entry.th32ParentProcessID,
                                         entry.szExeFile.decode(errors="replace"))
            if not kernel32.Process32Next(snap, ctypes.byref(entry)):
                break
    kernel32.CloseHandle(snap)
    return tree


def lineage(pid, tree, depth=6):
    chain = []
    while pid in tree and depth > 0:
        up, name = tree[pid]
        chain.append(f"{name}({pid})")
        pid, depth = up, depth - 1
    return " < ".join(chain)


def shot():
    found = {}

    def visit(hwnd, _):
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if cls.value not in CONSOLES:
            return True
        pid = w.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        title = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, title, 256)
        found[hwnd] = (cls.value, pid.value, title.value)
        return True

    user32.EnumWindows(PROC(visit), 0)
    return found


def main():
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    out = sys.argv[2] if len(sys.argv) > 2 else "windows.log"
    known = shot()
    end = time.monotonic() + seconds
    with open(out, "a", encoding="utf-8") as handle:
        handle.write(f"--- watching {seconds}s from {time.strftime('%H:%M:%S')}\n")
        handle.flush()
        while time.monotonic() < end:
            now = shot()
            for hwnd, what in now.items():
                if hwnd in known:
                    continue
                cls, pid, title = what
                handle.write(f"{time.strftime('%H:%M:%S')} {cls} pid={pid} "
                             f"{name_of(pid)} {title!r}\n")
                handle.flush()
            known = now
            time.sleep(0.03)
    return 0


if __name__ == "__main__":
    sys.exit(main())
