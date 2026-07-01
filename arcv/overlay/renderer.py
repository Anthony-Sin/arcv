"""Overlay — an immediate-mode HUD renderer that draws hand-laid-out vector and
text geometry through ARCV's HDR bloom composite.

Graphics (`ov.vector`) glow via HDR bloom; text (`ov.text`) is drawn crisp on top
*after* the bloom so labels stay readable (they change a lot). An optional faint
background grid is drawn behind the HUD.

    ov = Overlay(ctx, (1280, 720), theme=make_theme("green"))
    ov.begin()
    ov.vector.rounded_rect(40, 40, 300, 200, 12, ov.theme.stroke)  # glows
    ov.text.text("SYSTEM ONLINE", 56, 56, 18, ov.theme.stroke)     # crisp
    ov.render(time, target=fbo)
    img = ov.read_pixels(fbo)
"""

from __future__ import annotations

from typing import Optional, Tuple

import moderngl
import numpy as np

from .. import geometry, shaders
from ..passes import BloomPass, CompositePass, Target
from ..theme import Theme
from .batch import TextBatch, VectorBatch


class Overlay:
    def __init__(
        self,
        ctx,
        size: Tuple[int, int],
        theme: Optional[Theme] = None,
        base_color: Optional[Tuple[float, float, float, float]] = None,
        grid: bool = False,
        grid_cell: float = 42.0,
        grid_alpha: float = 0.10,
        bloom_text: bool = False,
    ) -> None:
        self.ctx = ctx
        self.size = (int(size[0]), int(size[1]))
        self.theme = theme or Theme()
        self.base_color = base_color if base_color is not None else self.theme.base
        self.grid = grid
        self.grid_cell = grid_cell
        self.grid_alpha = grid_alpha
        self.bloom_text = bloom_text  # if True, text glows (old behavior)

        self._fsvbo = geometry.fullscreen_buffer(ctx)
        self.scene = Target(ctx, self.size, components=4, dtype="f2")
        self.hud = Target(ctx, self.size, components=4, dtype="f2")
        self.bloom = BloomPass(ctx, self._fsvbo, self.theme)
        self.bloom.resize(self.size)
        self.composite = CompositePass(ctx, self._fsvbo, self.theme)

        self._grid_prog = ctx.program(
            vertex_shader=shaders.load("fullscreen.vert"),
            fragment_shader=shaders.load("overlay_grid.frag"),
        )
        self._grid_vao = geometry.fullscreen_vao(ctx, self._grid_prog, self._fsvbo)

        self.vector = VectorBatch(ctx)
        self.text = TextBatch(ctx)

    def resize(self, width: int, height: int) -> None:
        self.size = (max(1, int(width)), max(1, int(height)))
        self.scene.resize(self.size)
        self.hud.resize(self.size)
        self.bloom.resize(self.size)

    def begin(self) -> None:
        self.vector.clear()
        self.text.clear()

    def _draw_grid(self) -> None:
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.ADDITIVE_BLENDING
        p = self._grid_prog
        p["u_resolution"].value = (float(self.size[0]), float(self.size[1]))
        p["u_color"].value = self.theme.stroke[:3]
        p["u_cell"].value = float(self.grid_cell)
        p["u_alpha"].value = float(self.grid_alpha)
        self._grid_vao.render()
        self.ctx.disable(moderngl.BLEND)

    def render(self, time: float = 0.0, target=None) -> None:
        # base scene (+ faint grid behind the HUD, not bloomed)
        self.scene.fbo.use()
        self.scene.fbo.clear(*self.base_color[:3], 1.0)
        if self.grid:
            self._draw_grid()

        # glowing HUD geometry (additive) -> bloom source
        self.hud.fbo.use()
        self.hud.fbo.clear(0.0, 0.0, 0.0, 0.0)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.ADDITIVE_BLENDING
        self.vector.draw(self.size)
        if self.bloom_text:
            self.text.draw(self.size)
        self.ctx.disable(moderngl.BLEND)

        bloom_tex = self.bloom.process(self.hud.tex, self.theme.bloom_iterations)

        out = target if target is not None else self.ctx.screen
        self.composite.render(out, self.scene.tex, self.hud.tex, bloom_tex, time)

        # crisp text on top (no bloom) so changing labels stay readable
        if not self.bloom_text:
            out.use()
            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = moderngl.ADDITIVE_BLENDING
            self.text.draw(self.size)
            self.ctx.disable(moderngl.BLEND)

    def read_pixels(self, target=None) -> np.ndarray:
        fbo = target if target is not None else self.ctx.screen
        w, h = fbo.size
        data = fbo.read(components=3, dtype="f1")
        return np.flipud(np.frombuffer(data, dtype=np.uint8).reshape(h, w, 3))
