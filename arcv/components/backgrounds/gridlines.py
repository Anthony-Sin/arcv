from __future__ import annotations

from .base import Background
from ...hud_context import HudContext


class GridLinesBackground(Background):
    FRAG = "bg_gridlines.frag"

    def __init__(self, ctx, vbo, theme, distance: float = 40.0, line_width: float = 1.0) -> None:
        super().__init__(ctx, vbo, theme)
        self.distance = distance
        self.line_width = line_width

    def render(self, hud: HudContext) -> None:
        if hud.bg_progress <= 0.001:
            return
        self._common(hud)
        self._set("u_distance", float(self.distance))
        self._set("u_lineWidth", float(self.line_width))
        self.vao.render()
