"""Animator — a Python port of the Arwes animator state machine.

Every visual element is driven by an animator node's ``state`` and ``progress``.

States form a finite machine::

    exited -> entering -> entered -> exiting -> exited

``progress`` moves 0 -> 1 while entering and 1 -> 0 while exiting, over the
node's ``duration_enter`` / ``duration_exit`` (defaults 0.4 s, matching Arwes
``ANIMATOR_DEFAULT_DURATION``). Parents sequence their children with a manager
(``parallel``, ``stagger``, ``staggerReverse``, ``sequence``). A parent forced
to ``exited`` forces its children to ``exited``.

This module is pure logic — no GPU, no I/O — so it is fully unit-testable.
"""

from __future__ import annotations

from typing import List

from . import easing

EXITED = "exited"
ENTERING = "entering"
ENTERED = "entered"
EXITING = "exiting"

# Arwes ANIMATOR_DEFAULT_DURATION (seconds).
DEFAULT_DURATION_ENTER = 0.4
DEFAULT_DURATION_EXIT = 0.4
DEFAULT_DELAY = 0.0
DEFAULT_STAGGER = 0.04

MANAGERS = ("parallel", "stagger", "staggerReverse", "sequence", "sequenceReverse")


class Animator:
    def __init__(
        self,
        duration_enter: float = DEFAULT_DURATION_ENTER,
        duration_exit: float = DEFAULT_DURATION_EXIT,
        delay: float = DEFAULT_DELAY,
        stagger: float = DEFAULT_STAGGER,
        manager: str = "parallel",
        easing_fn=easing.linear,
        initial_state: str = EXITED,
    ) -> None:
        self.duration_enter = float(duration_enter)
        self.duration_exit = float(duration_exit)
        self.delay = float(delay)
        self.stagger = float(stagger)
        self.manager = manager
        self.easing_fn = easing_fn

        self.state = initial_state
        # ``_raw`` is the un-eased progress in [0, 1]; ``progress`` is eased.
        self._raw = 1.0 if initial_state in (ENTERED,) else 0.0
        self.progress = self.easing_fn(self._raw)

        # Extra start delay imposed by a parent's manager (for staggering).
        self._start_delay = 0.0
        self._delay_left = 0.0

        self.children: List["Animator"] = []

    # -- tree --------------------------------------------------------------
    def add(self, child: "Animator") -> "Animator":
        self.children.append(child)
        return child

    # -- transitions -------------------------------------------------------
    def enter(self) -> None:
        if self.state in (ENTERED, ENTERING):
            return
        self.state = ENTERING
        self._delay_left = self.delay + self._start_delay
        self._schedule_children(entering=True)

    def exit(self) -> None:
        if self.state in (EXITED, EXITING):
            return
        self.state = EXITING
        self._delay_left = 0.0
        self._schedule_children(entering=False)

    def _schedule_children(self, entering: bool) -> None:
        n = len(self.children)
        for i, child in enumerate(self.children):
            child._start_delay = self._child_delay(i, n, entering)
            if entering:
                child.enter()
            else:
                child.exit()

    def _child_delay(self, i: int, n: int, entering: bool) -> float:
        m = self.manager
        if m == "stagger":
            return i * self.stagger
        if m == "staggerReverse":
            return (n - 1 - i) * self.stagger
        if m == "sequence":
            return i * (self.delay + self.duration_enter)
        if m == "sequenceReverse":
            return (n - 1 - i) * (self.delay + self.duration_enter)
        return 0.0  # parallel

    # -- update ------------------------------------------------------------
    def update(self, dt: float) -> None:
        if self.state == ENTERING:
            if self._delay_left > 0.0:
                consume = min(self._delay_left, dt)
                self._delay_left -= consume
                dt -= consume
            if dt > 0.0:
                step = dt / self.duration_enter if self.duration_enter > 0 else 1.0
                self._raw = min(1.0, self._raw + step)
                if self._raw >= 1.0:
                    self.state = ENTERED
        elif self.state == EXITING:
            step = dt / self.duration_exit if self.duration_exit > 0 else 1.0
            self._raw = max(0.0, self._raw - step)
            if self._raw <= 0.0:
                self.state = EXITED

        self.progress = self.easing_fn(self._raw)

        for child in self.children:
            child.update(dt if self.state != EXITED else 0.0)
            if self.state == EXITED:
                child.force_exited()

    def force_exited(self) -> None:
        self.state = EXITED
        self._raw = 0.0
        self.progress = self.easing_fn(0.0)
        for child in self.children:
            child.force_exited()

    @property
    def is_settled(self) -> bool:
        return self.state in (EXITED, ENTERED)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"Animator(state={self.state!r}, progress={self.progress:.3f})"
