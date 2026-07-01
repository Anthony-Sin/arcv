"""Render-target helper: a color texture + framebuffer that can be reallocated
on resize. Used for every offscreen pass."""

from __future__ import annotations

from typing import Tuple

_GL_LINEAR = 9729


class Target:
    def __init__(self, ctx, size: Tuple[int, int], components: int = 4, dtype: str = "f2") -> None:
        self.ctx = ctx
        self.components = components
        self.dtype = dtype
        self.tex = None
        self.fbo = None
        self.alloc(size)

    def alloc(self, size: Tuple[int, int]) -> None:
        w = max(1, int(size[0]))
        h = max(1, int(size[1]))
        self.tex = self.ctx.texture((w, h), self.components, dtype=self.dtype)
        self.tex.filter = (_GL_LINEAR, _GL_LINEAR)
        self.tex.repeat_x = False
        self.tex.repeat_y = False
        self.fbo = self.ctx.framebuffer(color_attachments=[self.tex])
        self.size = (w, h)

    def resize(self, size: Tuple[int, int]) -> None:
        self.release()
        self.alloc(size)

    def release(self) -> None:
        if self.tex is not None:
            self.tex.release()
            self.tex = None
        if self.fbo is not None:
            self.fbo.release()
            self.fbo = None
