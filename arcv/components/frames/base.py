"""Box-frame base: uploads the per-box uniform arrays and draws the fullscreen
pass. Each concrete frame just points at its own fragment shader."""

from __future__ import annotations

import numpy as np

from ..base import Component
from ...hud_context import HudContext


class BoxFrame(Component):
    FRAG = "frame_nefrex.frag"

    def render(self, hud: HudContext) -> None:
        if hud.count <= 0:
            return
        self._set("u_resolution", (float(hud.resolution[0]), float(hud.resolution[1])))
        self._set("u_color", self.theme.stroke[:3])
        self._set("u_count", int(hud.count))
        self.prog["u_boxes"].write(np.ascontiguousarray(hud.boxes, dtype="f4").tobytes())
        self.prog["u_meta"].write(np.ascontiguousarray(hud.meta, dtype="f4").tobytes())
        self.vao.render()
