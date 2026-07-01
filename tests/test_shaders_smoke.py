"""Headless GPU smoke test: compile every shader and run the full 4-pass
pipeline once against a synthetic frame + detections. No camera, no window."""

import numpy as np
import pytest

moderngl = pytest.importorskip("moderngl")

from arcv.scene import Scene
from arcv.theme import Theme, make_theme
from arcv.vision.types import Detection, DetectionFrame
from arcv.passes.base import Target


@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_standalone_context(require=330)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"No GL context available: {e}")
    yield c
    c.release()


def _synthetic_frame(w, h):
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    xx = np.linspace(0, 200, w, dtype=np.uint8)
    frame[:, :, 0] = xx[None, :]            # B gradient
    frame[:, :, 2] = np.linspace(0, 160, h, dtype=np.uint8)[:, None]  # R gradient
    frame[h // 3 : 2 * h // 3, w // 3 : 2 * w // 3] = (180, 180, 180)
    return frame


def _detections(w, h):
    edges = np.zeros((h, w), dtype=np.uint8)
    edges[::8, :] = 255
    edges[:, ::8] = 255
    boxes = [
        Detection(0.5, 0.55, 0.12, 0.18, score=0.98, label="TGT-00", kind="face", id=0),
        Detection(0.78, 0.30, 0.08, 0.10, score=0.80, label="OBJ-01", kind="object", id=1),
    ]
    return DetectionFrame(boxes=boxes, edges=edges, frame_size=(w, h), primary=0)


def test_full_pipeline_renders(ctx, tmp_path):
    w, h = 640, 360
    scene = Scene(ctx, (w, h), theme=Theme())
    out = Target(ctx, (w, h), components=4, dtype="f1")

    frame = _synthetic_frame(w, h)
    dets = _detections(w, h)

    # advance a few frames so the enter animation plays out
    for t in (0.0, 0.15, 0.3, 0.5):
        scene.submit(frame, dets)
        scene.set_mouse(w * 0.5, h * 0.5)
        scene.render(t, target=out.fbo)

    assert ctx.error == "GL_NO_ERROR"

    img = scene.read_pixels(out.fbo)  # (h, w, 3) uint8
    assert img.shape == (h, w, 3)
    assert img.max() > 0  # something was drawn

    # cyan HUD should be present: pixels where green & blue dominate red
    g = img[:, :, 1].astype(int)
    b = img[:, :, 2].astype(int)
    r = img[:, :, 0].astype(int)
    cyan = (g > 120) & (b > 120) & (g > r + 30)
    assert cyan.sum() > 50, "expected visible cyan HUD strokes"


def test_resize_reallocates(ctx):
    scene = Scene(ctx, (320, 240), theme=Theme())
    scene.resize(800, 600)
    assert scene.size == (800, 600)
    assert scene.scene_target.size == (800, 600)


def _detections_full(w, h):
    edges = np.zeros((h, w), dtype=np.uint8)
    edges[::8, :] = 255
    boxes = [
        Detection(0.4, 0.55, 0.12, 0.18, score=0.98, label="TGT-00", kind="face", id=0),
        Detection(0.75, 0.35, 0.08, 0.10, score=0.80, label="OBJ-01", kind="object", id=1),
    ]
    kps = [(0.2 + 0.05 * i, 0.3 + 0.04 * i) for i in range(20)]
    return DetectionFrame(
        boxes=boxes, edges=edges, frame_size=(w, h), primary=0,
        flow_mag=0.5, keypoints=kps,
    )


@pytest.mark.parametrize(
    "frame_style", ["nefrex", "corners", "lines", "octagon", "underline", "kranox"]
)
def test_every_frame_style_compiles(ctx, frame_style):
    w, h = 480, 270
    scene = Scene(ctx, (w, h), theme=Theme(), frame_style=frame_style)
    out = Target(ctx, (w, h), components=4, dtype="f1")
    frame = _synthetic_frame(w, h)
    dets = _detections_full(w, h)
    for t in (0.0, 0.3, 0.6):
        scene.submit(frame, dets)
        scene.render(t, target=out.fbo)
    assert ctx.error == "GL_NO_ERROR"
    assert scene.read_pixels(out.fbo).max() > 0


def test_overlay_kit_renders(ctx):
    from arcv.overlay import Overlay
    from arcv.theme import make_theme

    w, h = 480, 300
    ov = Overlay(ctx, (w, h), theme=make_theme("green"))
    out = Target(ctx, (w, h), components=4, dtype="f1")
    G = (0.4, 0.97, 0.66, 1.0)
    ov.begin()
    ov.vector.rounded_rect(20, 20, 200, 120, 10, G, 2.0)
    ov.vector.rounded_rect_fill(20, 20, 200, 120, 10, (0.4, 0.97, 0.66, 0.06))
    ov.vector.ring(320, 150, 50, G, 2.0)
    ov.vector.line((260, 150), (380, 150), G, 1.5)
    ov.vector.disc(100, 250, 6, (1.0, 0.27, 0.27, 1.0))
    ov.vector.triangle_outline((400, 40), (380, 90), (420, 90), G, 1.5)
    ov.text.text("SYSTEM ONLINE", 36, 36, 16, G)
    ov.text.text("THREAT // MEDIUM", 36, 70, 12, (0.88, 1.0, 0.94, 1.0))
    ov.render(0.0, target=out.fbo)
    assert ctx.error == "GL_NO_ERROR"
    img = ov.read_pixels(out.fbo)
    assert img.max() > 0
    # green-dominant HUD
    assert int(img[:, :, 1].sum()) > int(img[:, :, 2].sum())


def test_double_buffered_upload_and_themed(ctx):
    w, h = 320, 180
    scene = Scene(ctx, (w, h), theme=make_theme("amber"), upload="double")
    out = Target(ctx, (w, h), components=4, dtype="f1")
    frame = _synthetic_frame(w, h)
    dets = _detections_full(w, h)
    for t in (0.0, 0.2, 0.4):
        scene.submit(frame, dets)
        scene.render(t, target=out.fbo)
    assert ctx.error == "GL_NO_ERROR"
    img = scene.read_pixels(out.fbo)
    assert img.max() > 0
    # amber theme -> warm strokes: red channel total exceeds blue
    assert int(img[:, :, 0].sum()) > int(img[:, :, 2].sum())


def test_all_backgrounds_text_and_keypoints_compile(ctx):
    w, h = 480, 270
    scene = Scene(
        ctx, (w, h), theme=Theme(),
        text_style="typeon",
        backgrounds=("dots", "gridlines", "movinglines", "puffs"),
        show_keypoints=True,
    )
    out = Target(ctx, (w, h), components=4, dtype="f1")
    frame = _synthetic_frame(w, h)
    dets = _detections_full(w, h)
    for t in (0.0, 0.3, 0.6, 1.0):
        scene.submit(frame, dets)
        scene.render(t, target=out.fbo)
    assert ctx.error == "GL_NO_ERROR"
    img = scene.read_pixels(out.fbo)
    assert img.max() > 0
