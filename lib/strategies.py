"""Concrete strategies (spec §4).

Each strategy is a small, explicit `Strategy` subclass — a composition of
signal-generating logic, not a config-driven generic system (deliberately: a
declarative definition invites parameter-twisting; explicit code keeps a human
making each decision).

`SmaCrossoverStrategy` is the reference / regression case (spec §6).
"""

from __future__ import annotations

import polars as pl

from lib.engine import Strategy
from lib.signals import crossover, sma


class SmaCrossoverStrategy(Strategy):
    """Fast/slow SMA crossover on the mid price, with fixed SL/TP.

    Long on a fast-over-slow cross up, short on a cross down. The engine also
    exits on the opposite cross (`exit_on_opposite_signal` stays True, as the
    prototype did) and on SL/TP.

    SL/TP are required — the prototype's exact pip values aren't recorded, and a
    default here would silently bake in a guess before the regression pins them.
    """

    # The prototype was always in the market — it flipped long<->short on each
    # opposite cross rather than sitting flat (spec §6).
    reverse_on_opposite_signal = True

    def __init__(
        self,
        *,
        fast_n: int = 20,
        slow_n: int = 50,
        sl_pips: float,
        tp_pips: float,
        timeframe: str = "5m",
    ) -> None:
        super().__init__(sl_pips, tp_pips, timeframe)
        if not (1 <= fast_n < slow_n):
            raise ValueError(
                f"need 1 <= fast_n < slow_n, got fast_n={fast_n}, slow_n={slow_n}"
            )
        self.fast_n = fast_n
        self.slow_n = slow_n

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        # Mid price is for SIGNAL COMPUTATION ONLY (spec §0.3) — the engine
        # executes fills on bid/ask. SMA + crossover are purely position-based
        # (row t uses rows <= t), so §2.2's "bar t's close = bar_start +
        # timeframe" rule is vacuous here — no time arithmetic happens. It bites
        # for the 4H-trend-filter strategy (join_asof), not this one.
        out = df.with_columns(
            mid_close=(pl.col("bid_close") + pl.col("ask_close")) / 2,
        )
        out = out.with_columns(
            sma_fast=sma(pl.col("mid_close"), self.fast_n),
            sma_slow=sma(pl.col("mid_close"), self.slow_n),
        )
        cross_up, cross_down = crossover(pl.col("sma_fast"), pl.col("sma_slow"))
        return out.with_columns(long_signal=cross_up, short_signal=cross_down)
