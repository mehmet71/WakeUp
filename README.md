# WakeUp — Personal Workspace Launcher

Your personal workspace launcher.

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

> Run your terminal as Administrator once during first setup — `pynput`
> needs elevated rights to register global hotkeys.

### 2. Configure your profiles

Edit `profiles.json`. Each profile has:

```json
"work": {
  "trigger_keywords": ["wake up", "work mode"],
  "hotkey": "ctrl+alt+w",
  "message": "Good morning.",
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
```

**Path tips**
- Use `%LOCALAPPDATA%`, `%APPDATA%`, `%PROGRAMFILES%` env vars freely
- Find exact paths: right-click any shortcut → Properties → Target

**Window presets**
```
full             left-half / right-half    top-half / bottom-half
top-left / top-right / bottom-left / bottom-right
left-third / center-third / right-third
left-two-thirds / right-two-thirds
```

Or use exact pixel coords:
```json
"window": {"monitor": 0, "x": 0, "y": 0, "w": 1920, "h": 1080}
```

**Monitor index**: 0 = primary, 1 = secondary, etc.

### 3. Run

```bash
python wakeup.py
```

A tray icon appears (bottom-right taskbar). Right-click for the menu.

---

## Triggers

| Trigger | How |
|---------|-----|
| Voice keyword | Say any phrase in `trigger_keywords` (requires Vosk, see below) |
| Hotkey | Press the hotkey defined in the profile |
| Tray menu | Right-click the tray icon |
| Console | Type the profile name when running without tray |

---

## Voice Commands (optional)

1. Uncomment `vosk` in `requirements.txt` and run `pip install vosk`
2. Download a model: https://alphacephei.com/vosk/models
   - English: `vosk-model-small-en-us-0.15` (~50 MB, fast)
   - German: `vosk-model-small-de-0.15`
3. Extract to `models/vosk-model-small-en-us`
4. In `profiles.json` → `settings.voice`:
   ```json
   "enabled": true,
   "model_path": "models/vosk-model-small-en-us"
   ```

---

## Auto-start with Windows

1. Press `Win + R` → type `shell:startup` → Enter
2. Create a shortcut to `wakeup.py` (or a `.bat` file) in that folder

`.bat` example:
```bat
@echo off
cd /d C:\path\to\WakeUp
python wakeup.py
```

---

## Project Structure

```
WakeUp/
├── wakeup.py          ← Main entry point & orchestrator
├── audio_engine.py    ← Vosk voice keyword listener
├── launcher.py        ← App spawning + window arrangement trigger
├── window_manager.py  ← Monitor detection, presets, win32 positioning
├── config_ui.py       ← Visual config editor
├── capture_service.py ← Desktop snapshot → draft mode records
├── profiles.json      ← Your configuration
├── requirements.txt
└── models/            ← Place Vosk models here (optional)
```

---

## Roadmap

- [x] Phase 1 — Profile-based app launcher (hotkey + voice keywords)
- [x] Phase 2 — Window arrangement with multi-monitor support
- [ ] Phase 3 — Capture-based mode creation (snapshot current desktop → new mode)
- [ ] Phase 4 — Local voice agent (Whisper STT + LLM + TTS)
