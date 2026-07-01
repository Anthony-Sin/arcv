"""TrackerDots — small markers at ORB keypoints (Phase 2)."""

from __future__ import annotations

import numpy as np

from ..base import Component
from ...hud_context import HudContext


class TrackerDots(Component):
    FRAG = "points.frag"

    def render(self, hud: HudContext) -> None:
        if hud.keypoint_count <= 0 or hud.bg_progress <= 0.001:
            return
        self._set("u_resolution", (float(hud.resolution[0]), float(hud.resolution[1])))
        self._set("u_color", self.theme.glow[:3])
        self._set("u_pcount", int(hud.keypoint_count))
        self._set("u_progress", float(hud.bg_progress))
        self.prog["u_points"].write(np.ascontiguousarray(hud.keypoints, dtype="f4").tobytes())
        self.vao.render()
