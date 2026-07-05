"""Phase 6 — Player runner + value/playback completeness (pure Python)."""

import pytest

from arcv.overlay import anim
from arcv.overlay.anim import Animation, Timeline, Timer, Player


# -- Player: wall-clock -> t -------------------------------------------------
def test_player_advances_by_dt():
    a = Animation({"x": (0.0, 100.0)}, duration=1.0)
    p = Player(a)
    p.update(dt=0.5)
    assert p.time == pytest.approx(0.5)
    assert p.target.at(p.time)["x"] == pytest.approx(50.0)


def test_player_from_absolute_now():
    a = Animation({"x": (0.0, 10.0)}, duration=1.0)
    p = Player(a)
    p.update(now=100.0)          # first sample establishes baseline, dt=0
    assert p.time == pytest.approx(0.0)
    p.update(now=100.5)
    assert p.time == pytest.approx(0.5)
    p.update(now=101.0)
    assert p.time == pytest.approx(1.0)


def test_player_speed():
    a = Animation({"x": (0.0, 10.0)}, duration=1.0)
    p = Player(a, speed=2.0)
    p.update(dt=0.25)
    assert p.time == pytest.approx(0.5)


def test_player_pause_holds():
    p = Player(Timer(1.0))
    p.update(dt=0.3)
    p.pause()
    p.update(dt=0.5)
    assert p.time == pytest.approx(0.3)
    p.play()
    p.update(dt=0.2)
    assert p.time == pytest.approx(0.5)


def test_player_reversed_playback():
    a = Animation({"x": (0.0, 100.0)}, duration=1.0)
    p = Player(a, reversed=True, time=1.0)
    assert p.target.at(p.time)["x"] == pytest.approx(100.0)
    p.update(dt=0.5)
    assert p.time == pytest.approx(0.5)
    p.update(dt=1.0)             # clamps at 0
    assert p.time == pytest.approx(0.0)


def test_player_seek_and_restart():
    a = Animation({"x": (0.0, 10.0)}, duration=1.0)
    p = Player(a)
    p.seek(0.75)
    assert p.time == pytest.approx(0.75)
    p.restart()
    assert p.time == pytest.approx(0.0)


def test_player_progress_and_completed():
    tm = Timer(2.0)
    p = Player(tm)
    p.update(dt=1.0)
    assert p.progress == pytest.approx(0.5)
    assert not p.completed
    p.update(dt=1.5)
    assert p.completed


def test_player_fires_callbacks_once():
    events = []
    tl = Timeline(on_begin=lambda s: events.append("begin"),
                  on_complete=lambda s: events.append("complete"))
    tl.add({"x": (0.0, 1.0)}, {"duration": 1.0}, position=0.0)
    p = Player(tl)
    for _ in range(20):
        p.update(dt=0.1)         # forward past the end
    assert events.count("begin") == 1
    assert events.count("complete") == 1


# -- value completeness end-to-end through the Timeline ----------------------
def test_relative_value_through_timeline():
    tl = Timeline()
    tl.add({"x": "+=50"}, {"duration": 1.0, "base": {"x": 10.0}}, position=0.0)
    assert tl.at(0.0)["a0"]["x"] == pytest.approx(10.0)
    assert tl.at(1.0)["a0"]["x"] == pytest.approx(60.0)


def test_function_value_through_timeline():
    tl = Timeline()
    tl.add({"x": (0.0, lambda i, n: 99.0)}, {"duration": 1.0}, position=0.0)
    assert tl.at(1.0)["a0"]["x"] == pytest.approx(99.0)


def test_enddelay_and_loopcount_playback():
    # 2 loops, 0.5s hold at the end of each; total = 2*(1+0.5) = 3.0
    tm = Timer(1.0, end_delay=0.5, loop=2)
    assert tm.total_duration == pytest.approx(3.0)
    assert tm.at(1.25) == pytest.approx(1.0)     # holding in end_delay
    assert not tm.is_complete(1.25)
    assert tm.is_complete(3.0)


def test_reversed_and_alternate_are_pure_functions():
    tl = Timeline(loop=True, alternate=True)
    tl.add({"x": (0.0, 10.0)}, {"duration": 1.0}, position=0.0)
    # sampling the same t twice always agrees (no hidden playhead)
    assert tl.values_at(2.3)["x"] == tl.values_at(2.3)["x"]
