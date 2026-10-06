"""050 — London fade (046 entry and 1.5 x 5m ATR stop) with a runner after the middle band:

    make_b(): all-in runner. At the middle band (the 5m SMA20 distance at the signal, = 046's
              target) the stop moves to break-even; target = the opposite stretch band
              (MA -/+ 2 x 5m ATR at the signal); runner closed at 08:00 New York at the latest.
    make_c(): as B, but half the position is closed at the middle band (engine partial take-profit)
              and the other half runs as in B.

Entry, hours, context, news blackout as 046. See research/runs/050_london_fade_runner/summary.md.
"""

from __future__ import annotations

from datetime import time
from importlib import import_module

import polars as pl

from lib.data import PIP

_046 = import_module("research.strategies.046_london_fade_standalone")
_m = import_module("research.strategies.022_sweep_fade_to_ma")


class LondonFadeRunner(_046.LondonFade):
    def __init__(self, *, partial_frac: float | None = None, runner_end_ny: int = 8, **kw) -> None:
        super().__init__(**kw)
        self.partial_frac = partial_frac
        self.runner_end_ny = runner_end_ny
        self.be_frac = 1.0       # marks break-even use for the run_experiment audit (column set below)

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        out = super().generate_signals(df)
        sig = pl.col("long_signal") | pl.col("short_signal")
        ma_dist = pl.col("tp_pips")                                  # 046 target = distance to the 5m SMA20
        opp_band = ma_dist + self.stretch_atr * pl.col("atr5") / PIP  # distance to the opposite stretch band
        late = pl.col("close_time").dt.convert_time_zone(_m.NY).dt.hour() >= self.runner_end_ny
        cols = dict(
            be_trigger_pips=pl.when(sig).then(ma_dist),
            tp_pips=pl.when(sig).then(opp_band),
            exit_signal=pl.col("exit_signal") | (late & ~sig),
        )
        if self.partial_frac is not None:
            cols.update(partial_tp_pips=pl.when(sig).then(ma_dist),
                        partial_frac=pl.when(sig).then(pl.lit(self.partial_frac)))
        return out.with_columns(**cols)


def _make(partial_frac):
    return LondonFadeRunner(partial_frac=partial_frac, mode="sweep", stretch_atr=2.0, pivot_k=3,
                            er_trend=0.32, timeframe="1m", stop_mode="atr", stop_atr_mult=1.5,
                            window_start=time(8, 0), window_start_tz=_m.LONDON,
                            window_end=time(16, 0), window_end_tz=_m.NY)


def make_b() -> LondonFadeRunner:
    return _make(None)


def make_c() -> LondonFadeRunner:
    return _make(0.5)
