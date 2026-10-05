"""012 — as 010 (15m Bollinger stretch, 120-min setup, TP 80% to the 15m mid,
SL beyond the setup extreme) but confirmed by a 5m "outside" engulfing candle
instead of a 5m SMA 9/21 cross.

See research/runs/012_bb15_engulf5_extreme/summary.md.
"""

from importlib import import_module

Bb15Cross5FadeStrategy = import_module(
    "research.strategies.010_bb15_x5_fade_extreme").Bb15Cross5FadeStrategy


def make() -> Bb15Cross5FadeStrategy:
    return Bb15Cross5FadeStrategy(bb_tf="15m", bb_n=20, bb_k=2.0, setup_life_min=120,
                                  tp_frac=0.8, stop_mode="extreme", stop_buffer_pips=2.0,
                                  confirm="engulf_outside")
