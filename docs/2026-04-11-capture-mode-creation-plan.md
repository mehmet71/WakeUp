# Capture-First Mode Creation + Config UI Refresh

> **For agentic workers:** This plan is split into independent stories (S1–S5) that can be worked on in parallel. Dependencies between stories are called out explicitly. **Before writing any code, read the Contracts section below.** Every function signature, data shape, and instance variable listed there is frozen — do not rename, reorder, or reshape them. If your story produces or consumes a contract, code against the exact specification.

**Goal:** Add a capture-based mode creation workflow to WakeUp, keep manual editing as fallback, and redesign `config_ui` into a cleaner, more modern, task-oriented UI.

**Architecture:** The new flow sits on top of the current profile model. Window capture produces a draft mode, the review screen resolves app-specific launch intent, and the final saved result translates into the existing per-profile app structure. No migration needed.

**Tech Stack:** Python, Tkinter, `pywin32`, existing WakeUp launcher/window modules

---

## Contracts (READ FIRST — shared across all stories)

Every agent must code against these exact interfaces. If you are producing a contract, implement it exactly. If you are consuming one, import/use it exactly as written. **Do not deviate.**

### Contract C1 — Draft App Record

This is the central data shape that flows from capture (S1) → review UI (S3) → save logic (S4). Every field name, type, and nesting level is fixed.

```python
# TypedDict for reference — actual runtime is plain dict
DraftApp = {
    "name": str,                # human-friendly display name, e.g. "VS Code"
    "path": str,                # full executable path, e.g. "C:/Users/.../Code.exe"
    "window_title": str,        # captured window title at time of snapshot
    "window": {
        "monitor": int,         # 0-based monitor index
        "preset": str | None,   # matched preset name, or None if no match
        "x": int,               # absolute x of window rect
        "y": int,               # absolute y of window rect
        "w": int,               # width in pixels
        "h": int,               # height in pixels
    },
    "app_type": str,            # one of: "vscode", "chrome", "browser", "generic"
    "launch_behavior": str,     # one of: "plain", "vscode_folder", "vscode_session",
                                #         "chrome_urls", "chrome_new_window"
    "launch_details": dict,     # depends on launch_behavior:
                                #   vscode_folder  → {"folder": str}
                                #   chrome_urls    → {"urls": list[str]}
                                #   all others     → {}
    "confidence": str,          # one of: "high", "medium", "low"
}
```

**Rules:**
- S1 produces this shape from `capture_current_desktop()`. Fields `launch_details` is always `{}` at capture time.
- S3 (review UI) reads all fields, lets user edit `name`, `launch_behavior`, `launch_details`, `window.monitor`, `window.preset`. Writes changes back into the same dict shape.
- S4 (save) consumes this shape via `draft_to_profile_app()` to produce the final profile app dict.

### Contract C2 — capture_service.py public API

**File:** `capture_service.py` (created by S1, consumed by S3 and S4)

```python
def capture_current_desktop() -> list[DraftApp]:
    """
    Snapshot all visible windows on the current desktop.
    Returns a list of DraftApp dicts sorted by (monitor, x-position).
    Filters out junk/system windows.
    """
    ...

def draft_to_profile_app(draft: DraftApp) -> dict:
    """
    Convert a reviewed DraftApp into a profiles.json-compatible app entry.

    Returns:
        {
            "name": str,
            "path": str,
            "args": list[str],
            "delay": 0,
            "window": {"monitor": int, "preset": str}
                   or {"monitor": int, "x": int, "y": int, "w": int, "h": int}
        }

    Translation rules:
        launch_behavior     → args
        ─────────────────────────────────────
        plain               → []
        vscode_folder       → [launch_details["folder"]]
        vscode_session      → []
        chrome_urls         → ["--new-window"] + launch_details["urls"]
        chrome_new_window   → ["--new-window"]

    Window: uses preset if not None, otherwise falls back to x/y/w/h.
    """
    ...
```

**Import path used by consumers:**
```python
from capture_service import capture_current_desktop, draft_to_profile_app
```

