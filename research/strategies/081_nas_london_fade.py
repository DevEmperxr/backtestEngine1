"""081 — the London fade (066:london_fade = 046 rules + FTMO ±2 min news) run unchanged on NAS100. Pip-aware: the
022 base computes stop/target in EURUSD pips (0.0001); this wrapper converts them to index points (1.0).

See research/runs/081_nas_london_fade/summary.md.
"""

from __future__ import annotations

from importlib import import_module

import polars as pl

from lib.data import PIP, pip_size

_066 = import_module("research.strategies.066_ftmo_reruns")
_046 = import_module("research.strategies.046_london_fade_standalone")


class NasLondonFade(_046.LondonFade):
    pip_aware = True

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        out = super().generate_signals(df)
        k = PIP / pip_size("NAS100")
        cols = [c for c in ("sl_pips", "tp_pips", "be_trigger_pips") if c in out.columns]
        return out.with_columns([pl.col(c) * k for c in cols])


def make() -> NasLondonFade:
    return NasLondonFade(mode="sweep", stretch_atr=2.0, pivot_k=3, er_trend=0.32, timeframe="1m",
                         stop_mode="atr", stop_atr_mult=1.5, blackout_min=_066.FTMO_MIN, currencies=("USD",),
                         **_066._window)
