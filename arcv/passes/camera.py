"""Pass 1 — camera base + color grade into the scene FBO."""

from __future__ import annotations

import moderngl

from .. import geometry, shaders


class CameraPass:
    def __init__(self, ctx, vbo, theme) -> None:
        self.ctx = ctx
        self.theme = theme
        self.prog = ctx.program(
            vertex_shader=shaders.load("fullscreen.vert"),
            fragment_shader=shaders.load("camera.frag"),
        )
        self.vao = geometry.fullscreen_vao(ctx, self.prog, vbo)

    def render(self, scene_fbo, cam_tex, grade: float = 1.0) -> None:
        scene_fbo.use()
        scene_fbo.clear(0.0, 0.0, 0.0, 1.0)
        self.ctx.disable(moderngl.BLEND)
        cam_tex.use(0)
        self.prog["u_cam"].value = 0
        self.prog["u_base"].value = self.theme.base[:3]
        self.prog["u_grade"].value = float(grade)
        self.vao.render()
