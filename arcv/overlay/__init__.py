"""Overlay UI kit — lay out Arwes-style HUD elements at fixed positions and
render them through ARCV's bloom/composite pipeline (no camera required).

Includes an animation layer (Sequencer, easings, arc-length stroke reveal,
flicker) so hand-laid HUDs can assemble/boot like Arwes.
"""

from . import anim
from . import hud_kit
from .anim import Sequencer, flicker, Timer, Animation, Timeline
from .batch import TextBatch, VectorBatch
from .draw import Draw
from .renderer import Overlay
from .flat import FlatOverlay

__all__ = ["Overlay", "FlatOverlay", "VectorBatch", "TextBatch", "Sequencer",
           "flicker", "anim", "Draw", "hud_kit", "Timer", "Animation", "Timeline"]
