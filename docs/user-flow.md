# WakeUp — User Flow

How a user discovers, sets up, and grows into the app over time.

---

## Stage 1: Install & First Run

**User:** Clones the repo, runs `pip install -r requirements.txt`, then `python wakeup.py`.

**What happens:**
- A tray icon appears in the bottom-right taskbar.
- The app loads `profiles.json` with the four default profiles (work, focus, creative, gaming).
- Hotkeys are registered globally. Voice detection is off by default (no Vosk model yet).

**User's first impression:**
> "It's running. Nothing visible except the tray icon."

They right-click the tray to explore. They see their profiles listed under "Launch: …".

---

## Stage 2: First Launch — Tray or Hotkey

**User:** Wants to try it. They either:
- Right-click the tray → "Launch: work", or
- Press `Ctrl+Alt+W` (the default work hotkey).

**What happens:**
- VS Code, Chrome, and Outlook open.
- Each window moves to the configured monitor and snaps to its preset layout.
- The terminal prints the startup message: *"Good morning. Initializing work environment."*

**User's reaction:**
> "Oh. That actually worked."

They notice the apps opened in the right positions. They start thinking about their own layout.

---

## Stage 3: Customizing Profiles — Config UI

**User:** The default profiles don't match their actual apps or preferred layouts. They open the config editor:

```bash
python config_ui.py
```

**What they do:**
- Edit the "work" profile: swap Outlook for their actual mail client, change Chrome's preset from `right-third` to `right-half`.
- Change VS Code's path to their actual Projects folder.
- Add a second app (e.g. Spotify in the corner).
- Reassign a hotkey.
- Save and test with `Ctrl+Alt+W` again.

**User's reaction:**
> "Now it's actually my setup."

---

## Stage 4: Day-to-Day Usage — Hotkeys

**User:** WakeUp is now part of their daily routine. They've added a shortcut to auto-start it with Windows (via `shell:startup`).

**Typical session:**
1. PC boots → WakeUp silently starts in the tray.
2. User sits down, presses `Ctrl+Alt+W`.
3. Their full work environment appears, arranged and ready.
4. Later, `Ctrl+Alt+F` for a distraction-free focus session.

**The app is invisible when it's working well.** They only notice the tray icon if they need to reload config or exit.

---

## Stage 5: Voice Keywords (Optional)

**User:** They've read the README and decide to try voice triggers.

**Setup:**
1. Download a Vosk model (~50 MB).
2. Extract to `models/vosk-model-small-en-us`.
3. In `profiles.json`, set `"voice": { "enabled": true, ... }`.
4. Restart the app.

**Usage:**
- They're making coffee and say *"wake up"* or *"work mode"* — their environment appears before they sit down.
- They add a personal trigger phrase in `trigger_keywords`, like *"let's go"*.

**User's reaction:**
> "Now I feel like I have a computer from a sci-fi movie."

---

## Stage 6: Adding Custom Profiles — Manual

**User:** They realize they want a "meeting mode" — just their calendar and a notes app, no distractions.

**What they do in the config UI:**
1. Click `+ New mode`.
2. Choose "Manual setup".
3. Name it "meeting".
4. Set hotkey: `Ctrl+Alt+M`.
5. Add two apps (calendar + notes), pick layout presets.
6. Add keywords: *"meeting mode"*, *"show calendar"*.
7. Save.

Now `Ctrl+Alt+M` or saying *"meeting mode"* arranges that layout instantly.

---

## Stage 7: Capture-Based Mode Creation

**User:** They've arranged their apps exactly how they like for a new workflow. Instead of recreating it manually, they:

1. Open the config UI → click `+ New mode` → "Capture current setup".
2. The app snapshots all open windows: reads their positions, monitors, and executables.
3. They review the draft: confirm each app, set VS Code's folder, add Chrome URLs.
4. Name the mode, set a hotkey, save.

**The layout they just created manually is now a repeatable, one-keystroke setup.**

---

## Summary: Progressive Complexity

| Stage | What they learn | Time investment |
|-------|----------------|-----------------|
| 1 — Install & run | App starts, tray icon appears | 5 min |
| 2 — First launch | Hotkeys and tray work | 1 min |
| 3 — Config UI | Profiles match their real setup | 15–30 min |
| 4 — Daily use | Muscle memory for hotkeys | Ongoing |
| 5 — Voice (optional) | Hands-free triggers | 10 min setup |
| 6 — New profiles | Custom modes for any context | 5 min each |
| 7 — Capture | Snapshot real layouts instantly | 2 min |

The app earns trust at Stage 2, becomes genuinely useful at Stage 3, and becomes indispensable at Stage 4.
