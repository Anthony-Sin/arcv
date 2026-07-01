"""DetectorPipeline — runs the enabled OpenCV detectors on a frame and returns a
normalized DetectionFrame with stable ids (so HUD animators can play enter/exit
as targets appear and disappear).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import cv2
import numpy as np

from .detectors import (
    ContourDetector,
    EdgeDetector,
    FaceDetector,
    ORBDetector,
    OpticalFlowDetector,
    YuNetFaceDetector,
)
from .types import Detection, DetectionFrame


class _Tracker:
    """Minimal nearest-center id assignment across frames."""

    def __init__(self, max_dist: float = 0.12) -> None:
        self.max_dist = max_dist
        self._prev: List[Tuple[int, float, float]] = []  # (id, cx, cy)
        self._next_id = 0

    def assign(self, dets: List[Detection]) -> None:
        used = set()
        for d in dets:
            best_id, best_dist = -1, self.max_dist
            for idx, (pid, px, py) in enumerate(self._prev):
                if idx in used:
                    continue
                dist = ((d.cx - px) ** 2 + (d.cy - py) ** 2) ** 0.5
                if dist < best_dist:
                    best_dist, best_id, best_idx = dist, pid, idx
            if best_id >= 0:
                d.id = best_id
                used.add(best_idx)
            else:
                d.id = self._next_id
                self._next_id += 1
        self._prev = [(d.id, d.cx, d.cy) for d in dets]


class DetectorPipeline:
    def __init__(
        self,
        enable_faces: bool = True,
        enable_edges: bool = True,
        enable_contours: bool = True,
        enable_flow: bool = False,
        enable_orb: bool = False,
        face_backend: str = "haar",
        yunet_model: str = None,
        max_boxes: int = 16,
        max_points: int = 64,
        edge_downscale: int = 1,
    ) -> None:
        self.max_boxes = max_boxes
        self.max_points = max_points
        self.edge_downscale = max(1, edge_downscale)

        self.faces = None
        self._face_is_yunet = False
        if enable_faces:
            if face_backend == "yunet":
                try:
                    self.faces = YuNetFaceDetector(model_path=yunet_model)
                    self._face_is_yunet = True
                except Exception as e:  # noqa: BLE001 - fall back to Haar
                    print(f"[arcv] YuNet unavailable ({e}); using Haar cascade")
                    self.faces = FaceDetector()
            else:
                self.faces = FaceDetector()

        self.edges = EdgeDetector() if enable_edges else None
        self.contours = ContourDetector() if enable_contours else None
        self.flow = OpticalFlowDetector() if enable_flow else None
        self.orb = ORBDetector(n_features=max_points) if enable_orb else None
        self._tracker = _Tracker()

    def process(self, frame_bgr: np.ndarray) -> DetectionFrame:
        h, w = frame_bgr.shape[:2]
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

        boxes: List[Detection] = []
        face_landmarks: List[Tuple[float, float]] = []  # px

        if self.faces is not None:
            if self._face_is_yunet:
                for (x, y, fw, fh, score, lms) in self.faces.detect(frame_bgr):
                    boxes.append(
                        Detection.from_pixel_rect(
                            x, y, fw, fh, w, h, kind="face", score=score
                        )
                    )
                    for (lx, ly) in lms:
                        face_landmarks.append((float(lx), float(ly)))
            else:
                for (x, y, fw, fh) in self.faces.detect(gray):
                    boxes.append(
                        Detection.from_pixel_rect(
                            x, y, fw, fh, w, h, kind="face", score=1.0
                        )
                    )

        edge_mask: Optional[np.ndarray] = None
        if self.edges is not None:
            if self.edge_downscale > 1:
                small = cv2.resize(
                    gray, (w // self.edge_downscale, h // self.edge_downscale)
                )
                edge_mask = self.edges.detect(small)
            else:
                edge_mask = self.edges.detect(gray)

        if self.contours is not None and edge_mask is not None:
            mh, mw = edge_mask.shape[:2]
            for (x, y, cw, ch) in self.contours.detect(edge_mask):
                # scale contour rect back to full-res pixel space
                sx, sy = w / mw, h / mh
                boxes.append(
                    Detection.from_pixel_rect(
                        int(x * sx),
                        int(y * sy),
                        int(cw * sx),
                        int(ch * sy),
                        w,
                        h,
                        kind="object",
                        score=0.8,
                    )
                )

        boxes = boxes[: self.max_boxes]
        self._tracker.assign(boxes)
        for d in boxes:
            if not d.label:
                tag = "TGT" if d.kind == "face" else "OBJ"
                d.label = f"{tag}-{d.id:02d}"

        flow_mag = self.flow.detect(gray) if self.flow is not None else 0.0

        keypoints = []
        if self.orb is not None:
            for (kx, ky) in self.orb.detect(gray):
                keypoints.append((kx / w, 1.0 - ky / h))  # UV, y-up
        # YuNet facial landmarks become tracker points too
        for (lx, ly) in face_landmarks:
            keypoints.append((lx / w, 1.0 - ly / h))

        primary = self._pick_primary(boxes)
        return DetectionFrame(
            boxes=boxes,
            edges=edge_mask,
            frame_size=(w, h),
            primary=primary,
            flow_mag=flow_mag,
            keypoints=keypoints,
        )

    @staticmethod
    def _pick_primary(boxes: List[Detection]) -> int:
        faces = [(i, d.area) for i, d in enumerate(boxes) if d.kind == "face"]
        pool = faces if faces else [(i, d.area) for i, d in enumerate(boxes)]
        if not pool:
            return -1
        return max(pool, key=lambda t: t[1])[0]
