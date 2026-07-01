"""OpenCV detectors. Each is a thin wrapper returning raw OpenCV results; the
DetectorPipeline normalizes them into a DetectionFrame.
"""

from __future__ import annotations

import os
import urllib.request
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

Rect = Tuple[int, int, int, int]

# YuNet model resolution: env override -> bundled resources/models -> None.
_YUNET_FILENAME = "face_detection_yunet_2023mar.onnx"
_YUNET_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/models/"
    "face_detection_yunet/" + _YUNET_FILENAME
)


def default_yunet_path() -> Optional[str]:
    env = os.environ.get("ARCV_YUNET_MODEL")
    if env and Path(env).is_file():
        return env
    bundled = Path(__file__).resolve().parent.parent / "resources" / "models" / _YUNET_FILENAME
    return str(bundled) if bundled.is_file() else None


def download_yunet(dest: Optional[str] = None) -> str:
    """Download the YuNet ONNX model to ``dest`` (defaults to resources/models).
    Returns the path. Requires network access."""
    if dest is None:
        dest = str(
            Path(__file__).resolve().parent.parent / "resources" / "models" / _YUNET_FILENAME
        )
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(_YUNET_URL, dest)
    return dest


class FaceDetector:
    """Haar-cascade frontal-face detector (CPU, bundled with OpenCV)."""

    def __init__(
        self,
        scale_factor: float = 1.1,
        min_neighbors: int = 5,
        min_size_frac: float = 0.08,
    ) -> None:
        path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._clf = cv2.CascadeClassifier(path)
        if self._clf.empty():
            raise RuntimeError(f"Failed to load Haar cascade at {path}")
        self.scale_factor = scale_factor
        self.min_neighbors = min_neighbors
        self.min_size_frac = min_size_frac

    def detect(self, gray: np.ndarray) -> List[Rect]:
        h = gray.shape[0]
        min_side = max(16, int(h * self.min_size_frac))
        faces = self._clf.detectMultiScale(
            gray,
            scaleFactor=self.scale_factor,
            minNeighbors=self.min_neighbors,
            minSize=(min_side, min_side),
        )
        return [tuple(int(v) for v in f) for f in faces]


class YuNetFaceDetector:
    """DNN face detector (OpenCV FaceDetectorYN). More robust than Haar and also
    returns 5 facial landmarks (eyes, nose, mouth corners). Operates on the BGR
    frame (not grayscale)."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        score_threshold: float = 0.7,
        nms_threshold: float = 0.3,
        top_k: int = 50,
    ) -> None:
        path = model_path or default_yunet_path()
        if not path:
            raise FileNotFoundError(
                "YuNet model not found. Set ARCV_YUNET_MODEL or call "
                "arcv.vision.detectors.download_yunet()."
            )
        self._det = cv2.FaceDetectorYN.create(
            path, "", (320, 320), score_threshold, nms_threshold, top_k
        )
        self._size = (320, 320)

    def detect(self, frame_bgr: np.ndarray):
        """Returns list of (x, y, w, h, score, landmarks[5,2] in px)."""
        h, w = frame_bgr.shape[:2]
        if self._size != (w, h):
            self._det.setInputSize((w, h))
            self._size = (w, h)
        _, faces = self._det.detect(frame_bgr)
        out = []
        if faces is not None:
            for f in faces:
                x, y, bw, bh = f[0:4]
                landmarks = f[4:14].reshape(5, 2)
                score = float(f[14])
                out.append((int(x), int(y), int(bw), int(bh), score, landmarks))
        return out


class EdgeDetector:
    """Canny edge detector -> single-channel uint8 mask."""

    def __init__(self, threshold1: float = 80.0, threshold2: float = 160.0) -> None:
        self.threshold1 = threshold1
        self.threshold2 = threshold2

    def detect(self, gray: np.ndarray) -> np.ndarray:
        return cv2.Canny(gray, self.threshold1, self.threshold2)


class OpticalFlowDetector:
    """Dense Farneback optical flow on a downscaled gray frame. Returns the
    mean motion magnitude normalized to ~[0, 1] (useful as a HUD driver)."""

    def __init__(self, downscale: int = 4, gain: float = 0.15) -> None:
        self.downscale = max(1, downscale)
        self.gain = gain
        self._prev = None

    def detect(self, gray: np.ndarray) -> float:
        small = cv2.resize(
            gray, (gray.shape[1] // self.downscale, gray.shape[0] // self.downscale)
        )
        if self._prev is None or self._prev.shape != small.shape:
            self._prev = small
            return 0.0
        flow = cv2.calcOpticalFlowFarneback(
            self._prev, small, None, 0.5, 2, 15, 2, 5, 1.1, 0
        )
        self._prev = small
        mag = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2).mean()
        return float(np.clip(mag * self.gain, 0.0, 1.0))


class ORBDetector:
    """ORB keypoints -> list of (x, y) pixel points."""

    def __init__(self, n_features: int = 64) -> None:
        self._orb = cv2.ORB_create(nfeatures=n_features)
        self.n_features = n_features

    def detect(self, gray: np.ndarray) -> List[Tuple[int, int]]:
        kps = self._orb.detect(gray, None)
        return [(int(k.pt[0]), int(k.pt[1])) for k in kps[: self.n_features]]


class ContourDetector:
    """Find object-ish bounding boxes from an edge/binary mask."""

    def __init__(self, min_area_frac: float = 0.01, max_boxes: int = 8) -> None:
        self.min_area_frac = min_area_frac
        self.max_boxes = max_boxes

    def detect(self, mask: np.ndarray) -> List[Rect]:
        h, w = mask.shape[:2]
        frame_area = float(w * h)
        # Dilate so nearby edges merge into a single object blob.
        kernel = np.ones((5, 5), np.uint8)
        closed = cv2.dilate(mask, kernel, iterations=2)
        contours, _ = cv2.findContours(
            closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        rects: List[Tuple[float, Rect]] = []
        for c in contours:
            area = cv2.contourArea(c)
            if area < self.min_area_frac * frame_area:
                continue
            rects.append((area, tuple(int(v) for v in cv2.boundingRect(c))))
        rects.sort(key=lambda r: r[0], reverse=True)
        return [r for _, r in rects[: self.max_boxes]]
