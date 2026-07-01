"""Procedural background components (Phase 2)."""

from .base import Background
from .dots import DotsBackground
from .gridlines import GridLinesBackground
from .movinglines import MovingLinesBackground
from .puffs import PuffsBackground

#: name -> class, used by Scene(backgrounds=[...])
BACKGROUND_STYLES = {
    "dots": DotsBackground,
    "gridlines": GridLinesBackground,
    "movinglines": MovingLinesBackground,
    "puffs": PuffsBackground,
}

__all__ = [
    "Background",
    "DotsBackground",
    "GridLinesBackground",
    "MovingLinesBackground",
    "PuffsBackground",
    "BACKGROUND_STYLES",
]
