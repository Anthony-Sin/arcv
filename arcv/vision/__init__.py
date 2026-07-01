"""Computer-vision layer: capture-agnostic detectors that turn a camera frame
into normalized HUD-ready geometry."""

from .types import Detection, DetectionFrame
from .detectors import (
    FaceDetector,
    YuNetFaceDetector,
    EdgeDetector,
    ContourDetector,
    OpticalFlowDetector,
    ORBDetector,
    default_yunet_path,
    download_yunet,
)
from .pipeline import DetectorPipeline

__all__ = [
    "Detection",
    "DetectionFrame",
    "FaceDetector",
    "YuNetFaceDetector",
    "EdgeDetector",
    "ContourDetector",
    "OpticalFlowDetector",
    "ORBDetector",
    "DetectorPipeline",
    "default_yunet_path",
    "download_yunet",
]
