"""066 — the most promising earlier ideas, unchanged except for the FTMO rules (±2 min news window instead of
±60 min). Run with `run_experiment --prop` (commission, flat by 16:55 New York).

    make_london_fade()     046 London-open sideways fade (1.5x ATR stop, target the 5m SMA20)
    make_london_fade_4r()  049 variant: sweep + 3 pip stop, break-even at +2R, target 4R
    make_home_hours()      058 home-hours weakness (short home session, long US session, 1x daily-ATR stop)
    make_orb_nr7()         059 London-open range breakout after NR7 days

See research/runs/066_ftmo_reruns/summary.md.
"""

from __future__ import annotations

from datetime import time
from importlib import import_module

_m = import_module("research.strategies.022_sweep_fade_to_ma")
_046 = import_module("research.strategies.046_london_fade_standalone")
_049 = import_module("research.strategies.049_london_fade_be2r_tp4r")
_058 = import_module("research.strategies.058_home_hours")
_059 = import_module("research.strategies.059_london_orb_nr7")

FTMO_MIN = 2
_window = dict(window_start=time(8, 0), window_start_tz=_m.LONDON, window_end=time(16, 0), window_end_tz=_m.NY)


def make_london_fade():
    return _046.LondonFade(mode="sweep", stretch_atr=2.0, pivot_k=3, er_trend=0.32, timeframe="1m",
                           stop_mode="atr", stop_atr_mult=1.5, blackout_min=FTMO_MIN, **_window)


def make_london_fade_4r():
    return _049.LondonFadeRunner(mode="sweep", stretch_atr=2.0, pivot_k=3, er_trend=0.32, timeframe="1m",
                                 stop_mode="sweep", stop_buffer_pips=3.0, blackout_min=FTMO_MIN, **_window)


def make_home_hours():
    return _058.HomeHours(blackout_min=FTMO_MIN)


def make_orb_nr7():
    return _059.LondonORB(nr7=True, blackout_min=FTMO_MIN)
