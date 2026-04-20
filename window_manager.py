"""
Window Manager: Monitor detection, preset layouts, and window positioning.

Preset names (case-insensitive):
  full           → entire monitor
  left-half      → left 50%
  right-half     → right 50%
  top-half       → top 50%
  bottom-half    → bottom 50%
  top-left       → top-left quadrant
  top-right      → top-right quadrant
  bottom-left    → bottom-left quadrant
  bottom-right   → bottom-right quadrant
  left-third     → left 33%
  center-third   → center 33%
  right-third    → right 33%
  left-two-thirds  → left 66%
  right-two-thirds → right 66%

Or use explicit coordinates:
  "window": {"monitor": 0, "x": 100, "y": 50, "w": 900, "h": 600}
"""

import ctypes
import time
from typing import Optional

_user32 = ctypes.windll.user32
_GetLastActivePopup = _user32.GetLastActivePopup
_GetLastActivePopup.restype = ctypes.c_void_p

_dwmapi = ctypes.windll.dwmapi
_DWMWA_CLOAKED = 14

try:
    import win32gui
    import win32con
    import win32api
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    print("[WindowManager] 'pywin32' not installed - window positioning disabled.")


# ------------------------------------------------------------------ #
#  Monitor utilities                                                   #
# ------------------------------------------------------------------ #

def get_monitors() -> list[dict]:
    """
    Returns a list of monitor info dicts, sorted so that the primary
    monitor is always index 0.
    """
    if not HAS_WIN32:
        return []

    monitors = []
    for hMonitor, _hdc, _rect in win32api.EnumDisplayMonitors(None, None):
        info = win32api.GetMonitorInfo(hMonitor)
        monitors.append({
            "handle": hMonitor,
            "rect": info["Monitor"],      # (left, top, right, bottom) absolute coords
            "work_area": info["Work"],    # excludes taskbar
            "primary": bool(info["Flags"] & 1),
        })

    monitors.sort(key=lambda m: (0 if m["primary"] else 1))
    for i, m in enumerate(monitors):
        m["index"] = i
    return monitors


