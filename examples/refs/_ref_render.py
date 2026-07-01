"""Shared render harness for the reference-recreation HUDs.

Each `refN_layout.py` exposes `build(d, W, H, t)` (same adapter interface as the
robot / cyberpunk demos: d.line/poly/rect/rrect/rrect_fill/ring/disc/tri/
tri_fill/text) and calls one of the render helpers here to write a PNG.

Two render modes:

* ``mode="glow"`` (default) — draws through the full ARCV Overlay: additive HUD
  geometry + HDR bloom + composite (scanlines/sweep/vignette/tone-map). This is
  the glowing on-screen look (refs 2/3/4/5). Tune via the ``theme`` kwargs.

* ``mode="flat"`` — draws the SAME VectorBatch/TextBatch with premultiplied
  *over* blending onto a solid base, no bloom, no scanlines. This yields crisp
  opaque flat vector art and — crucially — lets you paint dark content on a
  bright fill (e.g. black text on a yellow warning panel), which the additive
  glow pipeline cannot do.

Optional photographic background compositing (refs 4/5) via ``bg_image``.

    from _ref_render import render_png
    render_png(build, "gallery/ref1.png", size=(1277, 605), mode="flat",
               base_color=(0.82, 0.82, 0.82, 1.0))
"""

from __future__ import annotations

import os
import sys
from typing import Callable, Optional, Tuple

import numpy as np
import cv2
import moderngl

_HERE = os.path.dirname(os.path.abspath(__file__))
_EXAMPLES = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_EXAMPLES)
for _p in (_ROOT, _EXAMPLES, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from arcv.overlay import Overlay  # noqa: E402
from arcv.overlay.batch import VectorBatch, TextBatch  # noqa: E402
from arcv.theme import Theme, make_theme  # noqa: E402
from arcv.passes.base import Target  # noqa: E402
from _hud_adapters import ArcvAdapter  # noqa: E402

Color = Tuple[float, float, float, float]

_CTX = None


def get_ctx():
    """One shared standalone GL context per process (Intel-safe GLSL 330)."""
    global _CTX
    if _CTX is None:
        _CTX = moderngl.create_standalone_context(require=330)
    return _CTX


class _Shim:
    """Minimal stand-in exposing .vector/.text so ArcvAdapter works without a
    full Overlay (used by flat mode)."""

    def __init__(self, vector, text):
        self.vector = vector
        self.text = text


def _read_rgb(fbo) -> np.ndarray:
    w, h = fbo.size
    data = fbo.read(components=3, dtype="f1")
    return np.flipud(np.frombuffer(data, dtype=np.uint8).reshape(h, w, 3))


def _composite_bg(img: np.ndarray, bg_image: str, size, mode: str) -> np.ndarray:
    bg = cv2.imread(bg_image, cv2.IMREAD_COLOR)
    if bg is None:
        return img
    bg = cv2.cvtColor(cv2.resize(bg, size), cv2.COLOR_BGR2RGB)
    if mode == "screen":
        a = bg.astype(np.float32) / 255.0
        b = img.astype(np.float32) / 255.0
        return ((1.0 - (1.0 - a) * (1.0 - b)) * 255.0).astype(np.uint8)
    # default: additive (HUD glow adds onto the scene)
    return np.clip(bg.astype(np.int32) + img.astype(np.int32), 0, 255).astype(np.uint8)


def render_png(
    build: Callable,
    out_path: str,
    size: Tuple[int, int] = (1280, 640),
    *,
    mode: str = "glow",
    theme: Optional[Theme] = None,
    base_color: Color = (0.02, 0.03, 0.05, 1.0),
    grid: bool = False,
    grid_cell: float = 46.0,
    grid_alpha: float = 0.09,
    bloom_text: bool = False,
    glow: Optional[Tuple[float, float, float]] = None,
    t: float = 8.0,
    bg_image: Optional[str] = None,
    bg_mode: str = "add",
    ctx=None,
) -> str:
    """Render `build` to `out_path` (PNG). Returns the absolute path written."""
    size = (int(size[0]), int(size[1]))
    ctx = ctx or get_ctx()
    if not os.path.isabs(out_path):
        out_path = os.path.join(_HERE, out_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    if mode == "flat":
        theme = theme or make_theme("cyan")
        tgt = Target(ctx, size, 4, "f1")
        vb, tb = VectorBatch(ctx), TextBatch(ctx)
        d = ArcvAdapter(_Shim(vb, tb))
        build(d, size[0], size[1], t)
        tgt.fbo.use()
        tgt.fbo.clear(*base_color[:3], 1.0)
        ctx.enable(moderngl.BLEND)
        ctx.blend_func = (moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA)  # premultiplied over
        vb.draw(size)
        tb.draw(size)
        ctx.disable(moderngl.BLEND)
        img = _read_rgb(tgt.fbo)
    else:
        theme = theme or make_theme("cyan")
        if glow is not None:
            theme.glow = glow
        ov = Overlay(ctx, size, theme=theme, base_color=base_color, grid=grid,
                     grid_cell=grid_cell, grid_alpha=grid_alpha, bloom_text=bloom_text)
        out = Target(ctx, size, 4, "f1")
        ov.begin()
        build(ArcvAdapter(ov), size[0], size[1], t)
        ov.render(t, target=out.fbo)
        img = ov.read_pixels(out.fbo)  # RGB uint8

    if bg_image:
        img = _composite_bg(img, bg_image, size, bg_mode)

    cv2.imwrite(out_path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    return out_path


def save_compare(ref_path: str, render_path: str, out_path: str, label: str = "") -> str:
    """Stack the reference (top) and the render (bottom) at equal width for
    quick visual grading."""
    def _resolve(p):
        return p if os.path.isabs(p) else os.path.join(_HERE, p)

    ref = cv2.imread(_resolve(ref_path), cv2.IMREAD_COLOR)
    ren = cv2.imread(_resolve(render_path), cv2.IMREAD_COLOR)
    if ref is None or ren is None:
        raise FileNotFoundError(f"missing {ref_path!r} or {render_path!r}")
    W = max(ref.shape[1], ren.shape[1])

    def _fit(im):
        h = int(im.shape[0] * W / im.shape[1])
        return cv2.resize(im, (W, h))

    ref, ren = _fit(ref), _fit(ren)
    gap = np.full((8, W, 3), 40, np.uint8)
    stack = np.vstack([ref, gap, ren])
    if label:
        cv2.putText(stack, label, (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (255, 255, 255), 2, cv2.LINE_AA)
    if not os.path.isabs(out_path):
        out_path = os.path.join(_HERE, out_path)
    cv2.imwrite(out_path, stack)
    return out_path
