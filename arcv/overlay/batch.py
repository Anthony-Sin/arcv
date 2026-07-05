"""Batched immediate-mode geometry for HUD overlays.

VectorBatch accumulates anti-aliased strokes and filled triangles into one draw
call; TextBatch does the same for colored glyph quads. Coordinates are in pixels
with a top-left origin (matching OpenCV), so the same layout code drives both
backends.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

import numpy as np

from .. import shaders
from . import anim
from ..components.text.atlas import FontAtlas

Color = Tuple[float, float, float, float]
Point = Tuple[float, float]
_TAU = math.pi * 2.0


class VectorBatch:
    def __init__(self, ctx) -> None:
        self.ctx = ctx
        self.prog = ctx.program(
            vertex_shader=shaders.load("vector.vert"),
            fragment_shader=shaders.load("vector.frag"),
        )
        self.data: List[float] = []
        self._buf = None
        self._vao = None
        self._cap = 0

    def clear(self) -> None:
        self.data = []

    # -- primitives --------------------------------------------------------
    def _vert(self, x, y, edge, color, hw) -> None:
        r, g, b, a = color
        self.data.extend((x, y, edge, r, g, b, a, hw))

    def segment(self, p0: Point, p1: Point, color: Color, width: float = 2.0) -> None:
        x0, y0 = p0
        x1, y1 = p1
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy)
        if L < 1e-6:
            return
        nx, ny = -dy / L, dx / L
        hw = max(width * 0.5, 0.4)
        ox, oy = nx * hw, ny * hw
        A = (x0 + ox, y0 + oy)
        B = (x0 - ox, y0 - oy)
        C = (x1 - ox, y1 - oy)
        D = (x1 + ox, y1 + oy)
        self._vert(A[0], A[1], 1.0, color, hw)
        self._vert(B[0], B[1], -1.0, color, hw)
        self._vert(C[0], C[1], -1.0, color, hw)
        self._vert(A[0], A[1], 1.0, color, hw)
        self._vert(C[0], C[1], -1.0, color, hw)
        self._vert(D[0], D[1], 1.0, color, hw)

    def line(self, p0: Point, p1: Point, color: Color, width: float = 2.0, reveal: float = 1.0) -> None:
        if reveal >= 1.0:
            self.segment(p0, p1, color, width)
        else:
            pts = anim.truncate_polyline([p0, p1], reveal)
            if len(pts) >= 2:
                self.segment(pts[0], pts[1], color, width)

    def polyline(self, pts: Sequence[Point], color: Color, width: float = 2.0,
                 closed: bool = False, reveal: float = 1.0) -> None:
        if reveal < 1.0:
            pts = anim.truncate_polyline(pts, reveal, closed)
            closed = False
        n = len(pts)
        if n < 2:
            return
        for i in range(n - 1):
            self.segment(pts[i], pts[i + 1], color, width)
        if closed:
            self.segment(pts[-1], pts[0], color, width)

    def rect(self, x0, y0, x1, y1, color: Color, width: float = 2.0, reveal: float = 1.0) -> None:
        self.polyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], color, width, closed=True, reveal=reveal)

    def arc(self, cx, cy, r, a0, a1, segments=48) -> List[Point]:
        return anim.arc_points(cx, cy, r, a0, a1, segments)

    def ring(self, cx, cy, r, color: Color, width: float = 2.0, a0=0.0, a1=_TAU,
             segments=64, reveal: float = 1.0) -> None:
        a1 = a0 + (a1 - a0) * reveal
        full = reveal >= 1.0 and abs((a1 - a0) - _TAU) < 1e-3
        self.polyline(self.arc(cx, cy, r, a0, a1, segments), color, width, closed=full)

    def _fill_fan(self, center: Point, pts: Sequence[Point], color: Color) -> None:
        cx, cy = center
        for i in range(len(pts) - 1):
            self._vert(cx, cy, 0.0, color, 1e4)
            self._vert(pts[i][0], pts[i][1], 0.0, color, 1e4)
            self._vert(pts[i + 1][0], pts[i + 1][1], 0.0, color, 1e4)

    def disc(self, cx, cy, r, color: Color, segments=28) -> None:
        ring = self.arc(cx, cy, r, 0.0, _TAU, segments)
        self._fill_fan((cx, cy), ring + [ring[0]], color)

    def dot(self, cx, cy, r, color: Color) -> None:
        self.disc(cx, cy, r, color, segments=14)

    def triangle_outline(self, p0, p1, p2, color: Color, width: float = 2.0) -> None:
        self.polyline([p0, p1, p2], color, width, closed=True)

    def triangle_fill(self, p0, p1, p2, color: Color) -> None:
        self._vert(p0[0], p0[1], 0.0, color, 1e4)
        self._vert(p1[0], p1[1], 0.0, color, 1e4)
        self._vert(p2[0], p2[1], 0.0, color, 1e4)

    def marker(self, cx, cy, local_pts: Sequence[Point], color: Color,
               angle: float = 0.0, scale: float = 1.0, width: float = 2.0,
               fill: bool = False, closed: bool = True, reveal: float = 1.0) -> None:
        """Draw a local-space shape rotated by ``angle`` (radians) at ``(cx, cy)``.

        This is the rotation-capable primitive the anim layer's motion-path
        follower needs: ``local_pts`` are defined around the origin (see
        ``anim.shape_triangle`` / ``shape_chevron``), scaled by ``scale``, rotated
        to face ``angle`` (e.g. the tangent from ``anim.sample_path``), then
        placed at ``(cx, cy)``. ``fill=True`` fans a solid shape; otherwise it is
        stroked (honouring ``reveal`` for draw-on).
        """
        c, s = math.cos(angle), math.sin(angle)
        world: List[Point] = []
        for lx, ly in local_pts:
            rx, ry = lx * scale, ly * scale
            world.append((cx + rx * c - ry * s, cy + rx * s + ry * c))
        if fill:
            if len(world) >= 3:
                self._fill_fan((cx, cy), world + [world[0]], color)
        else:
            self.polyline(world, color, width, closed=closed, reveal=reveal)

    # rounded rect ---------------------------------------------------------
    def _rrect_points(self, x0, y0, x1, y1, rad, seg=6) -> List[Point]:
        return anim.rrect_points(x0, y0, x1, y1, rad, seg)

    def rounded_rect(self, x0, y0, x1, y1, rad, color: Color, width: float = 2.0, reveal: float = 1.0) -> None:
        self.polyline(self._rrect_points(x0, y0, x1, y1, rad), color, width, closed=True, reveal=reveal)

    def rounded_rect_fill(self, x0, y0, x1, y1, rad, color: Color) -> None:
        pts = self._rrect_points(x0, y0, x1, y1, rad)
        self._fill_fan(((x0 + x1) * 0.5, (y0 + y1) * 0.5), pts + [pts[0]], color)

    # draw -----------------------------------------------------------------
    def _ensure(self, nbytes: int) -> None:
        if self._buf is None or nbytes > self._cap:
            if self._buf is not None:
                self._buf.release()
                self._vao.release()
            self._cap = max(nbytes, 1 << 16)
            self._buf = self.ctx.buffer(reserve=self._cap, dynamic=True)
            self._vao = self.ctx.vertex_array(
                self.prog, [(self._buf, "2f 1f 4f 1f", "in_pos", "in_edge", "in_color", "in_hw")]
            )

    def draw(self, resolution: Tuple[int, int]) -> None:
        if not self.data:
            return
        arr = np.asarray(self.data, dtype="f4")
        b = arr.tobytes()
        self._ensure(len(b))
        self._buf.write(b)
        self.prog["u_resolution"].value = (float(resolution[0]), float(resolution[1]))
        self._vao.render(vertices=len(arr) // 8)


class TextBatch:
    def __init__(self, ctx, atlas: FontAtlas = None) -> None:
        self.ctx = ctx
        self.atlas = atlas or FontAtlas()
        self.prog = ctx.program(
            vertex_shader=shaders.load("overlay_text.vert"),
            fragment_shader=shaders.load("overlay_text.frag"),
        )
        img = np.ascontiguousarray(self.atlas.image)
        self.tex = ctx.texture(
            (self.atlas.atlas_w, self.atlas.atlas_h), 1, img.tobytes(), dtype="f1", alignment=1
        )
        self.tex.filter = (9729, 9729)
        self.tex.repeat_x = False
        self.tex.repeat_y = False
        self.data: List[float] = []
        self._buf = None
        self._vao = None
        self._cap = 0

    def clear(self) -> None:
        self.data = []

    def advance(self, height: float) -> float:
        return height * self.atlas.aspect

    def measure(self, s: str, height: float) -> float:
        return len(s) * self.advance(height)

    def text(self, s, x, y, height, color: Color, align="left", mode="plain", t=0.0, progress=1.0) -> None:
        adv = self.advance(height)
        total = len(s) * adv
        if align == "center":
            x -= total * 0.5
        elif align == "right":
            x -= total
        r, g, b, a = color
        n = len(s)
        revealed = n if mode == "plain" else int(round(progress * n))
        bucket = int(t * 14.0)
        pool = self.atlas.scramble_pool
        for k, ch in enumerate(s):
            disp = ch
            if mode == "typeon" and k >= revealed:
                break
            if mode == "decipher" and k >= revealed and ch != " ":
                disp = pool[((bucket * 92821) ^ (k * 52711)) % len(pool)]
            if disp == " ":
                continue
            u0, u1 = self.atlas.u_range(disp)
            x0 = x + k * adv
            x1 = x0 + adv
            y0, y1 = y, y + height
            for (px, py, u, v) in (
                (x0, y0, u0, 0.0), (x1, y0, u1, 0.0), (x1, y1, u1, 1.0),
                (x0, y0, u0, 0.0), (x1, y1, u1, 1.0), (x0, y1, u0, 1.0),
            ):
                self.data.extend((px, py, u, v, r, g, b, a))

    def text_transformed(self, s, x, y, height, color: Color, align="left",
                         per_char=None, line_height: float = 1.3) -> None:
        """Draw text with an independent per-character transform — the static
        capability behind anime.js "split text".

        ``per_char`` is ``(k, ch) -> (dx, dy, alpha, scale)`` where ``k`` is the
        index into ``s`` (newlines included, matching :func:`anim.char_units`).
        Each glyph is scaled about its own centre, alpha-multiplied, then shifted
        by ``(dx, dy)`` — enough for per-unit fade / slide / scale-in entrances.
        Multi-line strings (``\\n``) are laid out so line-level staggers work.
        ``per_char=None`` renders plain text.
        """
        adv = self.advance(height)
        r, g, b, a = color
        lines = s.split("\n")
        line_len = [len(ln) for ln in lines]
        k = 0
        line = 0
        col = 0
        line_y = y
        base_x = self._align_x(x, line_len[0] * adv, align)
        for ch in s:
            if ch == "\n":
                line += 1
                col = 0
                line_y += height * line_height
                base_x = self._align_x(x, line_len[line] * adv, align)
                k += 1
                continue
            dx = dy = 0.0
            alpha = 1.0
            scale = 1.0
            if per_char is not None:
                res = per_char(k, ch)
                if res is not None:
                    dx = res[0]
                    dy = res[1]
                    alpha = res[2] if len(res) > 2 else 1.0
                    scale = res[3] if len(res) > 3 else 1.0
            k += 1
            col_x = base_x + col * adv
            col += 1
            if ch == " " or alpha <= 0.0 or scale <= 0.0:
                continue
            u0, u1 = self.atlas.u_range(ch)
            x0, x1 = col_x, col_x + adv
            y0, y1 = line_y, line_y + height
            cx, cy = (x0 + x1) * 0.5, (y0 + y1) * 0.5
            # scale about the glyph centre, then translate
            x0 = cx + (x0 - cx) * scale + dx
            x1 = cx + (x1 - cx) * scale + dx
            y0 = cy + (y0 - cy) * scale + dy
            y1 = cy + (y1 - cy) * scale + dy
            ca = a * alpha
            for (px, py, u, v) in (
                (x0, y0, u0, 0.0), (x1, y0, u1, 0.0), (x1, y1, u1, 1.0),
                (x0, y0, u0, 0.0), (x1, y1, u1, 1.0), (x0, y1, u0, 1.0),
            ):
                self.data.extend((px, py, u, v, r, g, b, ca))

    @staticmethod
    def _align_x(x: float, total: float, align: str) -> float:
        if align == "center":
            return x - total * 0.5
        if align == "right":
            return x - total
        return x

    def _ensure(self, nbytes: int) -> None:
        if self._buf is None or nbytes > self._cap:
            if self._buf is not None:
                self._buf.release()
                self._vao.release()
            self._cap = max(nbytes, 1 << 16)
            self._buf = self.ctx.buffer(reserve=self._cap, dynamic=True)
            self._vao = self.ctx.vertex_array(
                self.prog, [(self._buf, "2f 2f 4f", "in_pos", "in_auv", "in_color")]
            )

    def draw(self, resolution: Tuple[int, int]) -> None:
        if not self.data:
            return
        arr = np.asarray(self.data, dtype="f4")
        b = arr.tobytes()
        self._ensure(len(b))
        self._buf.write(b)
        self.tex.use(0)
        self.prog["u_atlas"].value = 0
        self.prog["u_resolution"].value = (float(resolution[0]), float(resolution[1]))
        self._vao.render(vertices=len(arr) // 8)