### Contract C3 — window_manager.py new helpers

**File:** `window_manager.py` (added by S1, consumed only inside `capture_service.py`)

```python
def list_visible_windows() -> list[dict]:
    """
    Returns list of visible, titled, non-tiny top-level windows.
    Each dict: {"hwnd": int, "title": str, "rect": (l, t, r, b), "pid": int}
    Filters: skips empty titles, area < 10_000 px².
    """
    ...

def get_window_process_path(hwnd: int) -> str | None:
    """
    Resolve the full executable path for the process owning this window.
    Returns None on failure or access-denied.
    """
    ...

def get_window_monitor_index(hwnd: int, monitors: list[dict]) -> int:
    """
    Determine which monitor a window is on based on its center point.
    Returns 0-based monitor index. Falls back to 0.
    """
    ...

def match_rect_to_preset(rect: tuple, monitor: dict, tolerance: float = 0.08) -> str | None:
    """
    Compare a window rect against all known presets for the given monitor.
    Returns the preset name if within tolerance, else None.
    rect is (left, top, right, bottom) absolute coordinates.
    """
    ...
```

These are consumed only by `capture_service.py`. No other file imports them directly.

### Contract C4 — config_ui.py screen system (established by S2, extended by S3/S4/S5)

**Instance variables on `WakeUpConfigUI`:**

```python
self._current_view: str             # one of the VIEW_* constants below
self._view_frame: tk.Frame          # right-side content area, cleared on view switch
self._draft_apps: list[dict] | None # list of DraftApp dicts during capture flow, else None
self._current_profile: str | None   # name of profile being edited, else None
self.profiles: dict                 # all profiles, keyed by name
self.config_data: dict              # full profiles.json content
```

**View name constants (use these strings, not free-form):**

```python
VIEW_HOME            = "home"
VIEW_NEW_MODE_CHOICE = "new_mode_choice"
VIEW_CAPTURE         = "capture"
VIEW_REVIEW          = "review"
VIEW_MODE_DETAIL     = "mode_detail"
VIEW_ADVANCED        = "advanced"
```

**Navigation method:**

```python
def _show_view(self, view_name: str):
    """
    Clears self._view_frame children, then calls self._build_<view_name>().
    Updates self._current_view.
    """
    ...
```

**Builder method naming convention:**
Each view has a builder method named `_build_{VIEW_NAME}()` that populates `self._view_frame`:
- `_build_home()`
- `_build_new_mode_choice()`
- `_build_capture()`           ← implemented by S3
- `_build_review()`            ← implemented by S3
- `_build_mode_detail()`       ← implemented by S4
- `_build_advanced()`          ← implemented by S4

S2 creates empty stubs for all six. S3 and S4 fill in the stubs they own.

**Shared UI helpers (created by S2, available to all):**

```python
def card_frame(parent, **pack_kw) -> tk.Frame:
    """Returns a styled card panel (bg=BG2, padx=16, pady=12). Caller packs it."""
    ...

def section_heading(parent, text: str):
    """Large 14px bold heading label."""
    ...

# Existing helpers remain available:
# labeled_entry, dark_text, icon_btn, section_label
```

**Theme constants (updated by S2, used everywhere):**

```python
BG       = "#1e1e1e"     # main background (was #1a1a1a)
BG2      = "#262626"     # card/panel background (was #242424)
BG3      = "#303030"     # input fields (was #2e2e2e)
ACCENT   = "#00b4d8"     # primary accent (unchanged)
ACCENT2  = "#0077a8"     # hover/pressed accent (unchanged)
FG       = "#e8e8e8"     # primary text (unchanged)
FG2      = "#a0a0a0"     # muted labels (unchanged)
RED      = "#e05555"     # danger (unchanged)
GREEN    = "#4caf7d"     # success (unchanged)
BORDER   = "#383838"     # borders (unchanged)
FONT     = ("Segoe UI", 10)
FONT_SM  = ("Segoe UI", 9)
FONT_B   = ("Segoe UI", 10, "bold")
FONT_H   = ("Segoe UI", 14, "bold")    # was 13
FONT_H2  = ("Segoe UI", 12, "bold")    # new — sub-headings
```

