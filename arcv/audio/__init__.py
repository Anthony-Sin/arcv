"""Synthesized HUD audio (bleeps).

Live, event-driven playback via :class:`Bleeps`; a :class:`CueScheduler` for
known timelines; and :func:`render_track` to bake a cue list into an audio track
for muxing onto an exported video.
"""

from . import synth
from .bleeps import Bleeps, CueScheduler, render_track
from .player import make_player
from .synth import build_bank, save_wav
from .load import (
    load_arwes_bank,
    download_arwes_sounds,
    decode_audio,
    arwes_available,
    ARWES_MAP,
)

__all__ = [
    "Bleeps",
    "CueScheduler",
    "render_track",
    "make_player",
    "build_bank",
    "save_wav",
    "synth",
    "load_arwes_bank",
    "download_arwes_sounds",
    "decode_audio",
    "arwes_available",
    "ARWES_MAP",
]
