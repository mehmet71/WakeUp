"""
Launcher: Spawns processes from a profile config, waits for their windows,
then hands off to WindowManager for arrangement.
"""

import os
import subprocess
import time
import threading
from pathlib import Path
from typing import Optional

from window_manager import find_window_by_pid, arrange_window, get_monitors


def _resolve_path(raw: str) -> str:
    """Expand env vars and ~ in app paths."""
    return str(Path(os.path.expandvars(os.path.expanduser(raw))))


def _build_launch_args(app: dict) -> list[str]:
    """
    Build the full command-line args list for an app entry (excluding the exe path).
    Pure function — no side effects. Honors the optional `browser` block:
      browser.restore_session == False  →  prepend "--new-window"
      browser.urls                       →  appended as positional args
    """
    args = [str(a) for a in app.get("args", [])]

    browser = app.get("browser")
    if browser is not None:
        if not browser.get("restore_session", True):
            args = ["--new-window"] + args
        urls = [str(u) for u in browser.get("urls", [])]
        args = args + urls

    return args


def launch_app(app: dict) -> Optional[int]:
    """
    Launch a single app from its config dict. Returns PID or None on failure.

    app dict fields:
      path       (required) Executable path
      args       (optional) List of command-line arguments
      delay      (optional) Seconds to wait before launching (default 0)
      if_running (optional) "focus" | "new_instance" | "skip" (default "focus")
      title_hint (optional) Window title fragment for finding the window
    """
    delay = app.get("delay", 0)
    if delay > 0:
        time.sleep(delay)

    exe_path = _resolve_path(app["path"])
    cmd = [exe_path] + _build_launch_args(app)

    name = app.get("name", Path(exe_path).stem)
    try:
        proc = subprocess.Popen(
            cmd,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            if hasattr(subprocess, "DETACHED_PROCESS") else 0,
        )
        return proc.pid
    except FileNotFoundError:
        print(f"[Launcher] ✗ Executable not found: {exe_path}")
        return None
    except Exception as e:
        print(f"[Launcher] ✗ Failed to start '{name}': {e}")
        return None


def _arrange_after_launch(app: dict, pid: int, monitors: list[dict]):
    """Wait for the window to appear, then arrange it. Runs in its own thread."""
    window_cfg = app.get("window")
    if not window_cfg:
        return  # No arrangement needed

    name = app.get("name", "app")
    wait_timeout = app.get("window_wait_timeout", 20.0)

    # Give the process a moment to initialize before we start polling
    time.sleep(0.5)

    hwnd = find_window_by_pid(pid, timeout=wait_timeout)
    if hwnd is None:
        print(f"[Launcher] ✗ Window for '{name}' (pid {pid}) not found within {wait_timeout}s.")
        return

    # Extra settle time for apps that repaint their window after creation
    settle = app.get("window_settle", 0.3)
    if settle > 0:
        time.sleep(settle)

    arrange_window(hwnd, window_cfg, monitors)


def execute_profile(profile: dict):
    """
    Execute a full profile: launch all apps and arrange their windows.
    Apps with the same `delay` are launched concurrently; window
    arrangement always happens asynchronously after the window appears.
    """
    apps = profile.get("apps", [])
    if not apps:
        print("[Launcher] Profile has no apps defined.")
        return

    monitors = get_monitors()

    threads: list[threading.Thread] = []

    for app in apps:
        pid = launch_app(app)
        if pid is None:
            continue

        # Arrange window in background — doesn't block the next app from launching
        t = threading.Thread(
            target=_arrange_after_launch,
            args=(app, pid, monitors),
            daemon=True,
            name=f"arrange-{app.get('name', pid)}",
        )
        t.start()
        threads.append(t)

    # Optional: wait for all arrangement threads before returning
    # (useful for scripting, less useful for interactive use)
    # for t in threads:
    #     t.join()