### Contract C5 — Profile app dict (existing, unchanged)

This is the final saved format in `profiles.json`. All agents must produce this exact shape when saving.

```python
ProfileApp = {
    "name": str,
    "path": str,
    "args": list[str],
    "delay": float,           # default 0
    "window": {
        "monitor": int,
        "preset": str,        # if preset-based
    }
    # OR
    "window": {
        "monitor": int,
        "x": int, "y": int, "w": int, "h": int,  # if coordinate-based
    }
}
```

### Contract C6 — Launch behavior ↔ UI mapping

Fixed mapping used by S3 (review UI) and S4 (save translation). Do not invent new values.

| `app_type` | `launch_behavior` options | UI label | Detail widget |
|---|---|---|---|
| `"vscode"` | `"vscode_folder"` | `"Open folder/workspace"` | Folder entry + browse |
| `"vscode"` | `"vscode_session"` | `"Reopen last session"` | None |
| `"vscode"` | `"plain"` | `"Launch plain"` | None |
| `"chrome"` | `"chrome_urls"` | `"Open these URLs"` | Multiline text |
| `"chrome"` | `"chrome_new_window"` | `"Open new window"` | None |
| `"browser"` | `"chrome_urls"` | `"Open these URLs"` | Multiline text |
| `"browser"` | `"chrome_new_window"` | `"Open new window"` | None |
| `"generic"` | `"plain"` | `"Launch normally"` | Optional args entry (advanced) |

### Contract C7 — File ownership

Each story owns specific files. No story may edit files it does not own.

| File | S1 | S2 | S3 | S4 | S5 |
|------|----|----|----|----|-----|
| `window_manager.py` | **owner** | — | — | — | — |
| `capture_service.py` | **owner** | — | import only | import only | — |
| `config_ui.py` | — | **owner** (foundation) | **owner** (`_build_capture`, `_build_review`) | **owner** (`_build_mode_detail`, `_build_advanced`, save logic, validation) | **owner** (test button) |
| `launcher.py` | — | — | — | — | **owner** |
| `README.md` | — | — | — | — | **owner** |

For `config_ui.py` which is touched by S2, S3, S4, and S5:
- **S2** builds the skeleton: theme, screen system, `_show_view`, stubs, `_build_home`, `_build_new_mode_choice`, shared helpers.
- **S3** fills in ONLY `_build_capture()` and `_build_review()` stubs. Does not touch other builders.
- **S4** fills in ONLY `_build_mode_detail()`, `_build_advanced()`, save handler, and validation. Does not touch S3's builders.
- **S5** adds test button into mode-detail and advanced builders (small addition, runs after S4).

---

## Dependency Graph

```
S1  Capture Backend ──────────┐
                               ├──► S3  Capture Flow UI (_build_capture, _build_review)
S2  UI Foundation + Visuals ──┤
                               ├──► S4  Mode Details + Save (_build_mode_detail, _build_advanced)
                               │
                               └──► S5  Test Mode + Docs
```

- **S1** and **S2** have zero shared files and can run fully in parallel.
- **S3** depends on both S1 and S2 being done.
- **S4** depends on S2 being done (uses the screen system). Does not need S1.
- **S5** depends on S4 being done (needs save to work). Light dependency on S3 for test-mode.

---

## File Plan

| Action | File | Owner story | Responsibility |
|--------|------|-------------|----------------|
| Create | `capture_service.py` | S1 | Window enumeration → draft app records (Contract C2) |
| Modify | `window_manager.py` | S1 | Capture helpers (Contract C3) |
| Modify | `config_ui.py` | S2 foundation, S3/S4/S5 fill stubs | Full UI redesign (Contract C4) |
| Modify | `launcher.py` | S5 | Small test-mode helpers |
| Modify | `README.md` | S5 | Document new workflow |

Schema unchanged: `profiles.json` keeps its current shape (Contract C5).

---

