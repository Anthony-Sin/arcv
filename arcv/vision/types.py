"""Detection data types.

All coordinates are normalized to UV space in ``[0, 1]`` with the origin at the
**bottom-left** (OpenGL convention) and the vertical axis already flipped from
OpenCV's top-left image space. That way every HUD component consumes detections
identically and they line up with the (v-flipped) camera texture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np


@dataclass
class Detection:
    cx: float  # center x in UV [0, 1]
    cy: float  # center y in UV [0, 1] (y-up)
    hw: float  # half width in UV
    hh: float  # half height in UV
    score: float = 1.0
    label: str = ""
    kind: str = "face"  # "face" | "object"
    id: int = -1

    @classmethod
    def from_pixel_rect(
        cls,
        x: int,
        y: int,
        w: int,
        h: int,
        frame_w: int,
        frame_h: int,
        **kwargs,
    ) -> "Detection":
        """Build from an OpenCV pixel rect ``(x, y, w, h)`` (top-left origin)."""
        cx = (x + w * 0.5) / frame_w
        cy = 1.0 - (y + h * 0.5) / frame_h  # flip to y-up
        hw = (w * 0.5) / frame_w
        hh = (h * 0.5) / frame_h
        return cls(cx=cx, cy=cy, hw=hw, hh=hh, **kwargs)

    @property
    def area(self) -> float:
        return self.hw * self.hh


@dataclass
class DetectionFrame:
    boxes: List[Detection] = field(default_factory=list)
    edges: Optional[np.ndarray] = None  # uint8 (H, W) Canny mask, top-left origin
    frame_size: Tuple[int, int] = (0, 0)  # (W, H)
    primary: int = -1  # index into ``boxes`` of the main target, or -1
    flow_mag: float = 0.0  # mean optical-flow magnitude, normalized 0..1
    keypoints: List[Tuple[float, float]] = field(default_factory=list)  # UV, y-up

    def packed_points(self, max_points: int) -> Tuple[np.ndarray, int]:
        pts = np.zeros((max_points, 2), dtype="f4")
        count = min(len(self.keypoints), max_points)
        for i in range(count):
            pts[i] = self.keypoints[i]
        return pts, count

    def packed(self, max_boxes: int) -> Tuple[np.ndarray, np.ndarray, int]:
        """Pack boxes for shader uniform arrays.

        Returns ``(boxes, meta, count)`` where ``boxes`` is ``(max_boxes, 4)``
        ``(cx, cy, hw, hh)`` and ``meta`` is ``(max_boxes, 4)``
        ``(progress, score, kind_flag, primary_flag)``. ``progress`` defaults
        to 1.0 here; the Scene overwrites it from per-box animators.
        """
        boxes = np.zeros((max_boxes, 4), dtype="f4")
        meta = np.zeros((max_boxes, 4), dtype="f4")
        count = min(len(self.boxes), max_boxes)
        for i in range(count):
            d = self.boxes[i]
            boxes[i] = (d.cx, d.cy, d.hw, d.hh)
            meta[i] = (
                1.0,
                d.score,
                0.0 if d.kind == "face" else 1.0,
                1.0 if i == self.primary else 0.0,
            )
        return boxes, meta, count
