"""Pass 3 — bloom: bright-pass extract + separable Gaussian ping-pong blur.

Runs at half resolution for a wide, cheap glow. Returns the blurred texture to
be composited additively.
"""

from __future__ import annotations

from typing import Tuple

import moderngl

from .. import geometry, shaders
from .base import Target


class BloomPass:
    def __init__(self, ctx, vbo, theme) -> None:
        self.ctx = ctx
        self.theme = theme
        self.bright_prog = ctx.program(
            vertex_shader=shaders.load("fullscreen.vert"),
            fragment_shader=shaders.load("bloom_bright.frag"),
        )
        self.blur_prog = ctx.program(
            vertex_shader=shaders.load("fullscreen.vert"),
            fragment_shader=shaders.load("bloom_blur.frag"),
        )
        self.bright_vao = geometry.fullscreen_vao(ctx, self.bright_prog, vbo)
        self.blur_vao = geometry.fullscreen_vao(ctx, self.blur_prog, vbo)
        self.bright = None
        self.ping_a = None
        self.ping_b = None

    def resize(self, size: Tuple[int, int]) -> None:
        half = (max(1, size[0] // 2), max(1, size[1] // 2))
        if self.bright is None:
            self.bright = Target(self.ctx, half, components=4, dtype="f2")
            self.ping_a = Target(self.ctx, half, components=4, dtype="f2")
            self.ping_b = Target(self.ctx, half, components=4, dtype="f2")
        else:
            self.bright.resize(half)
            self.ping_a.resize(half)
            self.ping_b.resize(half)
        self._half = half

    def process(self, src_tex, iterations: int):
        self.ctx.disable(moderngl.BLEND)
        hw, hh = self._half

        # bright-pass extract
        self.bright.fbo.use()
        self.bright.fbo.clear(0.0, 0.0, 0.0, 1.0)
        src_tex.use(0)
        self.bright_prog["u_src"].value = 0
        self.bright_prog["u_threshold"].value = float(self.theme.bloom_threshold)
        self.bright_vao.render()

        # ping-pong separable blur
        read = self.bright
        targets = (self.ping_a, self.ping_b)
        for i in range(iterations * 2):
            horizontal = (i % 2 == 0)
            dst = targets[i % 2]
            dst.fbo.use()
            dst.fbo.clear(0.0, 0.0, 0.0, 1.0)
            read.tex.use(0)
            self.blur_prog["u_src"].value = 0
            self.blur_prog["u_dir"].value = (
                (1.0 / hw, 0.0) if horizontal else (0.0, 1.0 / hh)
            )
            self.blur_vao.render()
            read = dst

        return read.tex