## Story S1 — Capture Backend

**Scope:** Everything needed to snapshot the current desktop into draft app records.
**Files touched:** `window_manager.py`, `capture_service.py` (new)
**Produces:** Contracts C2 and C3
**Consumes:** Existing `window_manager.py` functions (`get_monitors`, `apply_preset`)
**No UI work.** This story is pure backend logic.

### Task 1.1: Add visible-window enumeration helpers

**File:** `window_manager.py`

Add the four functions specified in **Contract C3**, below the existing `arrange_window` function. Signatures, return types, and parameter names must match the contract exactly.

Implementation notes:
- `list_visible_windows`: use `win32gui.EnumWindows`. The returned `rect` is `(left, top, right, bottom)` matching `win32gui.GetWindowRect` format.
- `get_window_process_path`: use `win32process.GetWindowThreadProcessId` → `win32api.OpenProcess` → `win32process.GetModuleFileNameEx`. Wrap in try/except, return `None` on any failure.
- `get_window_monitor_index`: compute center `(cx, cy)` from rect, iterate `monitors` list, check if center falls within each monitor's `work_area` `(l, t, r, b)`.
- `match_rect_to_preset`: for each preset name, call the existing `apply_preset(monitor, preset_name)` to get expected `(x, y, w, h)`, convert actual rect `(l, t, r, b)` to `(x, y, w, h)`, compare with tolerance as fraction of monitor dimension.

- [ ] Implement `list_visible_windows`
- [ ] Implement `get_window_process_path`
- [ ] Implement `get_window_monitor_index`
- [ ] Implement `match_rect_to_preset`
- [ ] Smoke-test: run helpers from a scratch script, print results, verify output makes sense with 2-3 open windows

### Task 1.2: Build capture service

**File:** `capture_service.py` (new)

Implement the two public functions from **Contract C2** plus these private helpers:

- `_detect_app_type(exe_path: str, title: str) -> str`
  - Map known exe names (case-insensitive stem):
    - `Code.exe` → `"vscode"`
    - `chrome.exe` → `"chrome"`
    - `msedge.exe` → `"chrome"`
    - `firefox.exe` → `"browser"`
    - everything else → `"generic"`

- `_generate_display_name(exe_path: str, title: str) -> str`
  - Known: `"vscode"` → `"VS Code"`, `"chrome"` → `"Chrome"`, etc.
  - Fallback: exe stem, first letter capitalized.

- `_default_launch_behavior(app_type: str) -> str`
  - `"vscode"` → `"vscode_folder"`
  - `"chrome"` → `"chrome_urls"`
  - `"browser"` → `"chrome_urls"`
  - `"generic"` → `"plain"`

- Junk-window filtering: skip windows titled `"Program Manager"`, `"MSCTFIME"`, `"Windows Input Experience"`, or with area < 10 000 px².

**Output must match Contract C1 exactly.** `launch_details` is always `{}` at capture time.

Imports from `window_manager`:
```python
from window_manager import (
    get_monitors,
    list_visible_windows,
    get_window_process_path,
    get_window_monitor_index,
    match_rect_to_preset,
)
```

- [ ] Create `capture_service.py` with `capture_current_desktop` and private helpers
- [ ] Add junk-window filtering
- [ ] Implement `draft_to_profile_app` per Contract C2 translation table
- [ ] Smoke-test: call `capture_current_desktop()` with a few apps open, verify JSON output matches Contract C1

---

## Story S2 — UI Foundation + Visual Refresh

**Scope:** Refactor `config_ui.py` internals into a screen-based architecture and apply the modern visual style. Create stubs for all screens. Build home and new-mode-choice screens.
**Files touched:** `config_ui.py` only
**Produces:** Contract C4 (screen system, helpers, theme, stubs)
**Consumes:** Nothing new
**No dependency on S1.** Does not import `capture_service`.

### Task 2.1: Update theme constants and helpers

**File:** `config_ui.py`

Update the constants at the top to match **Contract C4 theme constants** exactly. Add the two new helpers:

