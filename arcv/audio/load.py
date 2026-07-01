"""Load the real Arwes bleep sounds and map them to ARCV HUD events.

Arwes ships its bleeps as mp3/webm assets (hover, type, click, error, intro,
assemble, info, open, close). We decode them to float32 mono PCM with ffmpeg
(already required for MP4 export) — no extra Python deps — and fall back to the
synthesized bank for anything missing, so audio still works without ffmpeg or
the files.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import urllib.request
import wave
from pathlib import Path
from typing import Dict, Optional

import numpy as np

from . import synth

# Arwes bleep asset names available at next.arwes.dev/assets/sounds/<name>.mp3
ARWES_SOUND_NAMES = ["hover", "type", "click", "error", "intro", "assemble", "info", "open", "close"]
_ARWES_BASE = "https://next.arwes.dev/assets/sounds"

# ARCV HUD event -> Arwes sound file name
ARWES_MAP = {
    "assemble": "assemble",
    "type": "type",
    "action": "click",
    "lock": "intro",
    "panel": "open",
    "decipher": "info",
    "scan": "hover",
    "exit": "close",
    "error": "error",   # target lost
    "alert": "error",
}
# rapid-fire events get trimmed so repeats don't smear
_RAPID = {"type", "scan", "hover"}


def default_sounds_dir() -> str:
    env = os.environ.get("ARCV_SOUNDS_DIR")
    if env and Path(env).is_dir():
        return env
    return str(Path(__file__).resolve().parent.parent / "resources" / "sounds")


def download_arwes_sounds(dest: Optional[str] = None) -> str:
    """Download the Arwes bleep mp3s into ``dest`` (defaults to resources/sounds)."""
    dest = dest or default_sounds_dir()
    Path(dest).mkdir(parents=True, exist_ok=True)
    for n in ARWES_SOUND_NAMES:
        urllib.request.urlretrieve(f"{_ARWES_BASE}/{n}.mp3", os.path.join(dest, f"{n}.mp3"))
    return dest


def decode_audio(path: str, sr: int = synth.SR) -> Optional[np.ndarray]:
    """Decode any audio file to float32 mono at ``sr`` via ffmpeg. Returns None
    if the file/ffmpeg is missing or decoding fails."""
    if not os.path.isfile(path):
        return None
    ff = shutil.which("ffmpeg")
    if ff is None:
        if path.lower().endswith(".wav"):
            try:
                with wave.open(path, "rb") as w:
                    raw = w.readframes(w.getnframes())
                    a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                    if w.getnchannels() > 1:
                        a = a.reshape(-1, w.getnchannels()).mean(axis=1)
                    return a
            except Exception:  # noqa: BLE001
                return None
        return None
    try:
        out = subprocess.run(
            [ff, "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        ).stdout
        a = np.frombuffer(out, dtype="<f4").astype(np.float32).copy()
        return a if a.size else None
    except Exception:  # noqa: BLE001
        return None


def _trim(s: np.ndarray, dur: float, sr: int) -> np.ndarray:
    n = int(dur * sr)
    if len(s) <= n:
        return s
    s = s[:n].copy()
    r = max(1, int(n * 0.25))
    s[-r:] *= np.linspace(1.0, 0.0, r, dtype=np.float32)
    return s


def load_arwes_bank(sr: int = synth.SR, volume: float = 0.6,
                    sounds_dir: Optional[str] = None) -> Dict[str, np.ndarray]:
    """Bank keyed by ARCV event names, using real Arwes sounds where available
    and synthesized bleeps as fallback."""
    bank = synth.build_bank(volume, sr)  # fallback for every event
    d = sounds_dir or default_sounds_dir()
    for ev, fname in ARWES_MAP.items():
        s = decode_audio(os.path.join(d, f"{fname}.mp3"), sr)
        if s is None:
            continue
        if ev in _RAPID:
            s = _trim(s, 0.2, sr)
        bank[ev] = s * volume
    return bank


def arwes_available(sounds_dir: Optional[str] = None) -> bool:
    d = sounds_dir or default_sounds_dir()
    return shutil.which("ffmpeg") is not None and any(
        Path(d, f"{n}.mp3").is_file() for n in ARWES_SOUND_NAMES
    )
