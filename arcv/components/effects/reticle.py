"""Reticle — targeting crosshair locked to the primary detection."""

from __future__ import annotations

from ..base import Component
from ...hud_context import HudContext


class Reticle(Component):
    FRAG = "reticle.frag"

    def render(self, hud: HudContext) -> None:
        if hud.primary_progress <= 0.001:
            return
        self._set("u_resolution", (float(hud.resolution[0]), float(hud.resolution[1])))
        self._set("u_center", hud.primary_center)
        self._set("u_half", hud.primary_half)
        self._set("u_progress", float(hud.primary_progress))
        self._set("u_time", float(hud.time))
        self._set("u_color", self.theme.stroke[:3])
        self.vao.render()
