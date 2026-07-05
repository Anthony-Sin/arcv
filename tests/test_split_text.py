"""Phase 5 — split text units + staggered entrance transform (pure Python)."""

import pytest

from arcv.overlay import anim


# -- char_units --------------------------------------------------------------
def test_char_units_chars():
    units, count = anim.char_units("abc", "chars")
    assert units == [0, 1, 2]
    assert count == 3


def test_char_units_words():
    units, count = anim.char_units("ab cd", "words")
    assert units == [0, 0, 0, 1, 1]
    assert count == 2


def test_char_units_words_leading_space():
    units, count = anim.char_units(" ab cd", "words")
    # leading space maps to word 0; two words total
    assert count == 2
    assert units[0] == 0
    assert units[-1] == 1


def test_char_units_lines():
    units, count = anim.char_units("a\nbc", "lines")
    assert units == [0, 0, 1, 1]   # 'a', '\n' -> line 0 ; 'b','c' -> line 1
    assert count == 2


# -- text_entrance -----------------------------------------------------------
def test_text_entrance_returns_transform_tuple():
    per = anim.text_entrance("abc", t=0.5)
    res = per(0, "a")
    assert len(res) == 4  # (dx, dy, alpha, scale)


def test_text_entrance_fade_progression():
    # linear ease, per-char stagger; at t=0.1 the first char is in, later ones not
    per = anim.text_entrance("abcd", t=0.1, by="chars",
                             stagger=0.1, duration=0.1, ease="linear")
    assert per(0, "a")[2] == pytest.approx(1.0)   # alpha of first fully in
    assert per(3, "d")[2] == pytest.approx(0.0)   # last not started


def test_text_entrance_scale_and_slide():
    # at t=0 nothing has entered: scale_from applied, full slide, zero alpha
    per = anim.text_entrance("ab", t=0.0, stagger=0.1, duration=0.4,
                             fade=True, slide=20.0, scale_from=0.0)
    dx, dy, alpha, scale = per(0, "a")
    assert alpha == pytest.approx(0.0)
    assert dy == pytest.approx(20.0)
    assert scale == pytest.approx(0.0)


def test_text_entrance_settled():
    per = anim.text_entrance("hello", t=100.0, slide=20.0, scale_from=0.0)
    for k in range(5):
        dx, dy, alpha, scale = per(k, "h")
        assert alpha == pytest.approx(1.0)
        assert dy == pytest.approx(0.0)
        assert scale == pytest.approx(1.0)


def test_text_entrance_deterministic():
    a = anim.text_entrance("staggered", t=0.37, by="words", stagger=0.05)
    b = anim.text_entrance("staggered", t=0.37, by="words", stagger=0.05)
    assert [a(k, "x") for k in range(9)] == [b(k, "x") for k in range(9)]


def test_text_entrance_word_level_stagger():
    # two words; at a time where word 0 is in and word 1 is not
    s = "foo bar"
    per = anim.text_entrance(s, t=0.1, by="words", stagger=0.2,
                             duration=0.1, ease="linear")
    units, _ = anim.char_units(s, "words")
    # a char in word 0 fully in, a char in word 1 not yet
    k_word0 = units.index(0)
    k_word1 = units.index(1)
    assert per(k_word0, "f")[2] == pytest.approx(1.0)
    assert per(k_word1, "b")[2] == pytest.approx(0.0)
