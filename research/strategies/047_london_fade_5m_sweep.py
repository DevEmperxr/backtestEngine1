"""047 — the London fade (046) with the liquidity sweep read on 5m candles instead of 1m: a 5m
candle reaches the 2 x ATR stretch line, pokes past the latest confirmed 5m swing (k = 3, i.e. the
extreme of 7 candles = 35 min) and closes back inside; entry at the next 5m open. Everything else as
046 (1h sideways, entries 03:00–04:59 NY, stop 1.5 x 5m ATR, target the 5m SMA20, flat 16:00 NY,
+-1 h red-news blackout).

See research/runs/047_london_fade_5m_sweep/summary.md.
"""

from __future__ import annotations

from datetime import time
from importlib import import_module

_046 = import_module("research.strategies.046_london_fade_standalone")
_m = import_module("research.strategies.022_sweep_fade_to_ma")


def make():
    return _046.LondonFade(mode="sweep", stretch_atr=2.0, pivot_k=3, er_trend=0.32,
                           timeframe="5m", stop_mode="atr", stop_atr_mult=1.5,
                           window_start=time(8, 0), window_start_tz=_m.LONDON,
                           window_end=time(16, 0), window_end_tz=_m.NY)
