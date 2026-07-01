"""HUD components — one per Arwes visual element."""

from .base import Component
from .frames import (
    BoxFrame,
    FrameNefrex,
    FrameCorners,
    FrameLines,
    FrameOctagon,
    FrameUnderline,
    FrameKranox,
    FRAME_STYLES,
)
from .backgrounds import (
    Background,
    DotsBackground,
    GridLinesBackground,
    MovingLinesBackground,
    PuffsBackground,
    BACKGROUND_STYLES,
)
from .text import TextComponent, DecipherText, TypeOnText, TEXT_STYLES
from .effects import Reticle, EdgeTrace, Illuminator, TrackerDots

__all__ = [
    "Component",
    # frames
    "BoxFrame",
    "FrameNefrex",
    "FrameCorners",
    "FrameLines",
    "FrameOctagon",
    "FrameUnderline",
    "FrameKranox",
    "FRAME_STYLES",
    # backgrounds
    "Background",
    "DotsBackground",
    "GridLinesBackground",
    "MovingLinesBackground",
    "PuffsBackground",
    "BACKGROUND_STYLES",
    # text
    "TextComponent",
    "DecipherText",
    "TypeOnText",
    "TEXT_STYLES",
    # effects
    "Reticle",
    "EdgeTrace",
    "Illuminator",
    "TrackerDots",
]
