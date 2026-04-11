"""
Audio Engine: Clap detection + always-on voice keyword listener (Vosk).

Clap detection uses RMS amplitude spikes on the microphone stream.
Voice uses Vosk for fully local, offline keyword spotting.

Vosk model download (small ~50MB English):
  https://alphacephei.com/vosk/models  →  vosk-model-small-en-us-0.15
  Extract to:  models/vosk-model-small-en-us
"""

import json
import threading
import time
from pathlib import Path
from typing import Callable, Optional

import numpy as np

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


class ClapDetector:
    """
    Detects N consecutive claps within a time window.
    Fires on_clap() callback when the pattern is matched.
    """

    def __init__(
        self,
        on_clap: Callable,
        threshold: float = 0.15,
        claps_required: int = 2,
        window_ms: int = 900,
        debounce_ms: int = 120,
        cooldown_s: float = 2.0,
        sample_rate: int = 44100,
        device: int | str | None = None,
    ):
        self.on_clap = on_clap
        self.threshold = threshold
        self.claps_required = claps_required
        self.window_ms = window_ms / 1000
        self.debounce_ms = debounce_ms / 1000
        self.cooldown_s = cooldown_s
        self.sample_rate = sample_rate
        self._device = device

        self._clap_times: list[float] = []
        self._last_trigger: float = 0
        self._in_clap: bool = False
        self._stream = None
        self._callback_count: int = 0

    def _audio_callback(self, indata, frames, time_info, status):
        self._callback_count += 1
        normalized = indata.astype(np.float32) / 32768.0
        rms = float(np.sqrt(np.mean(normalized ** 2)))
        now = time.monotonic()

        if rms > self.threshold:
            if not self._in_clap:
                self._in_clap = True
                if not self._clap_times or (now - self._clap_times[-1]) > self.debounce_ms:
                    self._clap_times.append(now)
                    cutoff = now - self.window_ms
                    self._clap_times = [t for t in self._clap_times if t >= cutoff]

                    if (
                        len(self._clap_times) >= self.claps_required
                        and now - self._last_trigger > self.cooldown_s
                    ):
                        self._last_trigger = now
                        self._clap_times = []
                        threading.Thread(target=self.on_clap, daemon=True).start()
        else:
            self._in_clap = False

    def _resolve_device(self) -> int | None:
        """Resolve self._device (name substring, index, or None) to a device index."""
        if self._device is None:
            return None
        if isinstance(self._device, int):
            return self._device
        name = str(self._device).lower()
        for i, d in enumerate(sd.query_devices()):
            if d['max_input_channels'] > 0 and name in d['name'].lower():
                return i
        return None

    def _check_stream_health(self):
        """Warn the user if the selected device delivers no audio."""
        time.sleep(3)
        if self._callback_count > 0:
            return
        devices = []
        for i, d in enumerate(sd.query_devices()):
            if d['max_input_channels'] > 0:
                devices.append(f"  {i}: {d['name']}")
        device_list = "\n".join(devices)
        print(
            f"\n[ClapDetector] WARNING: No audio received from the current input device.\n"
            f"  Set \"device\" in profiles.json → settings → clap_detection.\n"
            f"  Use a device index or a name substring, e.g. \"device\": \"WH-1000XM5\"\n\n"
            f"  Available input devices:\n{device_list}\n"
        )

    def start(self):
        if not HAS_SD:
            return
        try:
            device_idx = self._resolve_device()
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=512,
                callback=self._audio_callback,
                device=device_idx,
            )
            self._stream.start()
            device_name = sd.query_devices(device_idx or sd.default.device[0], 'input')['name']
            print(f"[ClapDetector] Listening on: {device_name}")
            threading.Thread(target=self._check_stream_health, daemon=True).start()
        except Exception as e:
            print(f"[ClapDetector] Failed to open audio device: {e}")

    def stop(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def update_threshold(self, value: float):
        self.threshold = value


class VoiceListener:
    """
    Always-on keyword listener using Vosk (fully local, no cloud).
    Fires on_keyword(keyword) when a registered phrase is heard.

    keywords_map: dict mapping phrase -> profile_name or any string
    (the caller decides what to do with it)
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
    """
    Combines ClapDetector + VoiceListener into a single interface.
    Reads settings from the config dict.
    """

    def __init__(
        self,
        clap_settings: dict,
        voice_settings: dict,
        on_clap: Callable,
        on_keyword: Callable[[str], None],
    ):
        self._clap: Optional[ClapDetector] = None
        self._voice: Optional[VoiceListener] = None

        if clap_settings.get("enabled", True):
            self._clap = ClapDetector(
                on_clap=on_clap,
                threshold=clap_settings.get("threshold", 0.25),
                claps_required=clap_settings.get("claps_required", 2),
                window_ms=clap_settings.get("window_ms", 900),
                cooldown_s=clap_settings.get("cooldown_s", 2.0),
                device=clap_settings.get("device"),
            )

        if voice_settings.get("enabled", False):
            model_path = voice_settings.get("model_path", "models/vosk-model-small-en-us")
            self._voice = VoiceListener(
                model_path=model_path,
                on_keyword=on_keyword,
                sample_rate=voice_settings.get("sample_rate", 16000),
            )

    def start(self):
        if self._clap:
            self._clap.start()
        if self._voice:
            self._voice.start()

    def stop(self):
        if self._clap:
            self._clap.stop()
        if self._voice:
            self._voice.stop()

    def set_clap_threshold(self, value: float):
        """Live-tune clap sensitivity (0.0 - 1.0). Lower = more sensitive."""
        if self._clap:
            self._clap.update_threshold(value)

    def update_clap_settings(self, clap_settings: dict):
        if not self._clap:
            return
        self._clap.threshold = clap_settings.get("threshold", self._clap.threshold)
        self._clap.claps_required = clap_settings.get("claps_required", self._clap.claps_required)
        self._clap.window_ms = clap_settings.get("window_ms", self._clap.window_ms * 1000) / 1000
        self._clap.cooldown_s = clap_settings.get("cooldown_s", self._clap.cooldown_s)
