"""A library-owned pixel-coordinate drawing surface over an :class:`Overlay`.

``Draw`` wraps an :class:`~arcv.overlay.renderer.Overlay` and exposes a small,
flat drawing interface — lines, polylines, rects, rings, discs, triangles, and
text — in **pixel coordinates** (top-left origin), with colors as **RGBA floats
in [0, 1]**. It simply delegates to ``ov.vector.*`` / ``ov.text.*``.

This is the surface every :mod:`arcv.overlay.hud_kit` primitive draws through
(the primitives take a ``Draw`` — or any duck-typed object with the same
interface — as their first argument), so hand-laid HUDs can compose the kit's
badges, gauges, wireframes, etc. onto a bloom/composite overlay.

    from arcv.overlay import Overlay, Draw
    ov = Overlay(ctx, (1280, 720)); d = Draw(ov)
    ov.begin()
    d.ring(640, 360, 90, (0, 1, 1, 1), 2.0)
    ov.render(0.0, target=fbo)
"""

from __future__ import annotations

import math

_TAU = math.pi * 2.0


class Draw:
    """Flat pixel-coordinate drawing surface over an :class:`Overlay`.

    Parameters
    ----------
    overlay:
        Anything exposing ``.vector`` (a ``VectorBatch``) and ``.text`` (a
        ``TextBatch``) — normally an :class:`~arcv.overlay.renderer.Overlay`.

    All colors are RGBA floats in ``[0, 1]``; all coordinates are pixels with a
    top-left origin.
    """

    def __init__(self, overlay) -> None:
        self.ov = overlay

    def line(self, x0, y0, x1, y1, c, w=2.0, reveal=1.0):
        self.ov.vector.line((x0, y0), (x1, y1), c, w, reveal)

    def poly(self, pts, c, w=2.0, closed=False, reveal=1.0):
        self.ov.vector.polyline(pts, c, w, closed, reveal)

    def rect(self, x0, y0, x1, y1, c, w=2.0, reveal=1.0):
        self.ov.vector.rect(x0, y0, x1, y1, c, w, reveal)

    def rrect(self, x0, y0, x1, y1, r, c, w=2.0, reveal=1.0):
        self.ov.vector.rounded_rect(x0, y0, x1, y1, r, c, w, reveal)

    def rrect_fill(self, x0, y0, x1, y1, r, c):
        self.ov.vector.rounded_rect_fill(x0, y0, x1, y1, r, c)

    def ring(self, cx, cy, r, c, w=2.0, a0=0.0, a1=_TAU, reveal=1.0):
        self.ov.vector.ring(cx, cy, r, c, w, a0, a1, reveal=reveal)

    def disc(self, cx, cy, r, c):
        self.ov.vector.disc(cx, cy, r, c)

    def tri(self, p0, p1, p2, c, w=2.0, reveal=1.0):
        self.ov.vector.polyline([p0, p1, p2], c, w, True, reveal)

    def tri_fill(self, p0, p1, p2, c):
        self.ov.vector.triangle_fill(p0, p1, p2, c)

    def marker(self, cx, cy, local_pts, c, angle=0.0, scale=1.0, w=2.0,
               fill=False, closed=True, reveal=1.0):
        self.ov.vector.marker(cx, cy, local_pts, c, angle, scale, w, fill, closed, reveal)

    def text(self, s, x, y, h, c, align="left", mode="plain", t=0.0, progress=1.0):
        self.ov.text.text(s, x, y, h, c, align, mode, t, progress)

    def text_fx(self, s, x, y, h, c, align="left", per_char=None, line_height=1.3):
        self.ov.text.text_transformed(s, x, y, h, c, align, per_char, line_height)

    def text_width(self, s, h):
        return self.ov.text.measure(s, h)
