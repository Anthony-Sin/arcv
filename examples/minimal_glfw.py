"""Live windowed ARCV demo.

This is the one example that needs a window library:
    pip install "moderngl-window>=3,<4" glfw

The ARCV library itself is window-agnostic; here moderngl-window owns the window
and GL context, and we just drive a Scene from its render loop.

    python examples/minimal_glfw.py            # webcam 0 (falls back to synthetic)
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(_HERE))

import moderngl_window as mglw  # noqa: E402

from arcv.scene import Scene  # noqa: E402
from arcv.theme import make_theme  # noqa: E402
from arcv.vision.pipeline import DetectorPipeline  # noqa: E402
from _demo_scene import FrameSource  # noqa: E402

# moderngl-window owns argv, so configure via env vars:
#   ARCV_THEME=amber ARCV_FRAME=octagon ARCV_BG=gridlines,movinglines \
#   ARCV_FACES=yunet ARCV_KEYPOINTS=1 python examples/minimal_glfw.py
_THEME = os.environ.get("ARCV_THEME", "cyan")
_FRAME = os.environ.get("ARCV_FRAME", "nefrex")
_TEXT = os.environ.get("ARCV_TEXT", "decipher")
_BG = [b for b in os.environ.get("ARCV_BG", "").split(",") if b]
_FACES = os.environ.get("ARCV_FACES", "haar")
_KEYPOINTS = os.environ.get("ARCV_KEYPOINTS", "") not in ("", "0", "false")


class ARCVApp(mglw.WindowConfig):
    gl_version = (3, 3)
    title = "ARCV"
    window_size = (1280, 720)
    resizable = True
    vsync = True
    aspect_ratio = None  # allow free resize

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        w, h = self.wnd.buffer_size
        pipeline = DetectorPipeline(
            enable_orb=_KEYPOINTS, enable_flow=bool(_BG), face_backend=_FACES
        )
        self.scene = Scene(
            self.ctx, (w, h), theme=make_theme(_THEME), detector=pipeline,
            frame_style=_FRAME, text_style=_TEXT, backgrounds=_BG,
            show_keypoints=_KEYPOINTS, upload="double",
        )
        # camera 0; FrameSource falls back to a synthetic scene if unavailable
        self.source = FrameSource(w, h, camera=0)

    def on_render(self, t: float, frametime: float):
        frame = self.source.read(t)
        self.scene.submit(frame)
        self.scene.render(t)  # default target = ctx.screen

    def on_resize(self, width: int, height: int):
        self.scene.resize(width, height)

    def on_mouse_position_event(self, x, y, dx, dy):
        self.scene.set_mouse(x, y)

    def on_close(self):
        self.source.release()


if __name__ == "__main__":
    mglw.run_window_config(ARCVApp)
