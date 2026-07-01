"""Two drawing backends with one interface, so a single layout drives both.

ArcvAdapter -> ARCV Overlay (GPU vector/text batches + HDR bloom).
OpenCVAdapter -> plain cv2 primitives onto a numpy image (CPU).

Colors are RGBA floats in [0, 1]. Coordinates are pixels, top-left origin.
"""

from __future__ import annotations

import math

import cv2
import numpy as np

from arcv.overlay import anim

_TAU = math.pi * 2.0


class ArcvAdapter:
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

    def text(self, s, x, y, h, c, align="left", mode="plain", t=0.0, progress=1.0):
        self.ov.text.text(s, x, y, h, c, align, mode, t, progress)

    def text_width(self, s, h):
        return self.ov.text.measure(s, h)


class OpenCVAdapter:
    """Best-effort cyberpunk HUD with cv2. Draws onto an overlay image; the
    caller blurs it for the glow approximation."""

    def __init__(self, img) -> None:
        self.img = img  # BGR uint8

    @staticmethod
    def _bgr(c):
        r, g, b, a = c
        return (int(b * 255 * a), int(g * 255 * a), int(r * 255 * a))

    def _draw_pts(self, pts, c, w, closed):
        if len(pts) < 2:
            return
        arr = np.array([(int(x), int(y)) for x, y in pts], np.int32)
        cv2.polylines(self.img, [arr], closed, self._bgr(c), max(1, round(w)), cv2.LINE_AA)

    def line(self, x0, y0, x1, y1, c, w=2.0, reveal=1.0):
        if reveal < 1.0:
            self._draw_pts(anim.truncate_polyline([(x0, y0), (x1, y1)], reveal), c, w, False)
        else:
            cv2.line(self.img, (int(x0), int(y0)), (int(x1), int(y1)),
                     self._bgr(c), max(1, round(w)), cv2.LINE_AA)

    def poly(self, pts, c, w=2.0, closed=False, reveal=1.0):
        if reveal < 1.0:
            self._draw_pts(anim.truncate_polyline(pts, reveal, closed), c, w, False)
        else:
            self._draw_pts(pts, c, w, closed)

    def rect(self, x0, y0, x1, y1, c, w=2.0, reveal=1.0):
        if reveal < 1.0:
            self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], c, w, True, reveal)
        else:
            cv2.rectangle(self.img, (int(x0), int(y0)), (int(x1), int(y1)),
                          self._bgr(c), max(1, round(w)), cv2.LINE_AA)

    def rrect(self, x0, y0, x1, y1, r, c, w=2.0, reveal=1.0):
        if reveal < 1.0:
            self.poly(anim.rrect_points(x0, y0, x1, y1, r), c, w, True, reveal)
            return
        col, t = self._bgr(c), max(1, round(w))
        x0, y0, x1, y1, r = int(x0), int(y0), int(x1), int(y1), int(r)
        cv2.line(self.img, (x0 + r, y0), (x1 - r, y0), col, t, cv2.LINE_AA)
        cv2.line(self.img, (x0 + r, y1), (x1 - r, y1), col, t, cv2.LINE_AA)
        cv2.line(self.img, (x0, y0 + r), (x0, y1 - r), col, t, cv2.LINE_AA)
        cv2.line(self.img, (x1, y0 + r), (x1, y1 - r), col, t, cv2.LINE_AA)
        cv2.ellipse(self.img, (x0 + r, y0 + r), (r, r), 180, 0, 90, col, t, cv2.LINE_AA)
        cv2.ellipse(self.img, (x1 - r, y0 + r), (r, r), 270, 0, 90, col, t, cv2.LINE_AA)
        cv2.ellipse(self.img, (x1 - r, y1 - r), (r, r), 0, 0, 90, col, t, cv2.LINE_AA)
        cv2.ellipse(self.img, (x0 + r, y1 - r), (r, r), 90, 0, 90, col, t, cv2.LINE_AA)

    def rrect_fill(self, x0, y0, x1, y1, r, c):
        col = self._bgr(c)
        x0, y0, x1, y1, r = int(x0), int(y0), int(x1), int(y1), int(r)
        cv2.rectangle(self.img, (x0 + r, y0), (x1 - r, y1), col, -1)
        cv2.rectangle(self.img, (x0, y0 + r), (x1, y1 - r), col, -1)
        for (cx, cy) in ((x0 + r, y0 + r), (x1 - r, y0 + r), (x1 - r, y1 - r), (x0 + r, y1 - r)):
            cv2.circle(self.img, (cx, cy), r, col, -1, cv2.LINE_AA)

    def ring(self, cx, cy, r, c, w=2.0, a0=0.0, a1=_TAU, reveal=1.0):
        a1 = a0 + (a1 - a0) * reveal
        cv2.ellipse(self.img, (int(cx), int(cy)), (int(r), int(r)), 0,
                    math.degrees(a0), math.degrees(a1), self._bgr(c), max(1, round(w)), cv2.LINE_AA)

    def disc(self, cx, cy, r, c):
        cv2.circle(self.img, (int(cx), int(cy)), int(r), self._bgr(c), -1, cv2.LINE_AA)

    def tri(self, p0, p1, p2, c, w=2.0, reveal=1.0):
        self.poly([p0, p1, p2], c, w, closed=True, reveal=reveal)

    def tri_fill(self, p0, p1, p2, c):
        arr = np.array([(int(x), int(y)) for x, y in (p0, p1, p2)], np.int32)
        cv2.fillPoly(self.img, [arr], self._bgr(c), cv2.LINE_AA)

    _POOL = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#%&/()=?<>"

    def text(self, s, x, y, h, c, align="left", mode="plain", t=0.0, progress=1.0):
        if mode != "plain":
            n = len(s)
            revealed = int(round(progress * n))
            if mode == "typeon":
                s = s[:revealed]
            elif mode == "decipher":
                bucket = int(t * 14.0)
                out = []
                for k, ch in enumerate(s):
                    if k < revealed or ch == " ":
                        out.append(ch)
                    else:
                        out.append(self._POOL[((bucket * 92821) ^ (k * 52711)) % len(self._POOL)])
                s = "".join(out)
            if not s:
                return
        scale = h / 22.0
        thick = max(1, round(h / 18.0))
        (tw, th), _ = cv2.getTextSize(s, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
        if align == "center":
            x -= tw / 2
        elif align == "right":
            x -= tw
        cv2.putText(self.img, s, (int(x), int(y + h * 0.92)),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, self._bgr(c), thick, cv2.LINE_AA)

    def text_width(self, s, h):
        scale = h / 22.0
        thick = max(1, round(h / 18.0))
        (tw, _), _ = cv2.getTextSize(s, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
        return tw
