"""013 — as 012 (5m outside-engulfing confirmation of a 15m Bollinger stretch),
but SL 2 pips beyond the engulfing candle itself.

See research/runs/013_bb15_engulf5_candlestop/summary.md.
"""

from importlib import import_module

Bb15Cross5FadeStrategy = import_module(
    "research.strategies.010_bb15_x5_fade_extreme").Bb15Cross5FadeStrategy


def make() -> Bb15Cross5FadeStrategy:
    return Bb15Cross5FadeStrategy(bb_tf="15m", bb_n=20, bb_k=2.0, setup_life_min=120,
                                  tp_frac=0.8, stop_mode="signal_bar", stop_buffer_pips=2.0,
                                  confirm="engulf_outside")
