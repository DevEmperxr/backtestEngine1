"""017 — 014/015's 15m-Bollinger + 5m outside-engulfing fade, entries only after
the London fix: window 16:00 London -> 16:00 New York.

    make_a(): SL beyond the setup extreme (as 014)
    make_b(): SL beyond the engulfing candle (as 015)

See research/runs/017_bb15_engulf5_postfix/summary.md.
"""

from datetime import time
from importlib import import_module

_m = import_module("research.strategies.010_bb15_x5_fade_extreme")
Bb15Cross5FadeStrategy = _m.Bb15Cross5FadeStrategy


def _make(stop_mode: str) -> Bb15Cross5FadeStrategy:
    return Bb15Cross5FadeStrategy(bb_tf="15m", bb_n=20, bb_k=2.0, setup_life_min=120,
                                  tp_frac=0.8, stop_mode=stop_mode, stop_buffer_pips=2.0,
                                  confirm="engulf_outside",
                                  window_start=time(16, 0), window_start_tz=_m.LONDON,
                                  window_end=time(16, 0), window_end_tz=_m.NY)


def make_a() -> Bb15Cross5FadeStrategy:
    return _make("extreme")


def make_b() -> Bb15Cross5FadeStrategy:
    return _make("signal_bar")


make = make_a
