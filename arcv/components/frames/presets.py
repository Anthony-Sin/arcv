"""The remaining Arwes frame presets (Phase 2). Each is a thin BoxFrame that
points at its own fragment shader."""

from __future__ import annotations

from .base import BoxFrame


class FrameCorners(BoxFrame):
    FRAG = "frame_corners.frag"


class FrameLines(BoxFrame):
    FRAG = "frame_lines.frag"


class FrameOctagon(BoxFrame):
    FRAG = "frame_octagon.frag"


class FrameUnderline(BoxFrame):
    FRAG = "frame_underline.frag"


class FrameKranox(BoxFrame):
    FRAG = "frame_kranox.frag"
