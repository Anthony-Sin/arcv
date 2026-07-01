from .base import BoxFrame
from .nefrex import FrameNefrex
from .presets import (
    FrameCorners,
    FrameLines,
    FrameOctagon,
    FrameUnderline,
    FrameKranox,
)

#: name -> class, used by Scene(frame_style=...)
FRAME_STYLES = {
    "nefrex": FrameNefrex,
    "corners": FrameCorners,
    "lines": FrameLines,
    "octagon": FrameOctagon,
    "underline": FrameUnderline,
    "kranox": FrameKranox,
}

__all__ = [
    "BoxFrame",
    "FrameNefrex",
    "FrameCorners",
    "FrameLines",
    "FrameOctagon",
    "FrameUnderline",
    "FrameKranox",
    "FRAME_STYLES",
]
