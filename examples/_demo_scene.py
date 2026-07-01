"""Shared helpers for the examples: pick a frame source (camera / image /
synthetic) so the demos run with or without a webcam."""

from __future__ import annotations

import math

import cv2
import numpy as np


def synthetic_frame(w: int, h: int, t: float) -> np.ndarray:
    """A dark scene with moving bright shapes so edge/contour detection always
    has something to lock onto (no webcam required)."""
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    # faint diagonal gradient
    xx = np.linspace(10, 60, w, dtype=np.uint8)
    frame[:] = xx[None, :, None]

    # a drifting "object" rectangle
    ox = int((0.5 + 0.25 * math.sin(t * 0.6)) * w)
    oy = int((0.45 + 0.15 * math.cos(t * 0.5)) * h)
    cv2.rectangle(frame, (ox - 70, oy - 50), (ox + 70, oy + 50), (200, 210, 210), -1)

    # a bright moving disc
    dx = int((0.5 + 0.3 * math.cos(t * 0.9)) * w)
    dy = int((0.6 + 0.2 * math.sin(t * 1.1)) * h)
    cv2.circle(frame, (dx, dy), 45, (230, 230, 235), -1)

    # a static panel block
    cv2.rectangle(frame, (int(w * 0.12), int(h * 0.18)), (int(w * 0.30), int(h * 0.42)), (160, 170, 170), -1)
    return frame


class FrameSource:
    """Yields BGR frames sized (w, h) from a camera, an image, or synthetic."""

    def __init__(self, w, h, camera=None, image=None):
        self.w, self.h = w, h
        self.kind = "synthetic"
        self.cam = None
        self.img = None
        if camera is not None:
            try:
                from arcv.capture import CameraSource

                self.cam = CameraSource(index=camera, width=w, height=h).start()
                self.kind = "camera"
            except Exception as e:  # noqa: BLE001
                print(f"[demo] camera unavailable ({e}); falling back")
        if self.cam is None and image is not None:
            img = cv2.imread(image)
            if img is None:
                raise FileNotFoundError(image)
            self.img = cv2.resize(img, (w, h))
            self.kind = "image"

    def read(self, t: float) -> np.ndarray:
        if self.cam is not None:
            for _ in range(100):
                f = self.cam.read()
                if f is not None:
                    return cv2.resize(f, (self.w, self.h))
            return synthetic_frame(self.w, self.h, t)
        if self.img is not None:
            return self.img.copy()
        return synthetic_frame(self.w, self.h, t)

    def release(self):
        if self.cam is not None:
            self.cam.release()
