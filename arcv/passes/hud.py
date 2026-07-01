"""Pass 2 — draw an ordered list of HUD components additively into the HUD FBO.

A separate FBO (not the camera) so the bloom pass can threshold only the HUD,
which is the glow source. The Scene owns the components and their order; this
pass just renders them.
"""

from __future__ import annotations

from typing import List

import moderngl

from ..hud_context import HudContext


class HudPass:
    def __init__(self, ctx) -> None:
        self.ctx = ctx

    def render(self, hud_fbo, layers: List, hud: HudContext) -> None:
        hud_fbo.use()
        hud_fbo.clear(0.0, 0.0, 0.0, 0.0)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.ADDITIVE_BLENDING
        for component in layers:
            component.render(hud)
        self.ctx.disable(moderngl.BLEND)
