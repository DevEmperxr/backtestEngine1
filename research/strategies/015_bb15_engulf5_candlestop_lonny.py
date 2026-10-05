"""015 — as 013 (15m Bollinger stretch + 5m outside-engulfing confirm, SL beyond
the engulfing candle), window 08:00 London -> 16:00 New York.

See research/runs/015_bb15_engulf5_candlestop_lonny/summary.md.
"""

from datetime import time
from importlib import import_module

_m = import_module("research.strategies.010_bb15_x5_fade_extreme")


class Bb15Cross5FadeStrategy(_m.Bb15Cross5FadeStrategy):
    @staticmethod
    def report_splits(trades, sig=None):
        """Pre-registered descriptive split: entries before vs at/after 16:00 London."""
        import polars as pl
        lt = trades["entry_time"].dt.convert_time_zone(_m.LONDON).dt.time()
        before = lt < time(16, 0)
        return {"entry_before_1600_london": trades.filter(before),
                "entry_after_1600_london": trades.filter(~before)}


def make() -> Bb15Cross5FadeStrategy:
    return Bb15Cross5FadeStrategy(bb_tf="15m", bb_n=20, bb_k=2.0, setup_life_min=120,
                                  tp_frac=0.8, stop_mode="signal_bar", stop_buffer_pips=2.0,
                                  confirm="engulf_outside",
                                  window_start=time(8, 0), window_start_tz=_m.LONDON,
                                  window_end=time(16, 0), window_end_tz=_m.NY)
