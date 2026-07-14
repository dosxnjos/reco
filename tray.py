"""Windows tray icon with hover-to-show — pure ctypes, no extra dependencies.

Why not pystray: it gives you an icon and a menu, but no hover event, and hover
is the whole point here (rest the mouse on the icon → the compact Reco window
appears over the tray, ready to stop/start a recording).

The one non-obvious piece is `Shell_NotifyIconGetRect`: we need the icon's screen
rectangle so the "keep the window open" hot zone can be the union of the icon and
the window. WM_MOUSEMOVE stops firing once the cursor stops moving, so a cursor
resting *on the icon* would otherwise dismiss the window it just opened.

The hidden message window lives on the Tk thread on purpose: Tk's event loop
already pumps every message posted to the thread, so our WndProc gets called
without a second message loop.
"""

import ctypes
from ctypes import wintypes
from pathlib import Path

user32   = ctypes.WinDLL("user32",   use_last_error=True)
shell32  = ctypes.WinDLL("shell32",  use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT,
                             wintypes.WPARAM, wintypes.LPARAM)

WM_DESTROY      = 0x0002
WM_COMMAND      = 0x0111
WM_MOUSEMOVE    = 0x0200
WM_LBUTTONUP    = 0x0202
WM_RBUTTONUP    = 0x0205
WM_TRAY         = 0x8000 + 1          # WM_APP + 1 (our callback message)

NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP  = 0x01, 0x02, 0x04
IMAGE_ICON      = 1
LR_LOADFROMFILE = 0x0010
MF_STRING       = 0x0000
MF_SEPARATOR    = 0x0800
TPM_RIGHTBUTTON = 0x0002
TPM_RETURNCMD   = 0x0100

ID_OPEN, ID_QUIT, ID_REC, ID_PAUSE = 1001, 1002, 1003, 1004


class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                ("right", wintypes.LONG), ("bottom", wintypes.LONG)]


class GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD), ("Data4", ctypes.c_byte * 8)]


class NOTIFYICONIDENTIFIER(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND),
                ("uID", wintypes.UINT), ("guidItem", GUID)]


class NOTIFYICONDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT), ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT), ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128), ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD), ("szInfo", wintypes.WCHAR * 256),
        ("uVersion", wintypes.UINT), ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD), ("guidItem", GUID),
        ("hBalloonIcon", wintypes.HICON),
    ]


class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT), ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR),
    ]


user32.DefWindowProcW.restype  = LRESULT
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT,
                                  wintypes.WPARAM, wintypes.LPARAM]
shell32.Shell_NotifyIconGetRect.argtypes = [ctypes.POINTER(NOTIFYICONIDENTIFIER),
                                            ctypes.POINTER(RECT)]
shell32.Shell_NotifyIconGetRect.restype  = ctypes.c_long


class TrayError(Exception):
    pass


