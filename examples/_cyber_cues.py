"""Bleep cue list for the Cyberpunk HUD boot sequence — (time_s, bleep_name)
timed to match cyberpunk_layout's stagger schedule. Used for both live playback
and the muxed MP4 audio track."""

from __future__ import annotations

import numpy as np

BOOT_CUES = [
    (0.00, "assemble"),  # title bracket
    (0.12, "decipher"),  # title text
    (0.20, "assemble"),  # scanner top bar
    (0.27, "assemble"),  # corners
    (0.35, "assemble"),
    (0.32, "scan"),      # face matching flicker
    (0.42, "assemble"),  # wings
    (0.60, "lock"),      # reticle forms
    (0.64, "type"), (0.72, "type"), (0.80, "type"), (0.88, "type"),  # SCANNING type-on
    (0.82, "panel"),     # threat panel
    (0.86, "lock"),      # red target box
    (1.00, "decipher"),  # MEDIUM
    (1.02, "decipher"),  # terminal #234
    (1.16, "decipher"),  # POISON
    (1.22, "type"), (1.34, "type"), (1.46, "type"),  # terminal rows
    (1.28, "scan"), (1.36, "scan"), (1.44, "scan"), (1.52, "scan"),  # triangles
    (1.42, "action"), (1.54, "action"), (1.66, "action"),  # LS / X / Y
    (1.55, "assemble"),  # antenna plane
]


def cues_for(duration: float):
    """Boot cues plus a subtle idle scan tick once assembled."""
    cues = list(BOOT_CUES)
    t = 2.6
    while t < duration:
        cues.append((round(t, 2), "scan"))
        t += 0.95
    return cues
