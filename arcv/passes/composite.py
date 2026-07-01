"""Pass 4 — composite graded camera + HUD + bloom, add scanlines/vignette, and
tone-map to the caller's target framebuffer."""

from __future__ import annotations

import moderngl

from .. import geometry, shaders


class CompositePass:
    def __init__(self, ctx, vbo, theme) -> None:
        self.ctx = ctx
        self.theme = theme
        self.prog = ctx.program(
            vertex_shader=shaders.load("fullscreen.vert"),
            fragment_shader=shaders.load("composite.frag"),
        )
        self.vao = geometry.fullscreen_vao(ctx, self.prog, vbo)

    def render(self, target_fbo, scene_tex, hud_tex, bloom_tex, time: float) -> None:
        target_fbo.use()
        self.ctx.disable(moderngl.BLEND)
        scene_tex.use(0)
        hud_tex.use(1)
        bloom_tex.use(2)
        p = self.prog
        p["u_scene"].value = 0
        p["u_hud"].value = 1
        p["u_bloom"].value = 2
        p["u_time"].value = float(time)
        p["u_bloom_intensity"].value = float(self.theme.bloom_intensity)
        p["u_glow"].value = self.theme.glow[:3]
        p["u_scan_count"].value = float(self.theme.scanline_count)
        p["u_scan_strength"].value = float(self.theme.scanline_strength)
        p["u_sweep_speed"].value = float(self.theme.scanline_sweep_speed)
        p["u_sweep_strength"].value = float(getattr(self.theme, "sweep_strength", 0.12))
        p["u_exposure"].value = float(getattr(self.theme, "exposure", 1.25))
        self.vao.render()
