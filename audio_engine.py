"""
Audio Engine: Always-on voice keyword listener (Vosk).

Vosk model download (small ~50MB English):
  https://alphacephei.com/vosk/models  →  vosk-model-small-en-us-0.15
  Extract to:  models/vosk-model-small-en-us
"""

import json
import threading
from pathlib import Path
from typing import Callable, Optional

try:
    import sounddevice as sd
    HAS_SD = True
except ImportError:
    HAS_SD = False
    print("[AudioEngine] 'sounddevice' not installed - audio disabled.")

try:
    from vosk import Model, KaldiRecognizer
    HAS_VOSK = True
except ImportError:
    HAS_VOSK = False
    print("[AudioEngine] 'vosk' not installed - voice keyword detection disabled.")


class VoiceListener:
    """
    Always-on keyword listener using Vosk (fully local, no cloud).
    Fires on_keyword(keyword) when a registered phrase is heard.
    """

    def __init__(
        self,
        model_path: str,
        on_keyword: Callable[[str], None],
        sample_rate: int = 16000,
    ):
        self.on_keyword = on_keyword
        self.sample_rate = sample_rate
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._recognizer: Optional[object] = None

        if not HAS_VOSK or not HAS_SD:
            return

        if not Path(model_path).exists():
            print(
                f"[VoiceListener] Model not found at '{model_path}'.\n"
                "  Download from https://alphacephei.com/vosk/models\n"
                "  and extract to the path above. Voice disabled for now."
            )
            return

        model = Model(model_path)
        self._recognizer = KaldiRecognizer(model, sample_rate)

    def start(self):
        if not self._recognizer:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="VoiceListener")
        self._thread.start()

    def _listen_loop(self):
        try:
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=4000,
            ) as stream:
                while self._running:
                    data, _ = stream.read(4000)
                    if self._recognizer.AcceptWaveform(bytes(data)):
                        result = json.loads(self._recognizer.Result())
                        text = result.get("text", "").strip().lower()
                        if text:
                            threading.Thread(
                                target=self.on_keyword,
                                args=(text,),
                                daemon=True,
                            ).start()
        except Exception as e:
            print(f"[VoiceListener] Error: {e}")

    def stop(self):
        self._running = False


class AudioEngine:
    """Manages VoiceListener lifecycle."""

    def __init__(
        self,
        voice_settings: dict,
        on_keyword: Callable[[str], None],
    ):
        self._voice: Optional[VoiceListener] = None
        if voice_settings.get("enabled", False):
            self._voice = VoiceListener(
                model_path=voice_settings.get("model_path", "models/vosk-model-small-en-us"),
                on_keyword=on_keyword,
                sample_rate=voice_settings.get("sample_rate", 16000),
            )

    def start(self):
        if self._voice:
            self._voice.start()

    def stop(self):
        if self._voice:
            self._voice.stop()