def apply_preset(monitor: dict, preset: str) -> tuple[int, int, int, int]:
    """
    Returns (x, y, w, h) for the given preset within the monitor's work area.
    """
    l, t, r, b = monitor["work_area"]
    mw = r - l
    mh = b - t

    p = preset.lower().strip()
    presets = {
        "full":              (l,          t,          mw,       mh),
        "left-half":         (l,          t,          mw // 2,  mh),
        "right-half":        (l + mw//2,  t,          mw // 2,  mh),
        "top-half":          (l,          t,          mw,       mh // 2),
        "bottom-half":       (l,          t + mh//2,  mw,       mh // 2),
        "top-left":          (l,          t,          mw // 2,  mh // 2),
        "top-right":         (l + mw//2,  t,          mw // 2,  mh // 2),
        "bottom-left":       (l,          t + mh//2,  mw // 2,  mh // 2),
        "bottom-right":      (l + mw//2,  t + mh//2,  mw // 2,  mh // 2),
        "left-third":        (l,          t,          mw // 3,  mh),
        "center-third":      (l + mw//3,  t,          mw // 3,  mh),
        "right-third":       (l + 2*mw//3, t,         mw // 3,  mh),
        "left-two-thirds":   (l,          t,          2*mw//3,  mh),
        "right-two-thirds":  (l + mw//3,  t,          2*mw//3,  mh),
    }
    if p not in presets:
        print(f"[WindowManager] Unknown preset '{preset}', falling back to 'full'.")
        return presets["full"]
    return presets[p]


# ------------------------------------------------------------------ #
#  Window finding                                                      #
# ------------------------------------------------------------------ #

def find_window_by_pid(pid: int, timeout: float = 15.0) -> Optional[int]:
    """
    Wait up to `timeout` seconds for a visible, titled window belonging
    to the given process ID. Returns the window handle or None.
    """
    if not HAS_WIN32:
        return None

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = []

        def _cb(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return True
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return True
            try:
                _, wpid = win32process.GetWindowThreadProcessId(hwnd)
                if wpid == pid:
                    found.append(hwnd)
            except Exception:
                pass
            return True

        win32gui.EnumWindows(_cb, None)
        if found:
            # Prefer the window that is not just a tooltip or tiny helper
            best = max(found, key=lambda h: _window_area(h))
            return best
        time.sleep(0.35)

    return None


def _window_area(hwnd: int) -> int:
    try:
        rect = win32gui.GetWindowRect(hwnd)
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        return w * h
    except Exception:
        return 0


def find_window_by_title(title_fragment: str) -> Optional[int]:
    """Fuzzy-find a window by title substring (case-insensitive)."""
    if not HAS_WIN32:
        return None
    results = []

    def _cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd)
            if title_fragment.lower() in t.lower():
                results.append(hwnd)
        return True

    win32gui.EnumWindows(_cb, None)
    return results[0] if results else None


# ------------------------------------------------------------------ #
#  Window positioning                                                  #
# ------------------------------------------------------------------ #

def set_window_position(hwnd: int, x: int, y: int, w: int, h: int, maximize: bool = False):
    """Move and resize a window. Restores it first if minimized/maximized."""
    if not HAS_WIN32:
        return
    try:
        # Restore first so SetWindowPos works correctly
        placement = win32gui.GetWindowPlacement(hwnd)
        if placement[1] in (win32con.SW_SHOWMAXIMIZED, win32con.SW_SHOWMINIMIZED):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.05)

        if maximize:
            win32gui.MoveWindow(hwnd, x, y, w, h, True)
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        else:
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOP,
                x, y, w, h,
                win32con.SWP_SHOWWINDOW,
            )
    except Exception as e:
        print(f"[WindowManager] Could not position hwnd {hwnd}: {e}")


def arrange_window(hwnd: int, window_cfg: dict, monitors: list[dict]):
    """
    Apply a window config dict to a window handle.

    window_cfg can be:
      {"monitor": 0, "preset": "left-half"}
      {"monitor": 1, "preset": "full", "maximize": true}
      {"monitor": 0, "x": 0, "y": 0, "w": 1920, "h": 1080}
    """
    if not monitors:
        print("[WindowManager] No monitors found, skipping arrangement.")
        return

    mon_idx = window_cfg.get("monitor", 0)
    if mon_idx >= len(monitors):
        print(f"[WindowManager] Monitor {mon_idx} not found (only {len(monitors)} monitors), using 0.")
        mon_idx = 0
    monitor = monitors[mon_idx]

    maximize = window_cfg.get("maximize", False)

    if "preset" in window_cfg:
        x, y, w, h = apply_preset(monitor, window_cfg["preset"])
    else:
        l, t, _, _ = monitor["work_area"]
        x = l + window_cfg.get("x", 0)
        y = t + window_cfg.get("y", 0)
        w = window_cfg.get("w", 1280)
        h = window_cfg.get("h", 720)

    set_window_position(hwnd, x, y, w, h, maximize=maximize)


# ------------------------------------------------------------------ #
#  Capture helpers (Contract C3)                                       #
# ------------------------------------------------------------------ #

_PRESET_NAMES = [
    "full", "left-half", "right-half", "top-half", "bottom-half",
    "top-left", "top-right", "bottom-left", "bottom-right",
    "left-third", "center-third", "right-third",
    "left-two-thirds", "right-two-thirds",
]


def list_visible_windows() -> list[dict]:
    """
    Returns list of visible, titled, non-minimized, on-screen top-level windows.
    Each dict: {"hwnd": int, "title": str, "rect": (l, t, r, b), "pid": int}
    Filters: skips empty titles, area < 10_000 px², minimized windows, off-screen windows.
    """
    if not HAS_WIN32:
        return []

    monitors = get_monitors()
    results = []

    def _cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        if win32gui.IsIconic(hwnd):
            return True
        # Skip cloaked windows: UWP apps suspended in background are marked
        # WS_VISIBLE by the OS but DWM doesn't draw them (TextInputHost, etc.)
        cloaked = ctypes.c_int(0)
        _dwmapi.DwmGetWindowAttribute(hwnd, _DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
        if cloaked.value:
            return True
        # Canonical Alt-Tab/taskbar filter: the window must be the last active
        # popup of its root-owner chain and not a tool window.
        root = win32gui.GetAncestor(hwnd, 3)  # GA_ROOTOWNER
        if _GetLastActivePopup(root) != hwnd:
            return True
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if (ex_style & win32con.WS_EX_TOOLWINDOW) and not (ex_style & win32con.WS_EX_APPWINDOW):
            return True
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return True
        try:
            l, t, r, b = win32gui.GetWindowRect(hwnd)
            if (r - l) * (b - t) < 10_000:
                return True
            if not any(l < mr and r > ml and t < mb and b > mt
                       for m in monitors
                       for ml, mt, mr, mb in [m["rect"]]):
                return True
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            results.append({"hwnd": hwnd, "title": title, "rect": (l, t, r, b), "pid": pid})
        except Exception:
            pass
        return True

    win32gui.EnumWindows(_cb, None)
    return results


def get_window_process_path(hwnd: int) -> "str | None":
    """
    Resolve the full executable path for the process owning this window.
    Returns None on failure or access-denied.
    """
    if not HAS_WIN32:
        return None
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010
        handle = win32api.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
        try:
            return win32process.GetModuleFileNameEx(handle, 0)
        finally:
            win32api.CloseHandle(handle)
    except Exception:
        return None


def get_window_monitor_index(hwnd: int, monitors: list[dict]) -> int:
    """
    Determine which monitor a window is on based on its center point.
    Returns 0-based monitor index. Falls back to 0.
    """
    if not HAS_WIN32 or not monitors:
        return 0
    try:
        l, t, r, b = win32gui.GetWindowRect(hwnd)
        cx = (l + r) // 2
        cy = (t + b) // 2
        for m in monitors:
            ml, mt, mr, mb = m["work_area"]
            if ml <= cx < mr and mt <= cy < mb:
                return m["index"]
    except Exception:
        pass
    return 0


def match_rect_to_preset(rect: tuple, monitor: dict, tolerance: float = 0.08) -> "str | None":
    """
    Compare a window rect against all known presets for the given monitor.
    Returns the preset name if within tolerance, else None.
    rect is (left, top, right, bottom) absolute coordinates.
    """
    l, t, r, b = rect
    actual_x, actual_y = l, t
    actual_w, actual_h = r - l, b - t

    ml, mt, mr, mb = monitor["work_area"]
    mw = mr - ml
    mh = mb - mt

    for name in _PRESET_NAMES:
        ex, ey, ew, eh = apply_preset(monitor, name)
        if (
            abs(ex - actual_x) <= tolerance * mw
            and abs(ey - actual_y) <= tolerance * mh
            and abs(ew - actual_w) <= tolerance * mw
            and abs(eh - actual_h) <= tolerance * mh
        ):
            return name
    return None
