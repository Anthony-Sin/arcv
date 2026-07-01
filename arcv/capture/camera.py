"""Threaded camera capture.

Reads frames on a background thread and publishes only the latest copy, so the
render loop never blocks on ``cap.read()`` and never accumulates stale frames.
Each published frame is a ``uint8`` ``(H, W, 3)`` BGR numpy array — the exact
handoff format the renderer uploads to a GPU texture.
"""

from __future__ import annotations

import sys
import threading
from typing import Optional, Tuple

import cv2
import numpy as np


def _default_backend() -> int:
    # DSHOW opens fast with low first-frame latency on Windows.
    if sys.platform.startswith("win"):
        return cv2.CAP_DSHOW
    return cv2.CAP_ANY


class CameraSource:
    def __init__(
        self,
        index: int = 0,
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
        backend: Optional[int] = None,
    ) -> None:
        self.index = index
        self.req_width = width
        self.req_height = height
        self.req_fps = fps
        self.backend = _default_backend() if backend is None else backend

        self._cap: Optional[cv2.VideoCapture] = None
        self._frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self.width = width
        self.height = height

    def start(self) -> "CameraSource":
        cap = cv2.VideoCapture(self.index, self.backend)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open camera index {self.index}")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.req_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.req_height)
        cap.set(cv2.CAP_PROP_FPS, self.req_fps)
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass
        # Use the actual negotiated size, not the requested one.
        self.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or self.req_width
        self.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or self.req_height
        self._cap = cap

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def _loop(self) -> None:
        assert self._cap is not None
        while self._running:
            ok, frame = self._cap.read()
            if not ok or frame is None:
                continue
            with self._lock:
                self._frame = frame.copy()  # decouple from OpenCV's reused buffer

    def read(self) -> Optional[np.ndarray]:
        """Return the latest frame (a copy-safe reference) or None if not ready."""
        with self._lock:
            return self._frame

    @property
    def size(self) -> Tuple[int, int]:
        return (self.width, self.height)

    def release(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self) -> "CameraSource":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.release()


def enumerate_cameras(max_index: int = 5, backend: Optional[int] = None) -> list:
    """Probe device indices [0, max_index) and return those that open and yield a
    frame. Useful for letting a UI pick among multiple cameras."""
    backend = _default_backend() if backend is None else backend
    found = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i, backend)
        try:
            if cap.isOpened():
                ok, frame = cap.read()
                if ok and frame is not None:
                    found.append(i)
        finally:
            cap.release()
    return found


class MultiCameraSource:
    """Manage several CameraSources, exposing one active feed at a time with
    ``switch()`` / ``next()``. All feeds run in their own capture threads."""

    def __init__(self, indices, width: int = 1280, height: int = 720, fps: int = 30):
        self.sources = [CameraSource(i, width, height, fps) for i in indices]
        self.indices = list(indices)
        self._active = 0

    def start(self) -> "MultiCameraSource":
        for s in self.sources:
            s.start()
        return self

    @property
    def active_index(self) -> int:
        return self.indices[self._active] if self.sources else -1

    def switch(self, slot: int) -> None:
        if 0 <= slot < len(self.sources):
            self._active = slot

    def next(self) -> None:
        if self.sources:
            self._active = (self._active + 1) % len(self.sources)

    def read(self):
        return self.sources[self._active].read() if self.sources else None

    @property
    def size(self):
        return self.sources[self._active].size if self.sources else (0, 0)

    def release(self) -> None:
        for s in self.sources:
            s.release()

    def __enter__(self) -> "MultiCameraSource":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.release()
