"""Background base — sets the uniforms common to every procedural background."""

from __future__ import annotations

from ..base import Component
from ...hud_context import HudContext


class Background(Component):
    def _common(self, hud: HudContext) -> None:
        self._set("u_resolution", (float(hud.resolution[0]), float(hud.resolution[1])))
        self._set("u_progress", float(hud.bg_progress))
        self._set("u_time", float(hud.time))
        self._set("u_color", self.theme.stroke[:3])

    def render(self, hud: HudContext) -> None:
        if hud.bg_progress <= 0.001:
            return
        self._common(hud)
        self.vao.render()
