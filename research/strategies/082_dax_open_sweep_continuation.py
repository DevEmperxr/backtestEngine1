"""082 — DAX-open sweep CONTINUATION: the exact mirror of the 081 London fade on GER40. Same signal bar (1m stretch
beyond the 5m SMA20 ± 2 ATR that sweeps a confirmed 1m swing, 09:00–10:59 Frankfurt, 1h sideways), but traded WITH
the move: target = the fade's stop distance (1.5 × 5m ATR14), stop = the fade's target distance (back to the 5m SMA20).
Signals with a stop under 5 points are skipped (cost guard). Pip-aware (points).

See research/runs/082_dax_open_sweep_continuation/summary.md.
"""

from __future__ import annotations

from importlib import import_module

import polars as pl

_081 = import_module("research.strategies.081_nas_london_fade")
MIN_STOP_PTS = 5.0


class SweepContinuation(_081.NasLondonFade):
    audit_kind = None    # the sweep022 audit checks fade direction/stop; use the generic audit

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        out = super().generate_signals(df)
        fs, fl = pl.col("short_signal"), pl.col("long_signal")
        ok = (pl.col("tp_pips") >= MIN_STOP_PTS).fill_null(False)
        return out.with_columns(
            long_signal=fs & ok, short_signal=fl & ok,
            sl_pips=pl.when((fs | fl) & ok).then(pl.col("tp_pips")),
            tp_pips=pl.when((fs | fl) & ok).then(pl.col("sl_pips")),
        )


def make() -> SweepContinuation:
    m = _081.make()
    s = SweepContinuation.__new__(SweepContinuation)
    s.__dict__.update(m.__dict__)
    return s
