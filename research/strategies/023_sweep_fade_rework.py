"""023 — Idea 1 reworked (see research/runs/023_sweep_fade_rework/summary.md).

    make_a(): 022's 1m sweep entry, stop = 1.5 x ATR14 of the last closed 5m bar
    make_b(): sweep read on 5m bars (5m swings, 5m stretch), stop 1 pip beyond the 5m sweep bar
"""

from importlib import import_module

SweepFadeStrategy = import_module("research.strategies.022_sweep_fade_to_ma").SweepFadeStrategy


def make_a() -> SweepFadeStrategy:
    return SweepFadeStrategy(mode="sweep", stretch_atr=2.0, pivot_k=3, er_trend=0.32,
                             timeframe="1m", stop_mode="atr", stop_atr_mult=1.5)


def make_b() -> SweepFadeStrategy:
    return SweepFadeStrategy(mode="sweep", stretch_atr=2.0, pivot_k=3, er_trend=0.32,
                             timeframe="5m", stop_mode="sweep", stop_buffer_pips=1.0)


make = make_a
