"""Overlay UI kit — lay out Arwes-style HUD elements at fixed positions and
render them through ARCV's bloom/composite pipeline (no camera required).

Includes an animation layer (Sequencer, easings, arc-length stroke reveal,
flicker) so hand-laid HUDs can assemble/boot like Arwes.
"""

from . import anim
from .anim import Sequencer, flicker
from .batch import TextBatch, VectorBatch
from .renderer import Overlay

__all__ = ["Overlay", "VectorBatch", "TextBatch", "Sequencer", "flicker", "anim"]
