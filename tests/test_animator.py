import math

from arcv import animator
from arcv.animator import Animator, EXITED, ENTERING, ENTERED, EXITING


def test_default_constants():
    assert animator.DEFAULT_DURATION_ENTER == 0.4
    assert animator.DEFAULT_DURATION_EXIT == 0.4
    assert animator.DEFAULT_STAGGER == 0.04


def test_single_node_enter_exit_cycle():
    a = Animator(duration_enter=0.4, duration_exit=0.4)
    assert a.state == EXITED and a.progress == 0.0

    a.enter()
    assert a.state == ENTERING
    a.update(0.2)
    assert a.state == ENTERING
    assert math.isclose(a.progress, 0.5, abs_tol=1e-6)
    a.update(0.2)
    assert a.state == ENTERED
    assert math.isclose(a.progress, 1.0, abs_tol=1e-6)

    a.exit()
    assert a.state == EXITING
    a.update(0.2)
    assert math.isclose(a.progress, 0.5, abs_tol=1e-6)
    a.update(0.2)
    assert a.state == EXITED
    assert math.isclose(a.progress, 0.0, abs_tol=1e-6)


def test_delay_is_consumed_before_progress():
    a = Animator(duration_enter=0.4, delay=0.1)
    a.enter()
    a.update(0.1)  # all consumed by delay
    assert math.isclose(a.progress, 0.0, abs_tol=1e-6)
    a.update(0.2)
    assert math.isclose(a.progress, 0.5, abs_tol=1e-6)


def test_stagger_offsets_children():
    parent = Animator(manager="stagger", stagger=0.1)
    c0 = parent.add(Animator(duration_enter=0.2))
    c1 = parent.add(Animator(duration_enter=0.2))

    parent.enter()
    parent.update(0.1)
    # child 0: no start delay -> half done; child 1: delayed -> still 0
    assert math.isclose(c0.progress, 0.5, abs_tol=1e-6)
    assert math.isclose(c1.progress, 0.0, abs_tol=1e-6)

    parent.update(0.1)
    assert math.isclose(c0.progress, 1.0, abs_tol=1e-6)
    assert math.isclose(c1.progress, 0.5, abs_tol=1e-6)


def test_parent_exit_cascades_to_children():
    parent = Animator(duration_enter=0.2, duration_exit=0.2)
    child = parent.add(Animator(duration_enter=0.2, duration_exit=0.2))
    parent.enter()
    parent.update(0.2)
    assert parent.state == ENTERED and child.state == ENTERED

    parent.exit()
    parent.update(0.2)
    assert parent.state == EXITED
    assert child.state == EXITED
    assert child.progress == 0.0