```python
def card_frame(parent, **pack_kw) -> tk.Frame:
    f = tk.Frame(parent, bg=BG2, padx=16, pady=12)
    if pack_kw:
        f.pack(**pack_kw)
    return f

def section_heading(parent, text: str):
    tk.Label(parent, text=text, bg=BG, fg=FG, font=FONT_H).pack(anchor="w", pady=(0, 8))
```

Update `apply_theme` for any new style values (larger heading, sub-heading font, etc.).

- [ ] Update all color/font constants to match Contract C4
- [ ] Add `FONT_H2` constant
- [ ] Add `card_frame` helper
- [ ] Add `section_heading` helper
- [ ] Update `apply_theme` for new values

### Task 2.2: Introduce screen/view state management

**File:** `config_ui.py`

Add view constants and refactor `WakeUpConfigUI.__init__` and `_build_ui` per **Contract C4**.

Add to `__init__`:
```python
self._current_view: str = VIEW_HOME
self._view_frame: tk.Frame  # assigned in _build_ui
self._draft_apps: list[dict] | None = None
```

Refactor `_build_ui`:
- Keep left sidebar (mode list) always visible
- Replace the current right panel with `self._view_frame = tk.Frame(main, bg=BG)`
- Call `_show_view(VIEW_HOME)` at the end

Implement `_show_view` per contract:
```python
def _show_view(self, view_name: str):
    for child in self._view_frame.winfo_children():
        child.destroy()
    self._current_view = view_name
    builder = getattr(self, f"_build_{view_name}", None)
    if builder:
        builder()
```

Create empty stubs for all six builders. Each stub should show a centered label with the view name so it's testable:
```python
def _build_capture(self):
    tk.Label(self._view_frame, text="[capture — stub]", bg=BG, fg=FG2).pack(pady=40)

# same pattern for _build_review, _build_mode_detail, _build_advanced
```

- [ ] Add `VIEW_*` constants at module level
- [ ] Add instance variables to `__init__`
- [ ] Refactor `_build_ui` to use `_view_frame`
- [ ] Implement `_show_view`
- [ ] Create six stub builders
- [ ] Migrate existing detail-panel logic into `_build_mode_detail` stub (can be rough — S4 will rewrite)
- [ ] Verify app still opens and existing mode editing works

### Task 2.3: Refresh visual layout

**File:** `config_ui.py`

- Increase window geometry to `1060x720`, minsize `860x540`
- Widen left sidebar to `220px`
- Restyle sidebar: mode items show name + app count + hotkey hint
- Restyle top bar: cleaner title, unsaved-changes status chip
- Update `+ Add` button in sidebar to `+ New mode` (navigates to `VIEW_NEW_MODE_CHOICE`)
- Remove `Dupe` and `Del` from sidebar buttons (move to mode-detail or right-click context)

- [ ] Update geometry and sidebar width
- [ ] Restyle sidebar mode items
- [ ] Restyle top bar
- [ ] Update sidebar button to `+ New mode`
- [ ] Verify nothing visually broken

### Task 2.4: Build home screen

**File:** `config_ui.py`

Implement `_build_home()`:
- Section heading: `"Your modes"`
- If profiles exist: show mode cards (name, app count, hotkey) as clickable items
- If no profiles: show empty-state message + `"Create your first mode"` CTA
- Mode card click → `self._current_profile = name; self._show_view(VIEW_MODE_DETAIL)`
- `+ New mode` button prominent

- [ ] Implement `_build_home`
- [ ] Wire mode card clicks
- [ ] Wire new-mode button
- [ ] Handle empty-state

### Task 2.5: Build new-mode-choice screen

**File:** `config_ui.py`

Implement `_build_new_mode_choice()`:
- Heading: `"Create a new mode"`
- Two large cards:
  - `"Capture current setup"` → `_show_view(VIEW_CAPTURE)`
  - `"Manual setup"` → create empty profile, set `_current_profile`, `_show_view(VIEW_MODE_DETAIL)`
- `"Back"` link → `_show_view(VIEW_HOME)`

