"""016 — out-of-sample test of the London-fix fade on 2023 and 2025.

    make_a(): 007's rules, unchanged.
    make_b(): as A, but only when |15:00->16:00 London move| exceeds the median
              |move| of the previous 20 fix days (strictly past days).

See research/runs/016_fix_fade_oos/summary.md (registered before the test data
existed on disk).
"""

from __future__ import annotations

from datetime import time
from importlib import import_module

import polars as pl

_007 = import_module("research.strategies.007_fix_fade_london")
NY = _007.NY


class FixFadeFilteredStrategy(_007.FixFadeStrategy):
    """007 plus a past-only big-move filter."""

    def __init__(self, *, filter_days: int | None = None, **kw) -> None:
        super().__init__(**kw)
        self.filter_days = filter_days

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        out = super().generate_signals(df)
        if self.filter_days is None:
            return out
        # one row per fix day; threshold = median |r| of the PREVIOUS n fix days
        fix = out.filter(pl.col("is_fix_bar") & pl.col("r_lookback").is_not_null()).select(
            "close_time",
            thr=pl.col("r_lookback").abs()
                  .rolling_median(self.filter_days, min_samples=self.filter_days).shift(1),
        )
        out = out.join(fix, on="close_time", how="left", maintain_order="left")
        big = (pl.col("r_lookback").abs() > pl.col("thr")).fill_null(False)
        return out.with_columns(
            long_signal=pl.col("long_signal") & big,
            short_signal=pl.col("short_signal") & big,
        )


def _kw():
    return dict(fix_time=time(16, 0), lookback_min=60, window_end=time(16, 0),
                window_end_tz=NY, sl_pips=50, tp_pips=50)


def make_a() -> FixFadeFilteredStrategy:
    return FixFadeFilteredStrategy(filter_days=None, **_kw())


def make_b() -> FixFadeFilteredStrategy:
    return FixFadeFilteredStrategy(filter_days=20, **_kw())


make = make_a
