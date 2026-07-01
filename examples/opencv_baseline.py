"""The "best OpenCV can do" HUD, for the ARCV comparison.

Consumes the SAME DetectionFrame ARCV gets and draws a sci-fi-ish overlay using
only OpenCV CPU primitives: corner brackets (polylines), labels (putText), a
GaussianBlur+addWeighted glow approximation, a reticle, edge-trace, color grade,
and scanlines. This is the realistic ceiling of plain OpenCV — the thing ARCV's
GPU pipeline is compared against.
"""

from __future__ import annotations

import math
from typing import Tuple

import cv2
import numpy as np

CYAN = (255, 255, 0)  # BGR


def _rect_px(d, w, h) -> Tuple[int, int, int, int]:
    x0 = int((d.cx - d.hw) * w)
    x1 = int((d.cx + d.hw) * w)
    # UV is y-up; image is y-down
    y0 = int((1.0 - (d.cy + d.hh)) * h)
    y1 = int((1.0 - (d.cy - d.hh)) * h)
    return x0, y0, x1, y1


class OpenCVHud:
    def __init__(self, size: Tuple[int, int], glow_strength: float = 1.6) -> None:
        self.w, self.h = size
        self.glow_strength = glow_strength
        self._scan = self._build_scanlines(self.h, self.w)
        self._vignette = self._build_vignette(self.h, self.w)

    # -- static overlays ---------------------------------------------------
    @staticmethod
    def _build_scanlines(h, w):
        y = np.arange(h, dtype=np.float32)
        band = 0.5 + 0.5 * np.sin(y / h * 240.0 * math.pi)
        mask = (1.0 - 0.12 * (1.0 - band)).astype(np.float32)
        return mask[:, None, None]

    @staticmethod
    def _build_vignette(h, w):
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        cx, cy = w / 2.0, h / 2.0
        d = np.sqrt(((xx - cx) / w) ** 2 + ((yy - cy) / h) ** 2)
        vig = np.clip(1.0 - (d - 0.25) * 0.9, 0.72, 1.0)
        return vig[:, :, None]

    # -- grade -------------------------------------------------------------
    def grade(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray3 = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        desat = cv2.addWeighted(frame, 0.65, gray3, 0.35, 0)
        tint = desat.astype(np.float32) * np.array([1.12, 1.04, 0.62], np.float32)  # BGR
        graded = np.clip(tint * 0.82, 0, 255).astype(np.uint8)
        return graded

    # -- pieces ------------------------------------------------------------
    def _bracket(self, overlay, d):
        x0, y0, x1, y1 = _rect_px(d, self.w, self.h)
        arm = int(np.clip(min(x1 - x0, y1 - y0) * 0.35, 10, 80))
        s = int(np.clip(arm * 0.35, 6, 24))
        tl = [(x0, y0 + arm), (x0, y0 + s), (x0 + s, y0), (x0 + arm, y0)]
        br = [(x1, y1 - arm), (x1, y1 - s), (x1 - s, y1), (x1 - arm, y1)]
        for pts in (tl, br):
            cv2.polylines(overlay, [np.array(pts, np.int32)], False, CYAN, 2, cv2.LINE_AA)

    def _label(self, overlay, d):
        x0, y0, _, _ = _rect_px(d, self.w, self.h)
        cv2.putText(
            overlay, d.label or d.kind.upper(), (x0, max(12, y0 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, CYAN, 1, cv2.LINE_AA,
        )

    def _reticle(self, overlay, d, t):
        x0, y0, x1, y1 = _rect_px(d, self.w, self.h)
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        r = max(int(min(x1 - x0, y1 - y0) * 0.55), 18)
        cv2.circle(overlay, (cx, cy), r, CYAN, 1, cv2.LINE_AA)
        gap = int(r * 0.45)
        arm = int(r * 1.4)
        cv2.line(overlay, (cx + gap, cy), (cx + arm, cy), CYAN, 1, cv2.LINE_AA)
        cv2.line(overlay, (cx - gap, cy), (cx - arm, cy), CYAN, 1, cv2.LINE_AA)
        cv2.line(overlay, (cx, cy + gap), (cx, cy + arm), CYAN, 1, cv2.LINE_AA)
        cv2.line(overlay, (cx, cy - gap), (cx, cy - arm), CYAN, 1, cv2.LINE_AA)
        for k in range(4):
            th = t * 1.2 + k * (math.pi / 2)
            dx, dy = math.cos(th), math.sin(th)
            p0 = (int(cx + dx * r * 1.05), int(cy + dy * r * 1.05))
            p1 = (int(cx + dx * r * 1.28), int(cy + dy * r * 1.28))
            cv2.line(overlay, p0, p1, CYAN, 1, cv2.LINE_AA)

    def _edges(self, overlay, edges):
        if edges is None:
            return
        if edges.shape[:2] != (self.h, self.w):
            edges = cv2.resize(edges, (self.w, self.h))
        col = np.zeros_like(overlay)
        col[edges > 0] = CYAN
        cv2.addWeighted(overlay, 1.0, col, 0.4, 0, dst=overlay)

    # -- main --------------------------------------------------------------
    def render(self, frame, detections, t: float):
        base = self.grade(frame)
        overlay = np.zeros_like(frame)

        self._edges(overlay, detections.edges)
        for i, d in enumerate(detections.boxes):
            self._bracket(overlay, d)
            self._label(overlay, d)
            if i == detections.primary:
                self._reticle(overlay, d, t)

        # bloom approximation: blur the overlay and add it back
        glow = cv2.GaussianBlur(overlay, (0, 0), 8)
        hud = cv2.addWeighted(overlay, 1.0, glow, self.glow_strength, 0)
        out = cv2.add(base, hud)

        # scanlines + sweep + vignette
        out = (out.astype(np.float32) * self._scan)
        sweep_y = int((t * 0.15 % 1.0) * self.h)
        cv2.line(out, (0, sweep_y), (self.w, sweep_y), CYAN, 2, cv2.LINE_AA)
        out = np.clip(out * self._vignette, 0, 255).astype(np.uint8)
        return out