- [ ] Implement `_build_new_mode_choice`
- [ ] Wire capture card
- [ ] Wire manual card
- [ ] Wire back navigation

---

## Story S3 — Capture Flow UI

**Scope:** Fill in the `_build_capture` and `_build_review` stubs in `config_ui.py`.
**Files touched:** `config_ui.py` (only the two stub methods + `_build_app_card` helper)
**Depends on:** S1 (needs `capture_current_desktop` to be real) and S2 (needs screen system)
**Produces:** Nothing consumed by other stories
**Consumes:** Contract C1 (DraftApp shape), Contract C2 (`capture_current_desktop`), Contract C4 (screen system, helpers), Contract C6 (launch behavior ↔ UI mapping)

**Important:** Only fill in `_build_capture()`, `_build_review()`, and add a private `_build_app_card()` helper. Do not touch any other builder method or the screen system itself.

### Task 3.1: Build the capture screen

**File:** `config_ui.py` — fill in `_build_capture` stub

Centered panel:
- `section_heading`: `"Capture your current setup"`
- Instruction label: `"Open the apps you want in this mode and arrange them on your monitors. When ready, click Capture."`
- Primary button: `"Capture now"`
- Secondary: `"Back"` → `_show_view(VIEW_NEW_MODE_CHOICE)`, `"Build manually instead"` → create empty profile, `_show_view(VIEW_MODE_DETAIL)`

On capture:
```python
from capture_service import capture_current_desktop
drafts = capture_current_desktop()
self._draft_apps = drafts
```
- If `len(drafts) == 0`: show message `"No windows detected. Make sure your apps are open and visible."`
- Otherwise: show summary `f"Found {len(drafts)} apps on {n} monitors"`, then `_show_view(VIEW_REVIEW)`

- [ ] Implement `_build_capture`
- [ ] Wire capture button
- [ ] Handle zero-results
- [ ] Navigate to review

### Task 3.2: Build the review-draft screen

**File:** `config_ui.py` — fill in `_build_review` stub

Scrollable vertical list. One card per item in `self._draft_apps`.

Add `_build_app_card(self, parent: tk.Frame, draft: dict, index: int) -> tk.Frame`:
- Reads from `draft` (Contract C1 shape)
- Shows: name entry, path label + browse, launch behavior dropdown (options from Contract C6 based on `draft["app_type"]`), detail widget area, monitor dropdown, preset dropdown, remove button
- Launch behavior dropdown `<<ComboboxSelected>>` callback swaps the detail widget:
  - `vscode_folder` → folder entry + browse button, writes to `draft["launch_details"]["folder"]`
  - `chrome_urls` → multiline text, writes to `draft["launch_details"]["urls"]` (split by newlines)
  - others → hide detail area
- Remove button: removes from `self._draft_apps`, rebuilds review screen

Bottom actions:
- `"Continue"` → `_show_view(VIEW_MODE_DETAIL)`
- `"+ Add app manually"` → append empty DraftApp to `self._draft_apps`, rebuild
- `"Back to capture"` → `_show_view(VIEW_CAPTURE)`

Empty DraftApp template for manual add:
```python
{
    "name": "",
    "path": "",
    "window_title": "",
    "window": {"monitor": 0, "preset": "full", "x": 0, "y": 0, "w": 1280, "h": 720},
    "app_type": "generic",
    "launch_behavior": "plain",
    "launch_details": {},
    "confidence": "low",
}
```

- [ ] Implement `_build_review`
- [ ] Implement `_build_app_card`
- [ ] Wire launch-behavior dropdown to swap detail area
- [ ] Wire folder browse for VS Code
- [ ] Wire remove per card
- [ ] Wire continue, add-manually, back buttons

---

## Story S4 — Mode Details + Save Translation

**Scope:** Fill in `_build_mode_detail` and `_build_advanced` stubs. Implement save logic and validation.
**Files touched:** `config_ui.py` (only the two stub methods + save/validation helpers)
**Depends on:** S2 (needs screen system). Does NOT need S1 or S3 to be done — can work with mock `_draft_apps`.
**Produces:** Working save flow
**Consumes:** Contract C1 (DraftApp), Contract C2 (`draft_to_profile_app`), Contract C4 (screen system), Contract C5 (ProfileApp), Contract C6 (behavior mapping)

