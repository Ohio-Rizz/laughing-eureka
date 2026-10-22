"""
Clipboard Auto Typer for Windows — one file, no extra packages.

Run:
  python "%USERPROFILE%\\Desktop\\Clipboard_Auto_Typer.py"

Copy text normally with Ctrl+C, click the destination field, then press F8.
The script types the clipboard text one character at a time with a small delay.
Press Esc to stop typing. Press Ctrl+C in this console to exit.
"""

import ctypes
import os
import time
from ctypes import wintypes

if os.name != "nt":
    raise SystemExit("This script only works on Windows.")

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

MOD_NOREPEAT = 0x4000
VK_F8 = 0x77
VK_ESCAPE = 0x1B
WM_HOTKEY = 0x0312
HOTKEY_F8 = 1
HOTKEY_ESC = 2

CF_UNICODETEXT = 13
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

# Small pause between characters (milliseconds). Change to 10 for faster typing,
# or 25–40 for slower typing.
DELAY_MS = 15

user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = ctypes.c_int
user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE
user32.CloseClipboard.restype = wintypes.BOOL
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = wintypes.BOOL
user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_size_t]
user32.keybd_event.restype = None

stop_typing = False


def get_clipboard_text():
    for _ in range(10):
        if user32.OpenClipboard(None):
            break
        time.sleep(0.05)
    else:
        raise RuntimeError("Could not open the clipboard. Try again.")

    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            raise RuntimeError("Clipboard has no plain text. Copy text first.")
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            raise RuntimeError("Could not read clipboard text.")
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def type_char(char):
    # Unicode key events support text beyond the current keyboard layout.
    code = ord(char)
    user32.keybd_event(0, code & 0xFF, KEYEVENTF_UNICODE, 0)
    user32.keybd_event(0, code & 0xFF, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0)


def type_clipboard():
    global stop_typing
    stop_typing = False
    try:
        text = get_clipboard_text()
        if not text:
            print("Clipboard text is empty.")
            return

        print(f"Typing {len(text)} characters at {DELAY_MS} ms per character. Press Esc to stop.")
        for char in text:
            if stop_typing:
                print("Stopped.")
                break
            if char == "\r":
                continue
            if char == "\n":
                type_char("\r")
            else:
                type_char(char)
            time.sleep(DELAY_MS / 1000)
        else:
            print("Finished typing.")
    except Exception as exc:
        print(f"Typing error: {exc}")


def main():
    global stop_typing
    if not user32.RegisterHotKey(None, HOTKEY_F8, MOD_NOREPEAT, VK_F8):
        raise SystemExit("Could not register F8. Another app may already be using it.")
    if not user32.RegisterHotKey(None, HOTKEY_ESC, MOD_NOREPEAT, VK_ESCAPE):
        user32.UnregisterHotKey(None, HOTKEY_F8)
        raise SystemExit("Could not register Esc as the stop hotkey.")

    print("Clipboard Auto Typer is running.")
    print("Copy text, click the destination field, then press F8.")
    print(f"Typing delay: {DELAY_MS} ms per character.")
    print("Press Esc to stop typing. Press Ctrl+C in this console to exit.")
    message = wintypes.MSG()
    try:
        while True:
            result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
            if result <= 0:
                break
            if message.message == WM_HOTKEY:
                if message.wParam == HOTKEY_F8:
                    # Keep typing synchronous so hotkeys cannot start overlapping runs.
                    type_clipboard()
                elif message.wParam == HOTKEY_ESC:
                    stop_typing = True
    except KeyboardInterrupt:
        pass
    finally:
        user32.UnregisterHotKey(None, HOTKEY_F8)
        user32.UnregisterHotKey(None, HOTKEY_ESC)
        print("Clipboard Auto Typer closed.")


if __name__ == "__main__":
    main()
