"""024 — 023A (1m sweep fade to the 5m MA20) with three stop methods
(see research/runs/024_sweep_fade_stops/summary.md).

    make_a(): stop beyond the sweep bar + 0.5 x 5m ATR
    make_b(): 023A stop (1.5 x 5m ATR) + time stop after 30 one-minute bars
    make_c(): 023A stop (1.5 x 5m ATR) + break-even at 50% of the TP distance
"""

from importlib import import_module

SweepFadeStrategy = import_module("research.strategies.022_sweep_fade_to_ma").SweepFadeStrategy
_KW = dict(mode="sweep", stretch_atr=2.0, pivot_k=3, er_trend=0.32, timeframe="1m")


def make_a() -> SweepFadeStrategy:
    return SweepFadeStrategy(**_KW, stop_mode="sweep_buffer", buffer_atr=0.5)


def make_b() -> SweepFadeStrategy:
    return SweepFadeStrategy(**_KW, stop_mode="atr", stop_atr_mult=1.5, max_hold_bars=30)


def make_c() -> SweepFadeStrategy:
    return SweepFadeStrategy(**_KW, stop_mode="atr", stop_atr_mult=1.5, be_frac=0.5)


make = make_a
