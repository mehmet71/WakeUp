# WakeUp — CLAUDE.md

## Project Overview

WakeUp is a personal workspace launcher for Windows. It monitors audio (voice keywords) and hotkeys, then spawns and positions apps defined in profile configs.

## Architecture

```
wakeup.py          ← Orchestrator: tray icon, hotkey registration, profile dispatch
audio_engine.py    ← VoiceListener (Vosk) + AudioEngine wrapper
launcher.py        ← Process spawning + hands off to window_manager for arrangement
window_manager.py  ← Monitor detection, preset layout math, win32 window positioning
capture_service.py ← Desktop snapshot → draft app records for profile creation
config_ui.py       ← UI for editing profiles
profiles.json      ← User configuration (profiles + settings)
```

## Key Design Decisions

- **All optional dependencies degrade gracefully.** `pynput`, `pystray`, `sounddevice`, `vosk`, `pywin32` each have a `HAS_X` guard. Missing packages disable the feature but don't crash the app.
- **Voice uses Windows default mic.** VoiceListener opens on the system default input device via sounddevice. No device selection needed.
- **Threading model.** Profile execution runs on a daemon thread. A `_busy` lock prevents double-triggers. Window arrangement is always async (own thread per app).
- **Hotkeys use pynput** (not the `keyboard` library, which is unmaintained).

## profiles.json Schema

```json
{
  "settings": {
    "default_profile": "work",
    "voice": {
      "enabled": false,
      "model_path": "models/vosk-model-small-en-us",
      "sample_rate": 16000
    }
  },
  "profiles": {
    "<name>": {
      "trigger_keywords": ["..."],
      "hotkey": "ctrl+alt+w",
      "message": "...",
      "apps": [
        {
          "name": "VS Code",
          "path": "%LOCALAPPDATA%/Programs/Microsoft VS Code/Code.exe",
          "args": ["C:/Projects"],
          "delay": 0,
          "window": {
            "monitor": 0,
            "preset": "left-two-thirds"
          }
        }
      ]
    }
  }
}
```

**Window config options:**
- `preset` (string) — one of the named presets below
- `x/y/w/h` (int) — explicit coords relative to monitor top-left
- `monitor` (int) — 0 = primary, 1 = secondary
- `maximize` (bool) — optional, forces maximize after positioning

**Available presets:**
`full`, `left-half`, `right-half`, `top-half`, `bottom-half`,
`top-left`, `top-right`, `bottom-left`, `bottom-right`,
`left-third`, `center-third`, `right-third`,
`left-two-thirds`, `right-two-thirds`

## Dependencies

See `requirements.txt`. Key packages:
- `sounddevice` — audio streaming (WASAPI)
- `pynput` — global hotkeys
- `pystray` + `Pillow` — tray icon
- `pywin32` — window positioning
- `vosk` — optional, offline voice recognition

Do not add/remove/upgrade dependencies without approval.

## Running

```bash
python wakeup.py
```

Requires running terminal as Administrator at least once (pynput global hotkeys need elevated rights).

## Tests

Tests live in `tests/`. Run with:
```bash
python -m pytest tests/
```

## Current Roadmap State

- Phase 1 ✅ Profile-based launcher (hotkey + voice keywords)
- Phase 2 ✅ Window arrangement with multi-monitor support
- Phase 3 ✅ Capture-based mode creation (snapshot desktop → review → save)
- Phase 4 🔲 Local voice agent (Whisper STT + LLM + TTS)
