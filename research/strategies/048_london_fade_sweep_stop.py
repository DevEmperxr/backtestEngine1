"""048 — the London fade (046) with the stop beyond the sweep candle + 3 pips instead of
1.5 x 5m ATR: short stop = sweep candle high + 3 pips, long stop = sweep candle low - 3 pips
(distance measured from the signal candle's mid close; the engine applies it from the fill).
Everything else as 046.

See research/runs/048_london_fade_sweep_stop/summary.md.
"""

from __future__ import annotations

from datetime import time
from importlib import import_module

_046 = import_module("research.strategies.046_london_fade_standalone")
_m = import_module("research.strategies.022_sweep_fade_to_ma")


def make():
    return _046.LondonFade(mode="sweep", stretch_atr=2.0, pivot_k=3, er_trend=0.32,
                           timeframe="1m", stop_mode="sweep", stop_buffer_pips=3.0,
                           window_start=time(8, 0), window_start_tz=_m.LONDON,
                           window_end=time(16, 0), window_end_tz=_m.NY)
