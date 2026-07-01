import cv2
import numpy as np
import pytest

from arcv.vision.types import Detection, DetectionFrame
from arcv.vision.pipeline import DetectorPipeline
from arcv.vision.detectors import default_yunet_path


def test_from_pixel_rect_normalizes_and_flips():
    # rect at top-left quarter of a 200x200 frame
    d = Detection.from_pixel_rect(0, 0, 100, 100, 200, 200)
    assert abs(d.cx - 0.25) < 1e-6
    assert abs(d.cy - 0.75) < 1e-6  # y flipped to y-up
    assert abs(d.hw - 0.25) < 1e-6
    assert abs(d.hh - 0.25) < 1e-6


def test_packed_shapes_and_count():
    f = DetectionFrame(
        boxes=[Detection(0.5, 0.5, 0.1, 0.1, label="a")], frame_size=(640, 480),
        primary=0,
    )
    boxes, meta, count = f.packed(max_boxes=4)
    assert boxes.shape == (4, 4)
    assert meta.shape == (4, 4)
    assert count == 1
    assert tuple(boxes[0]) == (0.5, 0.5, 0.1, 0.1)
    assert meta[0][3] == 1.0  # primary flag


def test_pipeline_detects_object_and_flips_y():
    img = np.zeros((240, 320, 3), dtype=np.uint8)
    # white filled rectangle near the TOP of the image
    cv2.rectangle(img, (120, 20), (220, 120), (255, 255, 255), -1)

    pipe = DetectorPipeline(
        enable_faces=False, enable_edges=True, enable_contours=True
    )
    frame = pipe.process(img)

    assert frame.frame_size == (320, 240)
    assert frame.edges is not None
    assert len(frame.boxes) >= 1
    assert frame.primary >= 0
    # an object near the top of the image -> high cy in y-up UV space
    obj = frame.boxes[0]
    assert obj.cy > 0.5
    assert obj.id >= 0
    assert obj.label  # auto-labelled


def test_pipeline_assigns_stable_ids_across_frames():
    img = np.zeros((240, 320, 3), dtype=np.uint8)
    cv2.rectangle(img, (120, 60), (220, 160), (255, 255, 255), -1)
    pipe = DetectorPipeline(enable_faces=False)
    f1 = pipe.process(img)
    f2 = pipe.process(img)  # same scene -> same id
    assert f1.boxes[0].id == f2.boxes[0].id


def test_packed_points_shapes_and_uv():
    f = DetectionFrame(keypoints=[(0.1, 0.2), (0.3, 0.4), (0.5, 0.6)])
    pts, count = f.packed_points(max_points=8)
    assert pts.shape == (8, 2)
    assert count == 3
    assert tuple(pts[0]) == (0.1, 0.2)


def test_yunet_missing_model_falls_back_to_haar():
    pipe = DetectorPipeline(
        face_backend="yunet", yunet_model="___does_not_exist___.onnx",
        enable_edges=False, enable_contours=False,
    )
    assert pipe.faces is not None
    assert pipe._face_is_yunet is False


def test_yunet_runs_when_model_present():
    path = default_yunet_path()
    if not path:
        pytest.skip("YuNet model not available")
    pipe = DetectorPipeline(face_backend="yunet", enable_edges=False, enable_contours=False)
    assert pipe._face_is_yunet
    img = np.zeros((240, 320, 3), dtype=np.uint8)
    f = pipe.process(img)  # no faces in a black image, just must not crash
    assert f.frame_size == (320, 240)


def test_enumerate_cameras_returns_list():
    from arcv.capture import enumerate_cameras

    res = enumerate_cameras(max_index=1)
    assert isinstance(res, list)


def test_optical_flow_and_orb_run():
    img1 = np.zeros((120, 160, 3), dtype=np.uint8)
    cv2.rectangle(img1, (40, 40), (90, 90), (255, 255, 255), -1)
    img2 = np.zeros((120, 160, 3), dtype=np.uint8)
    cv2.rectangle(img2, (55, 50), (105, 100), (255, 255, 255), -1)  # moved

    pipe = DetectorPipeline(
        enable_faces=False, enable_contours=False, enable_edges=False,
        enable_flow=True, enable_orb=True,
    )
    f1 = pipe.process(img1)
    assert f1.flow_mag == 0.0  # first frame: no previous -> zero motion
    f2 = pipe.process(img2)
    assert 0.0 <= f2.flow_mag <= 1.0
    # ORB finds corner-ish features on the rectangle; keypoints normalized to UV
    assert all(0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 for (x, y) in f2.keypoints)
