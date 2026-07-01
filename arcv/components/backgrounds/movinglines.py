from __future__ import annotations

from .base import Background
from ...hud_context import HudContext


class MovingLinesBackground(Background):
    FRAG = "bg_movinglines.frag"

    def __init__(self, ctx, vbo, theme, distance: float = 28.0, speed: float = 0.25) -> None:
        super().__init__(ctx, vbo, theme)
        self.distance = distance
        self.speed = speed

    def render(self, hud: HudContext) -> None:
        if hud.bg_progress <= 0.001:
            return
        self._common(hud)
        self._set("u_distance", float(self.distance))
        self._set("u_speed", float(self.speed))
        self._set("u_flow", float(hud.flow_mag))
        self.vao.render()
