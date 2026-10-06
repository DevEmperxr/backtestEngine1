"""053 — the London fade (046) one timeframe up: context on 4h (ER20 / SMA20 slope), stretch,
stop and target on 15m (SMA20 +- 2 x ATR14; stop 1.5 x 15m ATR; target the 15m SMA20), liquidity
sweep of the latest confirmed 5m swing (k = 3) as the trigger, entry at the next 5m open.
Same hours (entries 03:00–04:59 NY), 1h-equivalent threshold ER < 0.32 for "sideways", flat 16:00 NY,
news blackout, one position at a time, no daily limit.

See research/runs/053_london_fade_higher_tf/summary.md.
"""

from __future__ import annotations

from datetime import time
from importlib import import_module

_046 = import_module("research.strategies.046_london_fade_standalone")
_m = import_module("research.strategies.022_sweep_fade_to_ma")


def make():
    return _046.LondonFade(mode="sweep", stretch_atr=2.0, pivot_k=3, er_trend=0.32,
                           timeframe="5m", stop_mode="atr", stop_atr_mult=1.5,
                           setup_min=15, ctx_min=240,
                           window_start=time(8, 0), window_start_tz=_m.LONDON,
                           window_end=time(16, 0), window_end_tz=_m.NY)
