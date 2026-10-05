"""003 — as 001 (flat at 16:00 London), but SL = 2.5 x ATR(14) at the signal
bar and TP = 1.5 x SL, per trade.

See research/runs/003_sma_nywin_atr/summary.md.
"""

from importlib import import_module

SmaNyWindowStrategy = import_module("research.strategies.001_sma_nywin_flat1600").SmaNyWindowStrategy


def make() -> SmaNyWindowStrategy:
    # sl_pips/tp_pips here only set the 1.5R ratio and the chart fallback;
    # each trade's real distances come from the per-bar ATR columns.
    return SmaNyWindowStrategy(
        fast_n=20, slow_n=50, sl_pips=10, tp_pips=15, force_flat=True, atr_sl_mult=2.5, atr_n=14,
    )
