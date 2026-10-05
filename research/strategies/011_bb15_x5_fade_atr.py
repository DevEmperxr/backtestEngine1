"""011 — as 010 (15m Bollinger stretch + 5m SMA 9/21 cross, TP 80% to the
15m middle band), but SL = 2.5 x ATR(14) of 5m bars at the signal bar.

See research/runs/011_bb15_x5_fade_atr/summary.md.
"""

from importlib import import_module

Bb15Cross5FadeStrategy = import_module(
    "research.strategies.010_bb15_x5_fade_extreme").Bb15Cross5FadeStrategy


def make() -> Bb15Cross5FadeStrategy:
    return Bb15Cross5FadeStrategy(bb_tf="15m", bb_n=20, bb_k=2.0, fast_n=9, slow_n=21,
                                  setup_life_min=120, tp_frac=0.8, stop_mode="atr",
                                  atr_n=14, atr_sl_mult=2.5)
