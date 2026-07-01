"""Audio synthesis / scheduling tests — no audio device required."""

import wave

import numpy as np
import pytest

from arcv.audio import synth, render_track, save_wav, Bleeps, CueScheduler
from arcv.audio import arwes_available, load_arwes_bank, ARWES_MAP


def test_tone_shape_and_bounds():
    s = synth.tone(440, 0.05, "sine", vol=0.5)
    assert s.dtype == np.float32
    assert abs(len(s) - int(0.05 * synth.SR)) <= 2
    assert np.max(np.abs(s)) <= 0.5 + 1e-3


def test_build_bank_names():
    bank = synth.build_bank(0.5)
    expected = {"assemble", "type", "decipher", "lock", "panel", "action", "exit", "scan",
                "error", "alert"}
    assert set(bank) == expected
    for v in bank.values():
        assert v.dtype == np.float32 and len(v) > 0


def test_render_timeline_length_and_peak():
    bank = synth.build_bank(0.6)
    track = synth.render_timeline([(0.0, "assemble"), (0.5, "lock")], 1.0, bank)
    assert track.dtype == np.float32
    assert len(track) >= int(1.0 * synth.SR)
    assert np.max(np.abs(track)) <= 1.0 + 1e-6


def test_save_wav_readable(tmp_path):
    p = tmp_path / "b.wav"
    save_wav(str(p), render_track([(0.0, "lock")], 0.5, 0.6))
    w = wave.open(str(p))
    assert w.getnchannels() == 1
    assert w.getsampwidth() == 2
    assert w.getframerate() == synth.SR
    assert w.getnframes() > 0


def test_bleeps_disabled_is_silent_noop():
    b = Bleeps(enabled=False)  # no device / no player
    b.play("lock")  # must not raise
    b.close()


def test_arwes_bank_covers_all_events_and_uses_real_sounds():
    # bank always covers every HUD event (synth fallback), even without files
    bank = load_arwes_bank(volume=0.6)
    for ev in ARWES_MAP:
        assert ev in bank and len(bank[ev]) > 0
    if not arwes_available():
        pytest.skip("Arwes sounds / ffmpeg not available")
    syn = synth.build_bank(0.6)
    # at least one mapped event should be a real (differently-sized) Arwes clip
    assert any(len(bank[ev]) != len(syn[ev]) for ev in ("assemble", "lock", "panel", "exit"))


def test_bleeps_arwes_source_builds_disabled():
    b = Bleeps(enabled=False, source="arwes")
    assert set(ARWES_MAP).issubset(b.bank.keys())
    b.play("lock")  # no device -> silent no-op
    b.close()


def test_cue_scheduler_fires_in_time_order():
    class Rec:
        def __init__(self):
            self.calls = []

        def play(self, name):
            self.calls.append(name)

    rec = Rec()
    sched = CueScheduler(rec, [(0.1, "a"), (0.5, "b"), (0.3, "c")])
    sched.update(0.0)
    assert rec.calls == []
    sched.update(0.35)
    assert rec.calls == ["a", "c"]
    sched.update(1.0)
    assert rec.calls == ["a", "c", "b"]
