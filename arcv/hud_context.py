"""Per-frame data handed to every HUD component during the HUD pass."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np


@dataclass
class Label:
    text: str
    x: float          # start x in screen UV (y-up)
    y: float          # baseline y in screen UV (y-up)
    progress: float   # 0..1 reveal


@dataclass
class HudContext:
    resolution: Tuple[int, int]
    time: float
    boxes: np.ndarray                 # (16, 4)  (cx, cy, hw, hh)
    meta: np.ndarray                  # (16, 4)  (progress, score, kind, primary)
    count: int
    mouse: Tuple[float, float]        # UV, y-up
    edge_tex: Optional[object] = None # moderngl.Texture or None
    primary_center: Tuple[float, float] = (0.5, 0.5)
    primary_half: Tuple[float, float] = (0.1, 0.1)
    primary_progress: float = 0.0
    edge_progress: float = 1.0
    labels: List[Label] = field(default_factory=list)
    # background / global chrome
    bg_progress: float = 0.0
    flow_mag: float = 0.0             # optical-flow magnitude 0..1
    # ORB keypoints
    keypoints: Optional[np.ndarray] = None  # (64, 2) UV, y-up
    keypoint_count: int = 0
