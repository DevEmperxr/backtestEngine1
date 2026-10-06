"""039 — 034 (Idea 1, London open -> NY close) with the stop widened to 3 x 5m ATR.
See research/runs/039_london_sideways_wide_stop_eurgbp/summary.md.
"""

from datetime import time
from importlib import import_module

_m = import_module("research.strategies.022_sweep_fade_to_ma")


def make():
    return _m.SweepFadeStrategy(mode="sweep", stretch_atr=2.0, pivot_k=3, er_trend=0.32,
                                timeframe="1m", stop_mode="atr", stop_atr_mult=3.0,
                                window_start=time(8, 0), window_start_tz=_m.LONDON,
                                window_end=time(16, 0), window_end_tz=_m.NY)
