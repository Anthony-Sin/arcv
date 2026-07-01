"""Scene — the conductor.

Library-only: construct against an existing ``moderngl.Context`` and a render
size. Feed frames with :meth:`submit`, then call :meth:`render` from your own
loop. The Scene never creates a window or context.

Per frame::

    detections = pipeline.process(frame)      # or let the Scene do it
    scene.submit(frame, detections)           # upload texture + edge mask, track ids
    scene.render(time)                         # 4-pass pipeline -> target FBO

Configurable look::

    Scene(ctx, size,
          frame_style="nefrex",               # corners/lines/octagon/underline/kranox
          text_style="decipher",              # or "typeon"
          backgrounds=("gridlines", "movinglines"),
          show_keypoints=True)
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np

from . import geometry
from .animator import Animator, EXITED
from .components import TrackerDots
from .components.backgrounds import BACKGROUND_STYLES
from .components.effects import EdgeTrace, Illuminator, Reticle
from .components.frames import FRAME_STYLES
from .components.text import TEXT_STYLES
from .hud_context import HudContext, Label
from .passes import BloomPass, CameraPass, CompositePass, HudPass, Target
from .theme import Theme
from .vision.types import DetectionFrame

_MAX_BOXES = 16
_MAX_POINTS = 64


class _Track:
    __slots__ = ("anim", "det", "present")

    def __init__(self, anim: Animator, det, present: bool) -> None:
        self.anim = anim
        self.det = det
        self.present = present


class _CameraUploader:
    """Uploads camera frames to a GPU texture.

    ``double=True`` alternates between two textures so the GPU can keep sampling
    last frame's texture while this frame is written into the other — the same
    decoupling a PBO gives (true PBO mapping isn't exposed by ModernGL's API).
    Frames are written directly from the contiguous numpy buffer (no ``.tobytes``
    copy).
    """

    def __init__(self, ctx, double: bool = False) -> None:
        self.ctx = ctx
        self.double = double
        self.texs = [None, None]
        self.size = (0, 0)
        self.idx = 0

    def _alloc(self, w: int, h: int) -> None:
        for i in range(2 if self.double else 1):
            if self.texs[i] is not None:
                self.texs[i].release()
            t = self.ctx.texture((w, h), 3, dtype="f1", alignment=1)
            t.swizzle = "BGR"  # OpenCV BGR -> RGB for free
            t.filter = (9729, 9729)
            self.texs[i] = t
        self.size = (w, h)

    def upload(self, frame: np.ndarray):
        h, w = frame.shape[:2]
        frame = np.ascontiguousarray(frame)
        if self.size != (w, h):
            self._alloc(w, h)
        if self.double:
            self.idx ^= 1
        tex = self.texs[self.idx]
        tex.write(frame, alignment=1)
        return tex

    def release(self) -> None:
        for t in self.texs:
            if t is not None:
                t.release()


class Scene:
    def __init__(
        self,
        ctx,
        size: Tuple[int, int],
        theme: Optional[Theme] = None,
        detector=None,
        grade: float = 1.0,
        label_offset: float = 0.012,
        frame_style: str = "nefrex",
        text_style: str = "decipher",
        backgrounds: Iterable[str] = (),
        show_keypoints: bool = False,
        upload: str = "direct",
        bleeps=None,
    ) -> None:
        self.ctx = ctx
        self.size = (int(size[0]), int(size[1]))
        self.theme = theme or Theme()
        self.detector = detector
        self.grade = grade
        self.label_offset = label_offset
        self.bleeps = bleeps  # optional arcv.audio.Bleeps for lock-on / exit sounds

        self._vbo = geometry.fullscreen_buffer(ctx)
        self.camera_pass = CameraPass(ctx, self._vbo, self.theme)
        self.hud_pass = HudPass(ctx)
        self.bloom_pass = BloomPass(ctx, self._vbo, self.theme)
        self.composite_pass = CompositePass(ctx, self._vbo, self.theme)

        # ---- build the configurable HUD layer stack ----
        bg_components = [
            BACKGROUND_STYLES[name](ctx, self._vbo, self.theme)
            for name in backgrounds
            if name in BACKGROUND_STYLES
        ]
        frame_cls = FRAME_STYLES.get(frame_style, FRAME_STYLES["nefrex"])
        text_cls = TEXT_STYLES.get(text_style, TEXT_STYLES["decipher"])

        self.edge = EdgeTrace(ctx, self._vbo, self.theme)
        self.frame = frame_cls(ctx, self._vbo, self.theme)
        self.reticle = Reticle(ctx, self._vbo, self.theme)
        self.text = text_cls(ctx, self._vbo, self.theme)
        self.illuminator = Illuminator(ctx, self._vbo, self.theme)
        self.tracker = TrackerDots(ctx, self._vbo, self.theme) if show_keypoints else None

        self.layers: List = [*bg_components, self.edge, self.frame, self.reticle, self.text]
        if self.tracker is not None:
            self.layers.append(self.tracker)
        self.layers.append(self.illuminator)

        self.scene_target = Target(ctx, self.size, components=4, dtype="f2")
        self.hud_target = Target(ctx, self.size, components=4, dtype="f2")
        self.bloom_pass.resize(self.size)

        self._uploader = _CameraUploader(ctx, double=(upload == "double"))
        self._cam_tex = None
        self._edge_tex = None
        self._edge_size: Tuple[int, int] = (0, 0)

        self._detections: Optional[DetectionFrame] = None
        self._tracks: Dict[int, _Track] = {}
        self._primary_id: int = -1
        self._flow_mag = 0.0
        self._keypoints = np.zeros((_MAX_POINTS, 2), dtype="f4")
        self._keypoint_count = 0

        # global chrome (backgrounds) animator: enters once at startup
        self._bg_anim = Animator(duration_enter=1.0, duration_exit=0.6)
        self._bg_anim.enter()

        self._mouse = (0.5, 0.5)
        self._last_time: Optional[float] = None

    # -- input -------------------------------------------------------------
    def set_mouse(self, x_px: float, y_px: float) -> None:
        self._mouse = (x_px / self.size[0], 1.0 - y_px / self.size[1])

    def resize(self, width: int, height: int) -> None:
        self.size = (max(1, int(width)), max(1, int(height)))
        self.scene_target.resize(self.size)
        self.hud_target.resize(self.size)
        self.bloom_pass.resize(self.size)

    # -- per-frame submit --------------------------------------------------
    def submit(self, frame_bgr: np.ndarray, detections: Optional[DetectionFrame] = None) -> DetectionFrame:
        if detections is None:
            if self.detector is None:
                raise ValueError("No detections supplied and Scene has no detector")
            detections = self.detector.process(frame_bgr)
        self._detections = detections

        self._upload_camera(frame_bgr)
        self._upload_edges(detections.edges)
        self._track(detections)
        self._flow_mag = detections.flow_mag
        self._keypoints, self._keypoint_count = detections.packed_points(_MAX_POINTS)
        return detections

    def _upload_camera(self, frame: np.ndarray) -> None:
        self._cam_tex = self._uploader.upload(frame)

    def _upload_edges(self, edges: Optional[np.ndarray]) -> None:
        if edges is None:
            return
        h, w = edges.shape[:2]
        edges = np.ascontiguousarray(edges)
        if self._edge_tex is None or self._edge_size != (w, h):
            if self._edge_tex is not None:
                self._edge_tex.release()
            self._edge_tex = self.ctx.texture((w, h), 1, dtype="f1", alignment=1)
            self._edge_tex.filter = (9729, 9729)
            self._edge_size = (w, h)
        self._edge_tex.write(edges.tobytes(), alignment=1)

    def _track(self, detections: DetectionFrame) -> None:
        present_ids = set()
        for d in detections.boxes:
            present_ids.add(d.id)
            tr = self._tracks.get(d.id)
            if tr is None:
                anim = Animator(
                    duration_enter=self.theme.duration_enter,
                    duration_exit=self.theme.duration_exit,
                )
                self._tracks[d.id] = _Track(anim, d, True)
                anim.enter()
                if self.bleeps is not None:
                    self.bleeps.play("lock")  # target acquired
            else:
                tr.det = d
                tr.present = True
                tr.anim.enter()
        for tid, tr in self._tracks.items():
            if tid not in present_ids:
                if tr.present and self.bleeps is not None:
                    self.bleeps.play("exit")  # target lost (fire once on transition)
                tr.present = False
                tr.anim.exit()

        self._primary_id = -1
        if 0 <= detections.primary < len(detections.boxes):
            self._primary_id = detections.boxes[detections.primary].id

    # -- render ------------------------------------------------------------
    def render(self, time: float, target=None) -> None:
        dt = 0.0 if self._last_time is None else max(0.0, time - self._last_time)
        self._last_time = time
        self._advance(dt)

        hud = self._build_hud_context(time)

        if self._cam_tex is not None:
            self.camera_pass.render(self.scene_target.fbo, self._cam_tex, self.grade)
        else:
            self.scene_target.fbo.use()
            self.scene_target.fbo.clear(*self.theme.base[:3], 1.0)

        self.hud_pass.render(self.hud_target.fbo, self.layers, hud)
        bloom_tex = self.bloom_pass.process(self.hud_target.tex, self.theme.bloom_iterations)

        out = target if target is not None else self.ctx.screen
        self.composite_pass.render(
            out, self.scene_target.tex, self.hud_target.tex, bloom_tex, time
        )

    def _advance(self, dt: float) -> None:
        self._bg_anim.update(dt)
        dead: List[int] = []
        for tid, tr in self._tracks.items():
            tr.anim.update(dt)
            if tr.anim.state == EXITED and not tr.present:
                dead.append(tid)
        for tid in dead:
            del self._tracks[tid]

    def _build_hud_context(self, time: float) -> HudContext:
        boxes = np.zeros((_MAX_BOXES, 4), dtype="f4")
        meta = np.zeros((_MAX_BOXES, 4), dtype="f4")
        labels: List[Label] = []
        primary_center = (0.5, 0.5)
        primary_half = (0.1, 0.1)
        primary_progress = 0.0

        i = 0
        for tid, tr in self._tracks.items():
            if i >= _MAX_BOXES:
                break
            prog = tr.anim.progress
            if prog <= 0.001:
                continue
            d = tr.det
            is_primary = tid == self._primary_id
            boxes[i] = (d.cx, d.cy, d.hw, d.hh)
            meta[i] = (prog, d.score, 0.0 if d.kind == "face" else 1.0, 1.0 if is_primary else 0.0)
            labels.append(
                Label(
                    text=d.label or d.kind.upper(),
                    x=d.cx - d.hw,
                    y=d.cy + d.hh + self.label_offset,
                    progress=prog,
                )
            )
            if is_primary:
                primary_center = (d.cx, d.cy)
                primary_half = (d.hw, d.hh)
                primary_progress = prog
            i += 1

        return HudContext(
            resolution=self.size,
            time=time,
            boxes=boxes,
            meta=meta,
            count=i,
            mouse=self._mouse,
            edge_tex=self._edge_tex,
            primary_center=primary_center,
            primary_half=primary_half,
            primary_progress=primary_progress,
            edge_progress=1.0,
            labels=labels,
            bg_progress=self._bg_anim.progress,
            flow_mag=self._flow_mag,
            keypoints=self._keypoints,
            keypoint_count=self._keypoint_count,
        )

    def read_pixels(self, target=None) -> np.ndarray:
        """Read the last composited frame from ``target`` (or the screen) as an
        RGB uint8 numpy array, flipped to top-left origin for OpenCV/saving.
        """
        fbo = target if target is not None else self.ctx.screen
        w, h = fbo.size
        data = fbo.read(components=3, dtype="f1")
        arr = np.frombuffer(data, dtype=np.uint8).reshape(h, w, 3)
        return np.flipud(arr)  # GL bottom-left -> image top-left
