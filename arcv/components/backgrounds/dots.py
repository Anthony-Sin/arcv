from __future__ import annotations

from .base import Background
from ...hud_context import HudContext


class DotsBackground(Background):
    FRAG = "bg_dots.frag"

    def __init__(self, ctx, vbo, theme, distance: float = 34.0, size: float = 2.0) -> None:
        super().__init__(ctx, vbo, theme)
        self.distance = distance
        self.size = size

    def render(self, hud: HudContext) -> None:
        if hud.bg_progress <= 0.001:
            return
        self._common(hud)
        self._set("u_distance", float(self.distance))
        self._set("u_size", float(self.size))
        self.vao.render()
