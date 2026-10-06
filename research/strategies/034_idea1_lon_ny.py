"""034 — Idea 1 (023A, unchanged) with the window widened to 08:00 London -> 16:00 New York,
flat at 16:00 New York. See research/runs/034_idea1_lon_ny/summary.md.
"""

from datetime import time
from importlib import import_module

_m = import_module("research.strategies.022_sweep_fade_to_ma")


def make():
    return _m.SweepFadeStrategy(mode="sweep", stretch_atr=2.0, pivot_k=3, er_trend=0.32,
                                timeframe="1m", stop_mode="atr", stop_atr_mult=1.5,
                                window_start=time(8, 0), window_start_tz=_m.LONDON,
                                window_end=time(16, 0), window_end_tz=_m.NY)
