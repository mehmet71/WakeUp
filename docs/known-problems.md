# Known Problems

## P1 — Capture includes background/underlying processes

**Symptom:** When capturing the current desktop, the results include processes that are not visible open windows (e.g. background services, system processes, hidden windows).

**Expected:** Only visible, user-facing windows should appear in the capture results.

**Likely area:** `window_manager.py` → `list_visible_windows()` — the filtering logic (WS_VISIBLE flag check, area threshold, title blacklist) may not be strict enough to exclude all non-user windows.

---

## P2 — Window preset not applied on test/launch (VS Code opens in wrong position)

**Symptom:** A mode has VS Code configured to open on the left half of the monitor. When launched via "Test this mode" (or normal launch), VS Code opens with the correct workspace/folder but appears in the center of the monitor instead of the left half.

**Expected:** The window should be repositioned to the configured preset after launch.

**Likely area:** `launcher.py` / `window_manager.py` — the window arrangement may be firing too early (before VS Code's window is fully created), or the `hwnd` lookup is not finding the correct window. The arrangement timing or the window title/process matching may need adjustment.
