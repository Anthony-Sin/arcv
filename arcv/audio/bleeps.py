"""Bleeps — a named bank of synthesized HUD sounds with live playback and an
offline cue scheduler / timeline mixer for video export.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np

from . import synth
from .load import load_arwes_bank
from .player import make_player

Cue = Tuple[float, str]  # (time_seconds, bleep_name)


def _make_bank(source: str, volume: float, sr: int):
    if source == "arwes":
        return load_arwes_bank(sr, volume)  # real Arwes sounds, synth fallback
    return synth.build_bank(volume, sr)


class Bleeps:
    """Live, event-driven bleeps. ``play(name)`` is non-blocking.

    ``source="arwes"`` uses the real Arwes bleep sounds (decoded from the bundled
    mp3s via ffmpeg), falling back to synthesized blips for anything unavailable.
    """

    def __init__(self, volume: float = 0.5, sr: int = synth.SR, enabled: bool = True,
                 player=None, source: str = "synth") -> None:
        self.sr = sr
        self.enabled = enabled
        self.bank = _make_bank(source, volume, sr)
        self._player = player if player is not None else (make_player(sr) if enabled else None)

    def play(self, name: str) -> None:
        if not self.enabled or self._player is None:
            return
        s = self.bank.get(name)
        if s is not None:
            self._player.play(s)

    def close(self) -> None:
        if self._player is not None:
            self._player.close()


class CueScheduler:
    """Fires a fixed cue list as a clock advances (for known timelines, e.g. a
    boot sequence). Call ``update(time)`` each frame."""

    def __init__(self, bleeps: Bleeps, cues: List[Cue]) -> None:
        self.bleeps = bleeps
        self.cues = sorted(cues, key=lambda c: c[0])
        self._i = 0

    def reset(self) -> None:
        self._i = 0

    def update(self, time: float) -> None:
        while self._i < len(self.cues) and self.cues[self._i][0] <= time:
            self.bleeps.play(self.cues[self._i][1])
            self._i += 1


def render_track(cues: List[Cue], duration: float, volume: float = 0.5,
                 sr: int = synth.SR, source: str = "synth") -> np.ndarray:
    """Mix a cue list into one float32 audio track (for muxing into a video).

    ``source="arwes"`` uses the real Arwes sounds (synth fallback)."""
    bank = _make_bank(source, volume, sr)
    return synth.render_timeline(cues, duration, bank, sr)
