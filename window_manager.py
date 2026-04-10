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

import time
import threading
from typing import Optional

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

    print(f"[WindowManager] Positioning hwnd {hwnd} → ({x},{y}) {w}×{h} on monitor {mon_idx}")
    set_window_position(hwnd, x, y, w, h, maximize=maximize)