class Tray:
    """A tray icon whose hover/click/menu events call back into the app.

    on_hover()  — cursor entered the icon
    on_click()  — left click (open + focus)
    on_open()   — "Abrir" from the context menu
    on_quit()   — "Sair" from the context menu
    on_record() — "Gravar"/"Parar" from the context menu
    rec_label() — returns the current label for that item (record vs stop)
    """

    def __init__(self, icon_paths: dict, tooltip: str, menu_labels: dict,
                 on_hover=None, on_click=None, on_open=None, on_quit=None,
                 on_record=None, rec_label=None, on_pause=None, pause_label=None):
        self._icons = {}
        self._on_hover, self._on_click = on_hover, on_click
        self._on_open, self._on_quit   = on_open, on_quit
        self._on_record, self._rec_label = on_record, rec_label
        self._on_pause, self._pause_label = on_pause, pause_label
        self._menu_labels = menu_labels
        self._state = "idle"
        self._tip = tooltip
        self.alive = False

        hinst = kernel32.GetModuleHandleW(None)
        # Keep a ref: ctypes callbacks are garbage-collected, and a freed WndProc
        # is a crash the moment Windows calls back into it.
        self._wndproc = WNDPROC(self._wnd_proc)
        cls = WNDCLASS()
        cls.lpfnWndProc   = self._wndproc
        cls.hInstance     = hinst
        cls.lpszClassName = "RecoTrayWindow"
        if not user32.RegisterClassW(ctypes.byref(cls)):
            err = ctypes.get_last_error()
            if err != 1410:                      # ERROR_CLASS_ALREADY_EXISTS
                raise TrayError(f"RegisterClassW failed ({err})")
        self._cls = cls                          # keep alive too

        self._hwnd = user32.CreateWindowExW(
            0, "RecoTrayWindow", "Reco", 0, 0, 0, 0, 0, None, None, hinst, None)
        if not self._hwnd:
            raise TrayError(f"CreateWindowExW failed ({ctypes.get_last_error()})")

        for state, path in icon_paths.items():
            h = user32.LoadImageW(None, str(path), IMAGE_ICON, 0, 0,
                                  LR_LOADFROMFILE)
            if h:
                self._icons[state] = h
        if not self._icons:
            raise TrayError("no tray icon could be loaded")

        # Explorer restarts (crash / update) drop every tray icon; it broadcasts
        # TaskbarCreated so apps can re-add theirs.
        self._wm_taskbar_created = user32.RegisterWindowMessageW("TaskbarCreated")

        self._uid = 1
        if not self._notify(NIM_ADD):
            raise TrayError("Shell_NotifyIcon(NIM_ADD) failed")
        self.alive = True

    # ── win32 plumbing ─────────────────────────────────────────────────────────
    def _nid(self, flags=NIF_MESSAGE | NIF_ICON | NIF_TIP) -> NOTIFYICONDATA:
        nid = NOTIFYICONDATA()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        nid.hWnd = self._hwnd
        nid.uID = self._uid
        nid.uFlags = flags
        nid.uCallbackMessage = WM_TRAY
        nid.hIcon = self._icons.get(self._state) or next(iter(self._icons.values()))
        nid.szTip = self._tip[:127]
        return nid

    def _notify(self, msg) -> bool:
        return bool(shell32.Shell_NotifyIconW(msg, ctypes.byref(self._nid())))

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        try:
            if msg == WM_TRAY:
                ev = lparam & 0xFFFF
                if ev == WM_MOUSEMOVE and self._on_hover:
                    self._on_hover()
                elif ev == WM_LBUTTONUP and self._on_click:
                    self._on_click()
                elif ev == WM_RBUTTONUP:
                    self._show_menu()
            elif msg == self._wm_taskbar_created and self.alive:
                self._notify(NIM_ADD)
            elif msg == WM_DESTROY:
                self.remove()
        except Exception:
            pass                    # never let an exception cross back into Win32
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _show_menu(self):
        menu = user32.CreatePopupMenu()
        # Record/Stop and Pause/Resume first: they're the reason you'd right-click
        # the icon mid-call. Labels are asked for as the menu opens, so they always
        # match the live state (record vs stop, pause vs resume).
        added = False
        for cid, provider, enabled in ((ID_REC, self._rec_label, self._on_record),
                                       (ID_PAUSE, self._pause_label, self._on_pause)):
            if not enabled:
                continue
            try:
                label = provider() if provider else None
            except Exception:
                label = None
            if label:
                user32.AppendMenuW(menu, MF_STRING, cid, label)
                added = True
        if added:
            user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(menu, MF_STRING, ID_OPEN,
                           self._menu_labels.get("open", "Abrir"))
        user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(menu, MF_STRING, ID_QUIT,
                           self._menu_labels.get("quit", "Sair"))
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        # Required by the docs: without it the menu wouldn't close on click-away.
        user32.SetForegroundWindow(self._hwnd)
        cmd = user32.TrackPopupMenu(menu, TPM_RIGHTBUTTON | TPM_RETURNCMD,
                                    pt.x, pt.y, 0, self._hwnd, None)
        user32.DestroyMenu(menu)
        if cmd == ID_REC and self._on_record:
            self._on_record()
        elif cmd == ID_PAUSE and self._on_pause:
            self._on_pause()
        elif cmd == ID_OPEN and self._on_open:
            self._on_open()
        elif cmd == ID_QUIT and self._on_quit:
            self._on_quit()

    # ── public API ─────────────────────────────────────────────────────────────
    def set_state(self, state: str):
        """'idle' | 'rec' — swaps the icon (red dot while recording)."""
        if state != self._state and state in self._icons:
            self._state = state
            self._notify(NIM_MODIFY)

    def set_tooltip(self, text: str):
        if text != self._tip:
            self._tip = text
            self._notify(NIM_MODIFY)

    def icon_rect(self):
        """Screen rect of the icon in *logical* pixels, or None.

        Shell_NotifyIconGetRect answers in physical pixels even for a DPI-unaware
        process, while Tk geometry and GetCursorPos speak virtualized (logical)
        ones. On a 125% display that's a 20% error — enough to park the window in
        the wrong place and to miss the icon's hot zone entirely."""
        nid = NOTIFYICONIDENTIFIER()
        nid.cbSize = ctypes.sizeof(NOTIFYICONIDENTIFIER)
        nid.hWnd = self._hwnd
        nid.uID = self._uid
        rc = RECT()
        if shell32.Shell_NotifyIconGetRect(ctypes.byref(nid), ctypes.byref(rc)) != 0:
            return None
        if rc.right <= rc.left or rc.bottom <= rc.top:
            return None
        s = dpi_scale()
        return tuple(int(v / s) for v in (rc.left, rc.top, rc.right, rc.bottom))

    def remove(self):
        if self.alive:
            self.alive = False
            try:
                shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(
                    self._nid(NIF_ICON)))
            except Exception:
                pass


