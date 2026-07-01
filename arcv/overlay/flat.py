"""FlatOverlay — an *opaque* immediate-mode HUD renderer.

The glowing :class:`~arcv.overlay.renderer.Overlay` composites its geometry
**additively** (so bright strokes bloom on a dark scene). Additive light can only
ever *add* — it can't paint dark content on a bright fill, so it cannot draw the
black-on-yellow "WARNING panel" look at all.

``FlatOverlay`` draws the same :class:`VectorBatch` / :class:`TextBatch` with
**premultiplied *over*** blending onto an opaque base instead: a solid color, or
— crucially for ARCV — a **live camera frame**. That makes it the natural surface
for hard-edged, high-contrast HUDs laid *over the OpenCV feed* (opaque panels,
black text on yellow, bright reticles on the darkened camera).

    ov = FlatOverlay(ctx, (1280, 720))
    ov.begin()
    ov.vector.rounded_rect(40, 40, 300, 200, 12, (0.94, 0.90, 0.02, 1.0))  # opaque
    ov.text.text("WARNING", 56, 56, 24, (0.06, 0.06, 0.05, 1.0))           # black-on-yellow
    ov.render(cam_frame=frame_bgr, target=fbo)   # panels sit over the live feed
    img = ov.read_pixels(fbo)

``cam_frame`` is a ``uint8`` ``(H, W, 3)`` **BGR** array (an OpenCV frame). Pass
``None`` to fall back to ``base_color``. Pre-grade the frame yourself (darken /
desaturate) before handing it in if you want the HUD to pop — ``FlatOverlay``
blits it as-is.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Optional, Tuple

import moderngl
import numpy as np

from .. import geometry
from ..passes import Target
from ..passes.camera import CameraPass
from .batch import TextBatch, VectorBatch

Color = Tuple[float, float, float, float]


class FlatOverlay:
    def __init__(
        self,
        ctx,
        size: Tuple[int, int],
        base_color: Color = (0.05, 0.05, 0.05, 1.0),
    ) -> None:
        self.ctx = ctx
        self.size = (int(size[0]), int(size[1]))
        self.base_color = base_color

        self.vector = VectorBatch(ctx)
        self.text = TextBatch(ctx)
        self.out = Target(ctx, self.size, components=4, dtype="f1")

        # camera base (lazy — only built when a frame is first supplied)
        self._fsvbo = geometry.fullscreen_buffer(ctx)
        self._cam_pass: Optional[CameraPass] = None
        self._cam_tex = None
        self._cam_size: Tuple[int, int] = (0, 0)

    # ------------------------------------------------------------------ api
    def resize(self, width: int, height: int) -> None:
        self.size = (max(1, int(width)), max(1, int(height)))
        self.out.resize(self.size)

    def begin(self) -> None:
        self.vector.clear()
        self.text.clear()

    def render(
        self,
        time: float = 0.0,
        target=None,
        *,
        cam_frame: Optional[np.ndarray] = None,
        base_color: Optional[Color] = None,
        cam_grade: float = 0.0,
    ) -> None:
        """Composite the accumulated vector + text over the base into ``target``
        (or this overlay's own FBO). ``time`` is accepted for signature parity
        with :class:`Overlay` and is otherwise unused."""
        fbo = target if target is not None else self.out.fbo

        if cam_frame is not None:
            self._draw_camera(fbo, cam_frame, cam_grade)
        else:
            base = base_color if base_color is not None else self.base_color
            fbo.use()
            fbo.clear(*base[:3], 1.0)

        # opaque vector + text, premultiplied *over* the base (dark-on-light OK)
        fbo.use()
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA)
        self.vector.draw(self.size)
        self.text.draw(self.size)
        self.ctx.disable(moderngl.BLEND)

    def read_pixels(self, target=None) -> np.ndarray:
        fbo = target if target is not None else self.out.fbo
        w, h = fbo.size
        data = fbo.read(components=3, dtype="f1")
        return np.flipud(np.frombuffer(data, dtype=np.uint8).reshape(h, w, 3))

    # -------------------------------------------------------------- internal
    def _draw_camera(self, fbo, frame: np.ndarray, grade: float) -> None:
        h, w = frame.shape[:2]
        if self._cam_pass is None:
            self._cam_pass = CameraPass(self.ctx, self._fsvbo, SimpleNamespace(base=(0.0, 0.0, 0.0)))
        if self._cam_tex is None or self._cam_size != (w, h):
            if self._cam_tex is not None:
                self._cam_tex.release()
            self._cam_tex = self.ctx.texture((w, h), 3, dtype="f1")
            self._cam_tex.swizzle = "BGR"  # OpenCV BGR -> sampled as RGB
            self._cam_tex.filter = (9729, 9729)  # GL_LINEAR
            self._cam_size = (w, h)
        self._cam_tex.write(np.ascontiguousarray(frame, dtype="u1").tobytes())
        self._cam_pass.render(fbo, self._cam_tex, grade)
