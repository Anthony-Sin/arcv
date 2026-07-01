"""Component base class.

A component is one Arwes visual element: it owns its GLSL program and a
fullscreen VAO, and draws itself into the HUD framebuffer given a HudContext.
"""

from __future__ import annotations

from .. import geometry, shaders
from ..hud_context import HudContext


class Component:
    #: vertex/fragment shader file names (under arcv/shaders/)
    VERT = "fullscreen.vert"
    FRAG = ""

    def __init__(self, ctx, vbo, theme) -> None:
        self.ctx = ctx
        self.theme = theme
        self.prog = ctx.program(
            vertex_shader=shaders.load(self.VERT),
            fragment_shader=shaders.load(self.FRAG),
        )
        self.vao = geometry.fullscreen_vao(ctx, self.prog, vbo)

    def _set(self, name, value) -> None:
        """Set a uniform if it exists (programs drop unused uniforms)."""
        u = self.prog.get(name, None)
        if u is not None:
            u.value = value

    def render(self, hud: HudContext) -> None:  # pragma: no cover - abstract
        raise NotImplementedError
