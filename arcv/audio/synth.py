"""Procedural bleep synthesis — no audio asset files.

Generates short UI blips (sine/square/triangle/chirp/noise) as float32 mono
numpy arrays in [-1, 1], plus a named bank of HUD bleeps and WAV helpers.
"""

from __future__ import annotations

import io
import wave
from typing import Dict, List, Tuple

import numpy as np

SR = 44100


def _env(n: int, attack: float, release: float, sr: int) -> np.ndarray:
    e = np.ones(n, dtype=np.float32)
    a = max(1, int(attack * sr))
    r = max(1, int(release * sr))
    if a < n:
        e[:a] = np.linspace(0.0, 1.0, a, dtype=np.float32)
    if r < n:
        e[-r:] = np.linspace(1.0, 0.0, r, dtype=np.float32)
    return e


def tone(freq: float, dur: float, shape: str = "sine", vol: float = 0.5,
         attack: float = 0.005, release: float = 0.05, sr: int = SR) -> np.ndarray:
    n = max(1, int(dur * sr))
    t = np.arange(n, dtype=np.float32) / sr
    ph = 2.0 * np.pi * freq * t
    if shape == "square":
        w = np.sign(np.sin(ph))
    elif shape == "tri":
        w = (2.0 / np.pi) * np.arcsin(np.sin(ph))
    elif shape == "saw":
        w = 2.0 * (freq * t - np.floor(0.5 + freq * t))
    else:
        w = np.sin(ph)
    return (w.astype(np.float32) * _env(n, attack, release, sr) * vol)


def chirp(f0: float, f1: float, dur: float, shape: str = "sine", vol: float = 0.5,
          attack: float = 0.005, release: float = 0.05, sr: int = SR) -> np.ndarray:
    n = max(1, int(dur * sr))
    t = np.arange(n, dtype=np.float32) / sr
    freq = np.linspace(f0, f1, n, dtype=np.float32)
    ph = 2.0 * np.pi * np.cumsum(freq) / sr
    if shape == "square":
        w = np.sign(np.sin(ph))
    elif shape == "tri":
        w = (2.0 / np.pi) * np.arcsin(np.sin(ph))
    else:
        w = np.sin(ph)
    return (w.astype(np.float32) * _env(n, attack, release, sr) * vol)


def noise(dur: float, vol: float = 0.3, attack: float = 0.002, release: float = 0.03, sr: int = SR) -> np.ndarray:
    n = max(1, int(dur * sr))
    rng = np.random.default_rng(1234)
    w = rng.uniform(-1.0, 1.0, n).astype(np.float32)
    return w * _env(n, attack, release, sr) * vol


def mix(*sigs: np.ndarray) -> np.ndarray:
    n = max(len(s) for s in sigs)
    out = np.zeros(n, dtype=np.float32)
    for s in sigs:
        out[: len(s)] += s
    return out


def build_bank(volume: float = 0.5, sr: int = SR) -> Dict[str, np.ndarray]:
    v = volume
    return {
        "assemble": chirp(420, 920, 0.09, "square", 0.5 * v, sr=sr),
        "type": tone(1300, 0.018, "sine", 0.28 * v, attack=0.001, release=0.012, sr=sr),
        "decipher": mix(noise(0.045, 0.18 * v, sr=sr), tone(900, 0.045, "square", 0.18 * v, sr=sr)),
        "lock": mix(tone(680, 0.12, "square", 0.4 * v, sr=sr),
                    tone(1120, 0.12, "sine", 0.3 * v, attack=0.04, sr=sr)),
        "panel": tone(220, 0.11, "tri", 0.5 * v, release=0.08, sr=sr),
        "action": tone(880, 0.05, "square", 0.35 * v, sr=sr),
        "exit": chirp(820, 280, 0.13, "square", 0.4 * v, sr=sr),
        "scan": tone(600, 0.06, "sine", 0.22 * v, sr=sr),
        "error": mix(chirp(440, 130, 0.26, "square", 0.4 * v, sr=sr), noise(0.26, 0.12 * v, sr=sr)),
        "alert": mix(tone(300, 0.18, "square", 0.35 * v, sr=sr), tone(305, 0.18, "square", 0.25 * v, sr=sr)),
    }


def to_int16(samples: np.ndarray) -> np.ndarray:
    return (np.clip(samples, -1.0, 1.0) * 32767.0).astype(np.int16)


def to_wav_bytes(samples: np.ndarray, sr: int = SR) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(to_int16(samples).tobytes())
    return buf.getvalue()


def save_wav(path: str, samples: np.ndarray, sr: int = SR) -> None:
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(to_int16(samples).tobytes())


def render_timeline(cues: List[Tuple[float, str]], duration: float,
                    bank: Dict[str, np.ndarray], sr: int = SR) -> np.ndarray:
    """Mix a list of (time_seconds, bleep_name) cues into one float32 track."""
    track = np.zeros(int(duration * sr) + sr // 10, dtype=np.float32)
    for (t, name) in cues:
        s = bank.get(name)
        if s is None:
            continue
        i = int(t * sr)
        end = min(len(track), i + len(s))
        if i < len(track):
            track[i:end] += s[: end - i]
    peak = float(np.max(np.abs(track))) if track.size else 0.0
    if peak > 1.0:
        track /= peak
    return track
