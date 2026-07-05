"""Phase 2 — Timer / Animation / Timeline core engine (pure Python, no GPU).

Every assertion leans on determinism: ``.at(t)`` must be order-independent so
scrubbing, stills and MP4 export agree.
"""

import math

import pytest

from arcv.overlay import anim
from arcv.overlay.anim import Timer, Animation, Timeline


# ===========================================================================
#  Timer
# ===========================================================================
def test_timer_linear_progress_and_delay():
    tm = Timer(2.0, delay=1.0)
    assert tm.at(0.0) == 0.0            # in delay
    assert tm.at(0.5) == 0.0
    assert abs(tm.at(2.0) - 0.5) < 1e-9  # 1s into a 2s duration
    assert abs(tm.at(3.0) - 1.0) < 1e-9
    assert tm.at(10.0) == 1.0           # clamped after completion


def test_timer_completion_flag():
    tm = Timer(1.0)
    assert not tm.is_complete(0.5)
    assert tm.is_complete(1.0)
    assert tm.is_complete(5.0)


def test_timer_loop_iterations():
    tm = Timer(1.0, loop=3)
    assert tm.state_at(0.5).iteration == 0
    assert tm.state_at(1.5).iteration == 1
    assert tm.state_at(2.5).iteration == 2
    assert tm.state_at(2.5).completed is False
    assert tm.state_at(3.0).completed is True   # 3 iterations done
    # infinite never completes
    inf = Timer(1.0, loop=True)
    assert inf.state_at(100.0).completed is False
    assert inf.state_at(100.25).iteration == 100


def test_timer_alternate_yoyo():
    tm = Timer(1.0, loop=True, alternate=True)
    # iteration 0 goes forward, iteration 1 comes back
    assert abs(tm.at(0.25) - 0.25) < 1e-9
    assert abs(tm.at(1.25) - 0.75) < 1e-9   # reversed second iteration
    assert abs(tm.at(2.25) - 0.25) < 1e-9   # forward again


def test_timer_reversed():
    tm = Timer(2.0, reversed=True)
    assert abs(tm.at(0.0) - 1.0) < 1e-9
    assert abs(tm.at(2.0) - 0.0) < 1e-9


def test_timer_end_delay_holds():
    tm = Timer(1.0, end_delay=1.0, loop=2)
    assert abs(tm.at(1.0) - 1.0) < 1e-9     # reached end
    assert abs(tm.at(1.5) - 1.0) < 1e-9     # holding during end_delay
    assert tm.state_at(1.5).iteration == 0
    assert tm.state_at(2.0).iteration == 1  # next iteration starts after hold


def test_timer_determinism_order_independent():
    tm = Timer(3.0, loop=True, alternate=True)
    samples = [i * 0.137 for i in range(50)]
    forward = {t: tm.at(t) for t in samples}
    backward = {t: tm.at(t) for t in reversed(samples)}
    for t in samples:
        assert forward[t] == backward[t]


def test_timer_callbacks_once():
    events = []
    tm = Timer(1.0, loop=2,
               on_begin=lambda s: events.append("begin"),
               on_complete=lambda s: events.append("complete"),
               on_loop=lambda s, i: events.append(f"loop{i}"))
    for i in range(0, 25):
        tm.tick(i * 0.1)   # 0.0 .. 2.4 forward
    assert events.count("begin") == 1
    assert events.count("complete") == 1
    assert events.count("loop1") == 1
    # order: begin before loop before complete
    assert events.index("begin") < events.index("loop1") < events.index("complete")


# ===========================================================================
#  Animation
# ===========================================================================
def test_animation_basic_tween():
    a = Animation({"x": (0.0, 100.0)}, duration=1.0)
    assert a.at(0.0)["x"] == 0.0
    assert abs(a.at(0.5)["x"] - 50.0) < 1e-9
    assert a.at(1.0)["x"] == 100.0