**Important:** Only fill in `_build_mode_detail()`, `_build_advanced()`, and add save/validation helpers. Do not touch `_build_capture`, `_build_review`, or the screen system itself.

### Task 4.1: Build the mode-details screen

**File:** `config_ui.py` — fill in `_build_mode_detail` stub

Clean form inside a card:
- Mode name: large entry, prominent (pre-filled from `self._current_profile` if editing)
- Hotkey: entry with hint `"e.g. ctrl+alt+w"`
- Startup message: entry
- Trigger keywords: multiline `dark_text`, one per line

Store form variables:
```python
self._detail_vars = {
    "name": tk.StringVar(),
    "hotkey": tk.StringVar(),
    "message": tk.StringVar(),
}
self._detail_kw_text: tk.Text  # keywords multiline
```

If editing an existing profile (`self._current_profile is not None` and `self._draft_apps is None`):
- Pre-fill from `self.profiles[self._current_profile]`

If coming from capture flow (`self._draft_apps is not None`):
- Pre-fill name as empty (user must name it)
- Other fields empty

Primary action: `"Save mode"` → calls `self._save_mode()`
Secondary: `"Back to review"` (only if `self._draft_apps is not None`) → `_show_view(VIEW_REVIEW)`
Secondary: `"Advanced edit"` → `_show_view(VIEW_ADVANCED)`

- [ ] Implement `_build_mode_detail`
- [ ] Pre-fill for editing vs. new capture flow
- [ ] Wire save, back, advanced buttons

### Task 4.2: Implement save logic

**File:** `config_ui.py`

Add `_save_mode(self)`:

```python
def _save_mode(self):
    name = self._detail_vars["name"].get().strip()
    if not name:
        # show inline validation error
        return
    if name != self._current_profile and name in self.profiles:
        # show duplicate name error
        return

    hotkey = self._detail_vars["hotkey"].get().strip()
    message = self._detail_vars["message"].get().strip()
    raw_kw = self._detail_kw_text.get("1.0", "end").strip()
    keywords = [k.strip() for k in raw_kw.splitlines() if k.strip()]

    if self._draft_apps is not None:
        # Capture flow: translate drafts
        from capture_service import draft_to_profile_app
        apps = [draft_to_profile_app(d) for d in self._draft_apps]
    elif self._current_profile and self._current_profile in self.profiles:
        # Editing existing: keep current apps
        apps = self.profiles[self._current_profile].get("apps", [])
    else:
        apps = []

    profile = {
        "trigger_keywords": keywords,
        "hotkey": hotkey,
        "message": message,
        "apps": apps,
    }

    # Handle rename
    if self._current_profile and self._current_profile != name:
        del self.profiles[self._current_profile]

    self.profiles[name] = profile
    self._current_profile = name
    self._draft_apps = None
    self.config_data["profiles"] = self.profiles

    # Write file
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(self.config_data, f, indent=2, ensure_ascii=False)

    self._dirty = False
    self._refresh_profile_list(select=name)
    self._show_view(VIEW_HOME)
```

- [ ] Implement `_save_mode`
- [ ] Handle capture-flow save (draft translation)
- [ ] Handle existing-mode save (preserve apps)
- [ ] Handle rename
- [ ] Navigate to home after save

### Task 4.3: Refresh the advanced editor

**File:** `config_ui.py` — fill in `_build_advanced` stub

Reuse most of the current detail-panel content (apps treeview, add/edit/remove/reorder) but restyled.

Must load from `self.profiles[self._current_profile]` (requires mode to be saved first or being edited).

Navigation:
- `"Back to mode details"` → `_show_view(VIEW_MODE_DETAIL)`
- `"Save"` → flush tree to `self.profiles[self._current_profile]["apps"]`, write file

