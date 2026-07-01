"""TextComponent base — owns the glyph atlas/texture/program and lays glyph
quads out from screen-space labels. Subclasses decide which glyph each character
shows (decipher scramble vs type-on) and where the cursor goes.
"""

from __future__ import annotations

import math
from typing import List, Tuple

import numpy as np

from ... import shaders
from ...hud_context import HudContext
from .atlas import FontAtlas

_MAX_CHARS = 1024


class TextComponent:
    def __init__(self, ctx, vbo, theme, glyph_px: float = 20.0) -> None:
        self.ctx = ctx
        self.theme = theme
        self.glyph_px = glyph_px
        self.atlas = FontAtlas()

        self.prog = ctx.program(
            vertex_shader=shaders.load("text.vert"),
            fragment_shader=shaders.load("text.frag"),
        )
        img = np.ascontiguousarray(self.atlas.image)
        self.tex = ctx.texture(
            (self.atlas.atlas_w, self.atlas.atlas_h), 1, img.tobytes(), dtype="f1", alignment=1
        )
        self.tex.filter = (9729, 9729)  # GL_LINEAR
        self.tex.repeat_x = False
        self.tex.repeat_y = False

        self._vbo = ctx.buffer(reserve=_MAX_CHARS * 6 * 4 * 4, dynamic=True)
        self.vao = ctx.vertex_array(self.prog, [(self._vbo, "2f 2f", "in_pos", "in_auv")])

    # subclasses override -------------------------------------------------
    def _resolve(self, text: str, progress: float, time: float, li: int) -> Tuple[List[Tuple[int, str]], int]:
        """Return (list of (index, char_to_draw), cursor_index_or_-1)."""
        raise NotImplementedError

    # layout --------------------------------------------------------------
    def _quad(self, verts: List[float], x0, y0, gw, gh, ch) -> None:
        u0, u1 = self.atlas.u_range(ch)
        x1, y1 = x0 + gw, y0 + gh
        # atlas v: glyph top (y1) -> v=0, bottom (y0) -> v=1
        verts.extend((x0, y0, u0, 1.0, x1, y0, u1, 1.0, x1, y1, u1, 0.0))
        verts.extend((x0, y0, u0, 1.0, x1, y1, u1, 0.0, x0, y1, u0, 0.0))

    def render(self, hud: HudContext) -> None:
        if not hud.labels:
            return
        res_x, res_y = hud.resolution
        gh = self.glyph_px / res_y
        gw = (self.glyph_px * self.atlas.aspect) / res_x
        adv = gw

        verts: List[float] = []
        blink_on = (hud.time / 0.53) % 1.0 < 0.5
        for li, label in enumerate(hud.labels):
            if label.progress <= 0.001:
                continue
            chars, cursor_k = self._resolve(label.text, label.progress, hud.time, li)
            for k, ch in chars:
                if ch == " ":
                    continue
                self._quad(verts, label.x + k * adv, label.y, gw, gh, ch)
            if cursor_k >= 0 and blink_on:
                self._quad(verts, label.x + cursor_k * adv, label.y, gw, gh, "|")
            if len(verts) >= _MAX_CHARS * 6 * 4:
                break

        if not verts:
            return
        data = np.asarray(verts, dtype="f4")
        self._vbo.write(data.tobytes())
        self.tex.use(0)
        self.prog["u_atlas"].value = 0
        self.prog["u_color"].value = self.theme.stroke[:3]
        self.prog["u_alpha"].value = 1.0
        self.vao.render(vertices=len(data) // 4)

    def _scramble(self, seed: int) -> str:
        pool = self.atlas.scramble_pool
        return pool[seed % len(pool)]