def test_animation_scalar_to_with_base():
    a = Animation({"x": 100.0}, duration=1.0, base={"x": 20.0})
    assert abs(a.at(0.0)["x"] - 20.0) < 1e-9
    assert abs(a.at(1.0)["x"] - 100.0) < 1e-9


def test_animation_easing_applied():
    a = Animation({"x": (0.0, 1.0)}, duration=1.0, ease="inQuad")
    assert abs(a.at(0.5)["x"] - 0.25) < 1e-6   # inQuad(0.5) == 0.25


def test_animation_relative_values():
    a = Animation({"x": "+=50"}, duration=1.0, base={"x": 10.0})
    assert abs(a.at(0.0)["x"] - 10.0) < 1e-9
    assert abs(a.at(1.0)["x"] - 60.0) < 1e-9
    m = Animation({"x": "*=3"}, duration=1.0, base={"x": 4.0})
    assert abs(m.at(1.0)["x"] - 12.0) < 1e-9


def test_animation_function_values_per_index():
    made = [Animation({"x": (0.0, lambda i, n: 10.0 * i)}, duration=1.0, index=i, total=4)
            for i in range(4)]
    ends = [a.at(1.0)["x"] for a in made]
    assert ends == [0.0, 10.0, 20.0, 30.0]


def test_animation_keyframes_chain():
    a = Animation({"x": [{"to": 100.0, "duration": 1.0},
                         {"to": 0.0, "duration": 1.0}]}, base={"x": 0.0})
    assert abs(a.duration - 2.0) < 1e-9
    assert abs(a.at(1.0)["x"] - 100.0) < 1e-9    # end of first keyframe
    assert abs(a.at(2.0)["x"] - 0.0) < 1e-9      # end of second
    assert abs(a.at(1.5)["x"] - 50.0) < 1e-9     # midway back


def test_animation_color_interpolation():
    a = Animation({"c": [(0.0, 0.0, 0.0, 1.0), (1.0, 1.0, 1.0, 1.0)]}, duration=1.0)
    mid = a.at(0.5)["c"]
    assert all(abs(ch - 0.5) < 1e-9 for ch in mid[:3])
    assert abs(mid[3] - 1.0) < 1e-9


def test_animation_hex_color_interpolation():
    a = Animation({"c": ("#000000", "#ffffff")}, duration=1.0)
    mid = a.at(0.5)["c"]
    assert all(abs(ch - 0.5) < 1e-2 for ch in mid[:3])


def test_animation_per_property_delay():
    a = Animation({"x": {"to": 100.0, "delay": 1.0, "duration": 1.0},
                   "y": {"to": 100.0, "duration": 1.0}})
    # at t=1.0: y done, x just starting
    assert abs(a.at(1.0)["y"] - 100.0) < 1e-9
    assert abs(a.at(1.0)["x"] - 0.0) < 1e-9
    assert abs(a.at(2.0)["x"] - 100.0) < 1e-9


def test_animation_determinism():
    a = Animation({"x": (0.0, 100.0), "y": (10.0, -10.0)}, duration=2.0, ease="inOutCubic")
    ts = [i * 0.05 for i in range(60)]
    fwd = {t: a.at(t)["x"] for t in ts}
    bwd = {t: a.at(t)["x"] for t in reversed(ts)}
    assert fwd == bwd


# ===========================================================================
#  Timeline
# ===========================================================================
def test_timeline_sequential_append():
    tl = Timeline()
    tl.add({"x": (0.0, 10.0)}, {"duration": 1.0})
    tl.add({"x": (0.0, 20.0)}, {"duration": 1.0})   # appended after first
    assert abs(tl.duration - 2.0) < 1e-9
    # first child active in [0,1], second in [1,2]
    assert abs(tl.at(0.5)["a0"]["x"] - 5.0) < 1e-9
    assert abs(tl.at(1.5)["a1"]["x"] - 10.0) < 1e-9