class DEVMODE(ctypes.Structure):
    _fields_ = [("dmDeviceName", wintypes.WCHAR * 32), ("dmSpecVersion", wintypes.WORD),
                ("dmDriverVersion", wintypes.WORD), ("dmSize", wintypes.WORD),
                ("dmDriverExtra", wintypes.WORD), ("dmFields", wintypes.DWORD),
                ("dmPad", ctypes.c_byte * 16), ("dmColor", ctypes.c_short),
                ("dmDuplex", ctypes.c_short), ("dmYResolution", ctypes.c_short),
                ("dmTTOption", ctypes.c_short), ("dmCollate", ctypes.c_short),
                ("dmFormName", wintypes.WCHAR * 32), ("dmLogPixels", wintypes.WORD),
                ("dmBitsPerPel", wintypes.DWORD), ("dmPelsWidth", wintypes.DWORD),
                ("dmPelsHeight", wintypes.DWORD), ("dmDisplayFlags", wintypes.DWORD),
                ("dmDisplayFrequency", wintypes.DWORD), ("dmPad2", ctypes.c_byte * 36)]


def dpi_scale() -> float:
    """Physical ÷ logical width (1.25 on a 125% display, 1.0 if DPI-aware)."""
    try:
        dm = DEVMODE()
        dm.dmSize = ctypes.sizeof(DEVMODE)
        if user32.EnumDisplaySettingsW(None, -1, ctypes.byref(dm)):   # CURRENT_SETTINGS
            logical = user32.GetSystemMetrics(0)                      # SM_CXSCREEN
            if logical and dm.dmPelsWidth:
                return max(1.0, float(dm.dmPelsWidth) / float(logical))
    except Exception:
        pass
    return 1.0


def cursor_pos():
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def work_area():
    """Desktop area excluding the taskbar (SPI_GETWORKAREA)."""
    rc = RECT()
    user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rc), 0)
    return rc.left, rc.top, rc.right, rc.bottom


def show_no_activate(hwnd):
    """Show a window without stealing focus from whatever the user is typing in."""
    user32.ShowWindow(hwnd, 4)          # SW_SHOWNOACTIVATE
