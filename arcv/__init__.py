"""ARCV — an Arwes-style sci-fi HUD rendered with ModernGL GLSL shaders over a
live OpenCV camera feed.

Library-only: you own the window + GL context + main loop. Create a
:class:`~arcv.scene.Scene` against an existing ``moderngl.Context``, feed it
camera frames, and call ``render()``.
"""

from . import easing, theme, animator
from .theme import Theme, make_theme, THEME_PRESETS
from .animator import Animator
from .vision import (
    Detection,
    DetectionFrame,
    DetectorPipeline,
    FaceDetector,
    YuNetFaceDetector,
    EdgeDetector,
    ContourDetector,
    OpticalFlowDetector,
    ORBDetector,
    default_yunet_path,
    download_yunet,
)
from .capture import CameraSource, MultiCameraSource, enumerate_cameras

__all__ = [
    "easing",
    "theme",
    "animator",
    "Theme",
    "make_theme",
    "THEME_PRESETS",
    "Animator",
    "Detection",
    "DetectionFrame",
    "DetectorPipeline",
    "FaceDetector",
    "YuNetFaceDetector",
    "EdgeDetector",
    "ContourDetector",
    "OpticalFlowDetector",
    "ORBDetector",
    "default_yunet_path",
    "download_yunet",
    "CameraSource",
    "MultiCameraSource",
    "enumerate_cameras",
]

# style registries (names accepted by Scene)
from .components.frames import FRAME_STYLES  # noqa: E402
from .components.backgrounds import BACKGROUND_STYLES  # noqa: E402
from .components.text import TEXT_STYLES  # noqa: E402

__all__ += ["FRAME_STYLES", "BACKGROUND_STYLES", "TEXT_STYLES"]

# Overlay UI kit (lay out HUD elements at fixed positions, no camera needed)
from .overlay import Overlay  # noqa: E402

__all__ += ["Overlay"]

# Synthesized HUD audio (bleeps): live playback + cue-list MP4 audio export
from . import audio  # noqa: E402
from .audio import Bleeps, CueScheduler  # noqa: E402

__all__ += ["audio", "Bleeps", "CueScheduler"]

# Scene + components pull in the GPU stack; import lazily so the pure-Python /
# CV layer can be used (and unit-tested) without a GL context.
try:  # pragma: no cover - optional GPU import
    from .scene import Scene  # noqa: F401

    __all__.append("Scene")
except Exception:  # noqa: BLE001
    pass