def test_timeline_absolute_position():
    tl = Timeline()
    tl.add({"x": (0.0, 10.0)}, {"duration": 1.0}, position=0.0)
    tl.add({"x": (0.0, 10.0)}, {"duration": 1.0}, position=0.5)  # overlaps
    assert abs(tl.duration - 1.5) < 1e-9
    got = tl.at(0.75)
    assert abs(got["a0"]["x"] - 7.5) < 1e-9
    assert abs(got["a1"]["x"] - 2.5) < 1e-9


def test_timeline_relative_offsets():
    tl = Timeline()
    tl.add({"x": (0.0, 1.0)}, {"duration": 1.0})
    tl.add({"x": (0.0, 1.0)}, {"duration": 1.0}, position="-=0.5")  # start at 0.5
    assert abs(tl.children[1].start - 0.5) < 1e-9
    tl.add({"x": (0.0, 1.0)}, {"duration": 1.0}, position="+=0.25")  # dur was 1.5 -> 1.75
    assert abs(tl.children[2].start - 1.75) < 1e-9


def test_timeline_labels():
    tl = Timeline()
    tl.label("boot", 0.5)
    tl.add({"x": (0.0, 10.0)}, {"duration": 1.0}, position="boot")
    assert abs(tl.children[0].start - 0.5) < 1e-9
    tl.add({"x": (0.0, 10.0)}, {"duration": 1.0}, position="boot+=0.25")
    assert abs(tl.children[1].start - 0.75) < 1e-9


def test_timeline_prev_start_end_anchors():
    tl = Timeline()
    tl.add({"x": (0.0, 1.0)}, {"duration": 2.0})
    tl.add({"y": (0.0, 1.0)}, {"duration": 1.0}, position="<")   # previous start
    assert abs(tl.children[1].start - 0.0) < 1e-9
    tl.add({"z": (0.0, 1.0)}, {"duration": 1.0}, position=">")   # previous end
    assert abs(tl.children[2].start - 1.0) < 1e-9


def test_timeline_loop_and_determinism():
    tl = Timeline(loop=True, alternate=True)
    tl.add({"x": (0.0, 10.0)}, {"duration": 1.0})
    tl.add({"x": (0.0, 20.0)}, {"duration": 1.0})
    ts = [i * 0.11 for i in range(80)]
    fwd = {t: tl.values_at(t)["x"] for t in ts}
    bwd = {t: tl.values_at(t)["x"] for t in reversed(ts)}
    assert fwd == bwd


def test_timeline_at_structure():
    tl = Timeline()
    tl.add({"x": (0.0, 10.0), "y": (0.0, 5.0)}, {"duration": 1.0}, position=0.0)
    snap = tl.at(0.5)
    assert set(snap.keys()) == {"a0"}
    assert set(snap["a0"].keys()) == {"x", "y"}


def test_timeline_custom_id():
    tl = Timeline()
    tl.add({"x": (0.0, 10.0)}, {"duration": 1.0, "id": "hero"}, position=0.0)
    assert "hero" in tl.at(0.5)
    assert abs(tl.child_at(0.5, "hero")["x"] - 5.0) < 1e-9


# ===========================================================================
#  colors helper
# ===========================================================================
def test_parse_color_formats():
    assert anim.parse_color("#ff0000") == (1.0, 0.0, 0.0, 1.0)
    assert anim.parse_color("#f00") == (1.0, 0.0, 0.0, 1.0)
    r, g, b, a = anim.parse_color("#00ff0080")
    assert abs(g - 1.0) < 1e-9 and abs(a - 128 / 255) < 1e-9
    assert anim.parse_color((255, 128, 0)) == pytest.approx((1.0, 128 / 255, 0.0, 1.0))
    assert anim.parse_color((1.0, 0.0, 0.0, 1.0)) == (1.0, 0.0, 0.0, 1.0)
    r, g, b, a = anim.parse_color("hsl(120,100%,50%)")
    assert abs(r) < 1e-6 and abs(g - 1.0) < 1e-6 and abs(b) < 1e-6


def test_sequencer_still_works():
    # regression: original API untouched
    q = anim.Sequencer(0.7)
    assert abs(q.at(0.5, 0.4, anim.linear) - 0.5) < 1e-6
