"""EdgeTrace — render the OpenCV Canny edge mask as glowing cyan contours."""

from __future__ import annotations

from ..base import Component
from ...hud_context import HudContext


class EdgeTrace(Component):
    FRAG = "edgetrace.frag"

    def __init__(self, ctx, vbo, theme, intensity: float = 0.45) -> None:
        super().__init__(ctx, vbo, theme)
        self.intensity = intensity

    def render(self, hud: HudContext) -> None:
        if hud.edge_tex is None or hud.edge_progress <= 0.001:
            return
        hud.edge_tex.use(0)
        self._set("u_edge", 0)
        self._set("u_color", self.theme.stroke[:3])
        self._set("u_intensity", float(self.intensity))
        self._set("u_progress", float(hud.edge_progress))
        self.vao.render()
