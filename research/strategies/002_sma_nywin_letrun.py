"""002 — as 001, but trades are left to run to SL/TP (no 16:00 force-flat).

See research/runs/002_sma_nywin_letrun/summary.md.
"""

from importlib import import_module

SmaNyWindowStrategy = import_module("research.strategies.001_sma_nywin_flat1600").SmaNyWindowStrategy


def make() -> SmaNyWindowStrategy:
    return SmaNyWindowStrategy(fast_n=20, slow_n=50, sl_pips=10, tp_pips=15, force_flat=False)
