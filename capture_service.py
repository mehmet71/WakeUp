"""
Capture Service: Snapshots the current desktop into draft app records (Contract C2).

Public API:
    capture_current_desktop() -> list[dict]   # produces DraftApp dicts (Contract C1)
    draft_to_profile_app(draft: dict) -> dict  # converts to profiles.json app entry (Contract C5)
"""

import os

from window_manager import (
    get_monitors,
    list_visible_windows,
    get_window_process_path,
    get_window_monitor_index,
    match_rect_to_preset,
)

_JUNK_TITLES = {"Program Manager", "MSCTFIME", "Windows Input Experience"}

_APP_TYPE_MAP = {
    "code.exe":    "vscode",
    "chrome.exe":  "chrome",
    "msedge.exe":  "chrome",
    "firefox.exe": "browser",
}

_DISPLAY_NAME_MAP = {
    "vscode":  "VS Code",
    "chrome":  "Chrome",
    "browser": "Firefox",
}


# ------------------------------------------------------------------ #
#  Private helpers                                                     #
# ------------------------------------------------------------------ #

def _detect_app_type(exe_path: "str | None", title: str) -> str:
    if not exe_path:
        return "generic"
    stem = os.path.basename(exe_path).lower()
    return _APP_TYPE_MAP.get(stem, "generic")


def _generate_display_name(exe_path: "str | None", title: str) -> str:
    app_type = _detect_app_type(exe_path, title)
    if app_type in _DISPLAY_NAME_MAP:
        return _DISPLAY_NAME_MAP[app_type]
    if exe_path:
        stem = os.path.splitext(os.path.basename(exe_path))[0]
        return stem[0].upper() + stem[1:] if stem else title
    return title


def _default_launch_behavior(app_type: str) -> str:
    defaults = {
        "vscode":  "vscode_folder",
        "chrome":  "chrome_urls",
        "browser": "chrome_urls",
        "generic": "plain",
    }
    return defaults.get(app_type, "plain")


# ------------------------------------------------------------------ #
#  Public API                                                          #
# ------------------------------------------------------------------ #

def capture_current_desktop() -> list[dict]:
    """Snapshot visible windows into DraftApp dicts (Contract C1)."""
    monitors = get_monitors()
    windows = list_visible_windows()
    drafts = []

    for win in windows:
        title = win["title"]

        if title in _JUNK_TITLES:
            continue

        hwnd = win["hwnd"]
        rect = win["rect"]
        l, t, r, b = rect

        exe_path = get_window_process_path(hwnd)
        app_type = _detect_app_type(exe_path, title)
        display_name = _generate_display_name(exe_path, title)
        launch_behavior = _default_launch_behavior(app_type)

        mon_idx = get_window_monitor_index(hwnd, monitors)
        monitor = monitors[mon_idx] if mon_idx < len(monitors) else (monitors[0] if monitors else None)
        preset = match_rect_to_preset(rect, monitor, tolerance=0.08) if monitor else None

        confidence = "high" if app_type != "generic" else ("low" if not exe_path else "medium")

        drafts.append({
            "name": display_name,
            "path": exe_path or "",
            "window_title": title,
            "window": {
                "monitor": mon_idx,
                "preset": preset,
                "x": l,
                "y": t,
                "w": r - l,
                "h": b - t,
            },
            "app_type": app_type,
            "launch_behavior": launch_behavior,
            "launch_details": {},
            "confidence": confidence,
        })

    drafts.sort(key=lambda d: (d["window"]["monitor"], d["window"]["x"]))
    return drafts


def draft_to_profile_app(draft: dict) -> dict:
    """Convert reviewed DraftApp into profiles.json app entry (Contract C5)."""
    behavior = draft["launch_behavior"]
    details = draft.get("launch_details", {})

    args_map = {
        "plain":             [],
        "vscode_folder":     [details.get("folder", "")],
        "vscode_session":    [],
        "chrome_urls":       ["--new-window"] + details.get("urls", []),
        "chrome_new_window": ["--new-window"],
    }
    args = args_map.get(behavior, [])

    window = draft["window"]
    if window.get("preset") is not None:
        window_out = {"monitor": window["monitor"], "preset": window["preset"]}
    else:
        window_out = {
            "monitor": window["monitor"],
            "x": window["x"],
            "y": window["y"],
            "w": window["w"],
            "h": window["h"],
        }

    return {
        "name": draft["name"],
        "path": draft["path"],
        "args": args,
        "delay": 0,
        "window": window_out,
    }
