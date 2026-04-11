"""
WakeUp — Personal workspace launcher.
Main orchestrator: tray icon, hotkey registration, profile dispatch.
"""

import atexit
import json
import sys
import threading
import time
from pathlib import Path

# Optional imports - degrade gracefully
# Note: 'keyboard' (0.13.5) is unmaintained since 2020. Using pynput instead.
try:
    from pynput import keyboard as _kb
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False
    print("[WakeUp] 'pynput' not installed - hotkeys disabled.")

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False
    print("[WakeUp] 'pystray'/'Pillow' not installed - running without tray icon.")

from launcher import execute_profile
from audio_engine import AudioEngine


CONFIG_PATH = Path(__file__).parent / "profiles.json"


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def create_tray_icon() -> Image.Image:
    """Draw a sunrise / wake-up icon programmatically."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    accent = (0, 180, 255, 255)
    warm = (255, 180, 50, 255)

    # Horizon line
    d.line([(8, 40), (56, 40)], fill=accent, width=3)

    # Sun half-circle rising above horizon
    d.arc([18, 24, 46, 52], start=180, end=360, fill=warm, width=4)

    # Rays shooting upward from the sun center (x=32)
    d.line([(32, 20), (32, 8)], fill=warm, width=3)   # top
    d.line([(20, 24), (13, 14)], fill=warm, width=2)   # top-left
    d.line([(44, 24), (51, 14)], fill=warm, width=2)   # top-right

    # Small base lines below horizon to hint at a surface
    d.line([(12, 48), (52, 48)], fill=accent, width=2)
    d.line([(18, 54), (46, 54)], fill=accent, width=2)

    return img


class WakeUp:
    def __init__(self):
        self.config = load_config()
        self.profiles = self.config["profiles"]
        self.settings = self.config.get("settings", {})
        self._lock = threading.Lock()
        self._busy = False
        self._icon = None

        self.keyword_map: dict[str, str] = {}
        for name, profile in self.profiles.items():
            for kw in profile.get("trigger_keywords", []):
                self.keyword_map[kw.lower()] = name

        self.audio = AudioEngine(
            clap_settings=self.settings.get("clap_detection", {}),
            voice_settings=self.settings.get("voice", {}),
            on_clap=self._on_clap,
            on_keyword=self._on_keyword,
        )

    # ------------------------------------------------------------------ #
    #  Trigger handlers                                                    #
    # ------------------------------------------------------------------ #

    def _on_clap(self):
        default = self.settings.get("default_profile", "work")
        print(f"[WakeUp] Clap detected → launching profile '{default}'")
        self._trigger(default)

    def _on_keyword(self, keyword: str):
        profile_name = self.keyword_map.get(keyword.lower())
        if profile_name:
            print(f"[WakeUp] Keyword '{keyword}' → launching profile '{profile_name}'")
            self._trigger(profile_name)

    def _trigger(self, profile_name: str):
        with self._lock:
            if self._busy:
                return
            if profile_name not in self.profiles:
                print(f"[WakeUp] Unknown profile '{profile_name}'.")
                return
            self._busy = True

        def _run():
            try:
                profile = self.profiles[profile_name]
                msg = profile.get("message", f"Activating profile: {profile_name}.")
                print(f"[WakeUp] {msg}")
                execute_profile(profile)
            finally:
                with self._lock:
                    self._busy = False

        threading.Thread(target=_run, daemon=True).start()

    # ------------------------------------------------------------------ #
    #  Hotkey registration                                                 #
    # ------------------------------------------------------------------ #

    def _register_hotkeys(self):
        if not HAS_KEYBOARD:
            return

        # Convert "ctrl+alt+w" → "<ctrl>+<alt>+w" (pynput format)
        def _to_pynput(hk: str) -> str:
            parts = [p.strip().lower() for p in hk.split("+")]
            return "+".join(f"<{p}>" if len(p) > 1 else p for p in parts)

        hotkey_map = {}
        for name, profile in self.profiles.items():
            hk = profile.get("hotkey")
            if hk:
                pynput_hk = _to_pynput(hk)
                profile_name = name
                hotkey_map[pynput_hk] = lambda pn=profile_name: self._trigger(pn)

        if hotkey_map:
            listener = _kb.GlobalHotKeys(hotkey_map)
            listener.daemon = True
            listener.start()
            self._hotkey_listener = listener

    # ------------------------------------------------------------------ #
    #  Tray menu actions                                                   #
    # ------------------------------------------------------------------ #

    def _profile_tray_action(self, profile_name):
        def on_click(icon, item):
            self._trigger(profile_name)

        return on_click

    def _build_tray_menu(self):
        items = []
        for name in self.profiles:
            items.append(pystray.MenuItem(
                f"Launch: {name}",
                self._profile_tray_action(name),
            ))
        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem("Reload config", lambda icon, item: self._reload()))
        items.append(pystray.MenuItem("Exit WakeUp", lambda icon, item: self._shutdown()))
        return pystray.Menu(*items)

    def _reload(self):
        self.config = load_config()
        self.profiles = self.config["profiles"]
        self.settings = self.config.get("settings", {})
        self.keyword_map = {}
        for name, profile in self.profiles.items():
            for kw in profile.get("trigger_keywords", []):
                self.keyword_map[kw.lower()] = name
        if HAS_KEYBOARD and hasattr(self, "_hotkey_listener"):
            self._hotkey_listener.stop()
        self._register_hotkeys()
        self.audio.update_clap_settings(self.settings.get("clap_detection", {}))

    # ------------------------------------------------------------------ #
    #  Start                                                               #
    # ------------------------------------------------------------------ #

    def _shutdown(self, *_args):
        if getattr(self, "_shutting_down", False):
            return
        self._shutting_down = True
        if self._icon:
            self._icon.stop()
        self.audio.stop()

    def run(self):
        self._register_hotkeys()
        self.audio.start()

        atexit.register(self._shutdown)

        if HAS_TRAY:
            self._icon = pystray.Icon(
                "WakeUp",
                create_tray_icon(),
                "WakeUp",
                self._build_tray_menu(),
            )
            def _on_tray_ready(icon):
                icon.visible = True

            self._icon.run(setup=_on_tray_ready)
        else:
            print("[WakeUp] Running in console mode. Press Ctrl+C to exit.")
            print("         Available profiles:", list(self.profiles.keys()))
            try:
                while True:
                    cmd = input("wakeup> ").strip().lower()
                    if cmd in ("exit", "quit"):
                        break
                    elif cmd in self.profiles:
                        self._trigger(cmd)
                    elif cmd == "reload":
                        self._reload()
                    elif cmd:
                        self._on_keyword(cmd)
            except KeyboardInterrupt:
                pass

        self._shutdown()


if __name__ == "__main__":
    WakeUp().run()
