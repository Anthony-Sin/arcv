"""Illuminator — soft radial glow following the cursor."""

from __future__ import annotations

from ..base import Component
from ...hud_context import HudContext


class Illuminator(Component):
    FRAG = "illuminator.frag"

    def __init__(self, ctx, vbo, theme, radius: float = 0.28, strength: float = 0.35) -> None:
        super().__init__(ctx, vbo, theme)
        self.radius = radius
        self.strength = strength

    def render(self, hud: HudContext) -> None:
        self._set("u_mouse", hud.mouse)
        self._set("u_color", self.theme.glow[:3])
        self._set("u_radius", float(self.radius))
        self._set("u_strength", float(self.strength))
        self.vao.render()
