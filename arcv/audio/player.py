"""Non-blocking audio playback backends.

Prefers sounddevice (real mixing/overlap), falls back to winsound (Windows
stdlib, one sound at a time), then a silent null backend. Always degrades
gracefully when no audio device is present (e.g. headless/CI).
"""

from __future__ import annotations

import threading

import numpy as np

from .synth import SR, to_wav_bytes


class _NullBackend:
    def play(self, samples: np.ndarray) -> None:
        pass

    def close(self) -> None:
        pass


class _WinSoundBackend:
    def __init__(self, sr: int = SR) -> None:
        import winsound  # noqa: F401  (Windows only)
        self._winsound = winsound
        self.sr = sr

    def play(self, samples: np.ndarray) -> None:
        data = to_wav_bytes(samples, self.sr)
        self._winsound.PlaySound(
            data, self._winsound.SND_MEMORY | self._winsound.SND_ASYNC
        )

    def close(self) -> None:
        try:
            self._winsound.PlaySound(None, self._winsound.SND_PURGE)
        except Exception:  # noqa: BLE001
            pass


class _SoundDeviceBackend:
    """Software mixer over a sounddevice output stream (supports overlap)."""

    def __init__(self, sr: int = SR, max_voices: int = 16) -> None:
        import sounddevice as sd

        self.sr = sr
        self.max_voices = max_voices
        self._voices = []  # list of [samples, pos]
        self._lock = threading.Lock()
        self._stream = sd.OutputStream(
            samplerate=sr, channels=1, dtype="float32", blocksize=256, callback=self._cb
        )
        self._stream.start()

    def _cb(self, outdata, frames, time_info, status) -> None:  # noqa: ANN001
        out = np.zeros(frames, dtype=np.float32)
        with self._lock:
            keep = []
            for v in self._voices:
                s, pos = v
                end = min(len(s), pos + frames)
                chunk = s[pos:end]
                out[: len(chunk)] += chunk
                v[1] = end
                if end < len(s):
                    keep.append(v)
            self._voices = keep
        np.clip(out, -1.0, 1.0, out=out)
        outdata[:, 0] = out

    def play(self, samples: np.ndarray) -> None:
        with self._lock:
            if len(self._voices) >= self.max_voices:
                self._voices.pop(0)
            self._voices.append([samples.astype(np.float32), 0])

    def close(self) -> None:
        try:
            self._stream.stop()
            self._stream.close()
        except Exception:  # noqa: BLE001
            pass


def make_player(sr: int = SR):
    """Return the best available non-blocking player, or a null backend."""
    try:
        return _SoundDeviceBackend(sr)
    except Exception:  # noqa: BLE001
        pass
    try:
        import sys
        if sys.platform.startswith("win"):
            return _WinSoundBackend(sr)
    except Exception:  # noqa: BLE001
        pass
    return _NullBackend()