- [ ] Implement `_build_advanced` based on current `_build_detail_panel` logic
- [ ] Restyle with updated theme
- [ ] Wire navigation and save

### Task 4.4: Add inline validation helper

**File:** `config_ui.py`

```python
def _show_field_warning(self, parent: tk.Frame, message: str) -> tk.Label:
    lbl = tk.Label(parent, text=message, bg=BG, fg="#e8a838", font=FONT_SM)
    lbl.pack(anchor="w", pady=(2, 0))
    return lbl
```

Apply to:
- Mode name (required, unique)
- App path (warn if not exists, non-blocking)

- [ ] Add `_show_field_warning` helper
- [ ] Apply to mode name in `_build_mode_detail`
- [ ] Apply to app paths where visible

---

## Story S5 — Test Mode + Documentation

**Scope:** Test-mode action from inside the UI, and README updates.
**Files touched:** `config_ui.py` (small addition), `launcher.py`, `README.md`
**Depends on:** S4 (save must work so there is a profile to test)
**Consumes:** Contract C4 (screen system), existing `execute_profile` from `launcher.py`

### Task 5.1: Add test-mode action

**File:** `config_ui.py`

Add a `"Test this mode"` button to `_build_mode_detail` and `_build_advanced`.

On click:
- Build a temporary profile dict from current form state (do not require save)
- If `self._draft_apps is not None`: translate drafts via `draft_to_profile_app`
- Call `execute_profile(profile)` from `launcher.py`
- Show brief status label: `"Launching {n} apps…"`

```python
from launcher import execute_profile
```

- [ ] Add test button to mode detail screen
- [ ] Add test button to advanced editor
- [ ] Implement `_test_current_mode` handler
- [ ] Show launch status

### Task 5.2: Update README

**File:** `README.md`

Add new sections after "Quick Start":
- **Creating a mode from your current desktop** — capture → review → save
- **Review step** — why VS Code folder and Chrome URLs need input
- **Advanced editor** — fallback for power users
- **Known limitations** — tabs not auto-imported, workspace not auto-detected

Update project structure to include `capture_service.py`.

- [ ] Write new sections
- [ ] Update project structure
- [ ] Keep all existing sections intact

---

## Parallelism Summary

| Story | Can start immediately | Blocked by | Produces | Consumes |
|-------|----------------------|------------|----------|----------|
| **S1** Capture Backend | Yes | Nothing | C2, C3 | Existing `window_manager` |
| **S2** UI Foundation | Yes | Nothing | C4 | Nothing new |
| **S3** Capture Flow UI | No | S1 + S2 | — | C1, C2, C4, C6 |
| **S4** Mode Details + Save | No | S2 | Save flow | C1, C2, C4, C5, C6 |
| **S5** Test + Docs | No | S4 | — | C4, `execute_profile` |

```
Time ──────────────────────────────────────────►

Agent A:  ████ S1 ████ ──── ████ S3 ████
Agent B:  ████ S2 ████ ──── ████ S4 ████ ── ██ S5 ██
```

---

## Decisions Locked In

- `profiles.json` schema stays unchanged (Contract C5)
- Capture produces draft state, never auto-saves
- Launch intent resolved during review, not guessed
- VS Code folder and Chrome URLs are the only app-specific behaviors in MVP
- Tkinter stays as UI framework
- One new file: `capture_service.py`
- `config_ui.py` refactored internally, not split into multiple files for MVP
- All cross-story interfaces are frozen in the Contracts section

## Risks

- Window detection may capture junk/system windows → mitigated by filtering
- Preset matching may be imperfect for odd window sizes → tolerance + fallback to coordinates
- Chrome tabs and VS Code workspace cannot be inferred reliably → resolved in review step
- Tkinter has a styling ceiling → acceptable for MVP, can revisit framework later

## Out of Scope for MVP

- Full Chrome tab/session recovery
- Automatic VS Code workspace detection from window state
- Pixel-perfect live monitor preview map
- Multi-step wizard state recovery on crash
- Deep app-specific integrations beyond VS Code and Chrome
